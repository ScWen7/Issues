//go:build unix

// An integration test for Multica fdfbfcd. Install into server/internal/daemon.
// It runs the actual Daemon task executor against production handlers on loopback.
package daemon

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/multica-ai/multica/server/internal/analytics"
	authlib "github.com/multica-ai/multica/server/internal/auth"
	"github.com/multica-ai/multica/server/internal/daemon/execenv"
	"github.com/multica-ai/multica/server/internal/events"
	"github.com/multica-ai/multica/server/internal/handler"
	"github.com/multica-ai/multica/server/internal/middleware"
	"github.com/multica-ai/multica/server/internal/realtime"
	"github.com/multica-ai/multica/server/internal/service"
	"github.com/multica-ai/multica/server/internal/testutil"
	"github.com/multica-ai/multica/server/internal/util"
	db "github.com/multica-ai/multica/server/pkg/db/generated"
)

// Route only the private fixture subcommand to the upstream preparation helper.
// Production multi-purpose CLI binaries dispatch this operation in their own main.
func init() {
	if len(os.Args) == 2 && os.Args[1] == "ap4-prepare" {
		logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
		if err := execenv.RunPreparationHelper(os.Stdin, os.Stdout, logger); err != nil {
			logger.Error("fixture preparation helper", "error", err)
			os.Exit(1)
		}
		os.Exit(0)
	}
}
func TestPhase4DaemonResultHandoff(t *testing.T) {
	testutil.RedirectUserHome(t, t.TempDir())
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		t.Fatal("set DATABASE_URL to a disposable migrated database")
	}
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	q := db.New(pool)
	hub := realtime.NewHub()
	go hub.Run()
	h := handler.New(q, pool, hub, events.New(), service.NewEmailService(), nil, nil, analytics.NoopClient{}, handler.Config{})

	// Use distinct DB identities for the owner of the runtime and the user borrowing it.
	fx0 := testutil.New(pool, "", "")
	suffix := uuid.NewString()
	owner := fx0.User(t, "Resource owner", "owner-"+suffix+"@example.test")
	member := fx0.User(t, "Verifier", "verifier-"+suffix+"@example.test")
	ws := fx0.Workspace(t, "Order export", "ap4-"+suffix, testutil.Cols{"issue_prefix": "ORD"})
	fx := testutil.New(pool, ws, owner)
	fx.Member(t, ws, owner, "owner")
	fx.Member(t, ws, member, "member")
	machine := "fixture-" + suffix
	rt := fx.Runtime(t, "shared", testutil.Cols{"runtime_mode": "local", "provider": "claude", "daemon_id": machine})
	agent := fx.Agent(t, "verifier", rt, testutil.Cols{"owner_id": member, "runtime_mode": "local"})
	issue := fx.Issue(t, "Order export verification")
	ownerID, err := util.ParseUUID(owner)
	if err != nil {
		t.Fatal(err)
	}
	wsID, err := util.ParseUUID(ws)
	if err != nil {
		t.Fatal(err)
	}
	exp := pgtype.Timestamptz{Time: time.Now().Add(time.Hour), Valid: true}
	daemonToken, err := authlib.GenerateDaemonToken()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := q.CreateDaemonToken(ctx, db.CreateDaemonTokenParams{TokenHash: authlib.HashToken(daemonToken), WorkspaceID: wsID, DaemonID: machine, OwnerID: ownerID, ExpiresAt: exp}); err != nil {
		t.Fatal(err)
	}
	pat, err := authlib.GeneratePATToken()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := q.CreatePersonalAccessToken(ctx, db.CreatePersonalAccessTokenParams{UserID: ownerID, Name: "fixture", TokenHash: authlib.HashToken(pat), TokenPrefix: pat[:8], ExpiresAt: exp}); err != nil {
		t.Fatal(err)
	}

	// Route only the exercised methods, using the same production middlewares as cmd/server/router.go.
	router := chi.NewRouter()
	router.Group(func(r chi.Router) {
		r.Use(middleware.Auth(q, nil, nil, nil))
		r.Patch("/api/runtimes/{runtimeId}", h.UpdateAgentRuntime)
		r.Post("/api/runtimes/{runtimeId}/revoke-workspace-access", h.RevokeRuntimeWorkspaceAccess)
		r.Get("/api/issues/{id}", h.GetIssue)
	})
	router.Route("/api/daemon", func(r chi.Router) {
		r.Use(middleware.DaemonAuth(q, nil, nil, nil))
		r.Post("/runtimes/{runtimeId}/tasks/claim", h.ClaimTaskByRuntime)
		r.Post("/runtimes/{runtimeId}/tasks/{taskId}/prepare-lease", h.ExtendTaskPrepareLease)
		r.Post("/runtimes/{runtimeId}/tasks/{taskId}/skill-bundles/resolve", h.ResolveTaskSkillBundles)
		r.Post("/tasks/{taskId}/start", h.StartTask)
		r.Get("/tasks/{taskId}/status", h.GetTaskStatus)
		r.Post("/tasks/{taskId}/progress", h.ReportTaskProgress)
		r.Post("/tasks/{taskId}/messages", h.ReportTaskMessages)
		r.Post("/tasks/{taskId}/session", h.PinTaskSession)
		r.Post("/tasks/{taskId}/usage", h.ReportTaskUsage)
		r.Post("/tasks/{taskId}/context-receipt", h.ReportTaskContextReceipt)
		r.Post("/tasks/{taskId}/complete", h.CompleteTask)
		r.Post("/tasks/{taskId}/fail", h.FailTask)
		r.Post("/tasks/{taskId}/cancel-ack", h.AckTaskCancelled)
		r.Post("/tasks/{taskId}/supplements/claim", h.ClaimTaskSupplement)
	})
	var lock sync.Mutex
	counts := map[string]int{}
	var failAckPath string
	var outbox *terminalReportStore
	var pendingWhenAckLost int
	var stopTask string
	holdStatus := make(chan struct{})
	seenStatus := make(chan struct{}, 1)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		lock.Lock()
		counts[r.URL.Path]++
		n := counts[r.URL.Path]
		drop := r.URL.Path == failAckPath && n == 1
		hold := r.URL.Path == stopTask
		lock.Unlock()
		if hold {
			select {
			case seenStatus <- struct{}{}:
			default:
			}
			select {
			case <-holdStatus:
			case <-r.Context().Done():
				return
			}
		}
		if drop {
			captured := httptest.NewRecorder()
			router.ServeHTTP(captured, r)
			if captured.Code == 200 {
				stats, err := outbox.stats()
				if err != nil {
					t.Errorf("read terminal outbox: %v", err)
				}
				lock.Lock()
				pendingWhenAckLost = stats.PendingCount
				lock.Unlock()
				http.Error(w, "fixture: acknowledgement lost after commit", 503)
				return
			}
			w.WriteHeader(captured.Code)
			w.Write(captured.Body.Bytes())
			return
		}
		router.ServeHTTP(w, r)
	}))
	defer server.Close()
	request := func(method, path, token string, payload any, status int) {
		t.Helper()
		var body bytes.Buffer
		if payload != nil {
			if err := json.NewEncoder(&body).Encode(payload); err != nil {
				t.Fatal(err)
			}
		}
		req, err := http.NewRequestWithContext(ctx, method, server.URL+path, &body)
		if err != nil {
			t.Fatal(err)
		}
		req.Header.Set("Authorization", "Bearer "+token)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Workspace-ID", ws)
		res, err := server.Client().Do(req)
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if res.StatusCode != status {
			b, _ := io.ReadAll(res.Body)
			t.Fatalf("%s %s status=%d wanted=%d: %s", method, path, res.StatusCode, status, b)
		}
	}
	share := func(members []string) {
		request("PATCH", "/api/runtimes/"+rt, pat, map[string]any{"shared_with": members}, 200)
	}
	share([]string{member})
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Fatal(err)
	}
	// A real child process speaks the Claude streaming protocol. It copies an existing
	// order-verification report into its own working directory and returns its text.
	// The cancellation scenario blocks until the production daemon terminates this child.
	provider := filepath.Join(t.TempDir(), "claude")
	source := `import json, os, pathlib, sys, time
sys.stdin.readline()
def emit(obj): print(json.dumps(obj), flush=True)
emit({"type":"system","session_id":os.environ["AP4_SESSION"]})
data=pathlib.Path(os.environ["AP4_REPORT"]).read_bytes()
pathlib.Path("observed-report.json").write_bytes(data)
pathlib.Path(os.environ["AP4_STARTED"]).write_text(str(os.getpid()))
if os.environ.get("AP4_HOLD")=="yes":
    while True: time.sleep(.05)
emit({"type":"result","subtype":"success","is_error":False,"session_id":os.environ["AP4_SESSION"],"result":data.decode().strip()})
`
	if err := os.WriteFile(provider, []byte("#!"+python+"\n"+source), 0700); err != nil {
		t.Fatal(err)
	}
	work := t.TempDir()
	d := New(Config{ServerBaseURL: server.URL, DaemonID: machine, WorkspacesRoot: work, AgentTimeout: 30 * time.Second, Agents: map[string]AgentEntry{"claude": {Path: provider}}}, slog.New(slog.NewTextHandler(os.Stderr, nil)))
	d.executionEnvironmentCommand = func() ([]string, error) { binary, err := os.Executable(); return []string{binary, "ap4-prepare"}, err }
	outbox = d.terminalReports
	d.client.SetToken(daemonToken)
	d.runtimeIndex[rt] = Runtime{ID: rt, Provider: "claude"}
	d.cancelPollInterval = 200 * time.Millisecond
	reportPath := func(candidate string) string {
		path := os.Getenv("AP_" + candidate + "_REPORT")
		if path == "" {
			t.Fatalf("set AP_%s_REPORT to its order fixture", candidate)
		}
		return path
	}
	claim := func(candidate string, hold bool) (*Task, string) {
		t.Helper()
		id := fx.Task(t, agent, testutil.Cols{"runtime_id": rt, "issue_id": issue, "status": "queued", "originator_user_id": member, "accountable_user_id": member})
		task, err := d.client.ClaimTask(ctx, rt)
		if err != nil || task == nil || task.ID != id || task.Agent == nil || task.AuthToken == "" {
			t.Fatalf("claim %s: %v", candidate, err)
		}
		started := filepath.Join(t.TempDir(), "started")
		task.Agent.CustomEnv = map[string]string{"AP4_SESSION": uuid.NewString(), "AP4_REPORT": reportPath(candidate), "AP4_STARTED": started}
		if hold {
			task.Agent.CustomEnv["AP4_HOLD"] = "yes"
		}
		return task, started
	}
	state := func(id string) (string, string, string) {
		t.Helper()
		var status, result, dir string
		if err := pool.QueryRow(ctx, "SELECT status, coalesce(result->>'output',''),coalesce(work_dir,'') FROM agent_task_queue WHERE id=$1", id).Scan(&status, &result, &dir); err != nil {
			t.Fatal(err)
		}
		return status, result, dir
	}
	commentCount := func(task string) int {
		t.Helper()
		var n int
		if err := pool.QueryRow(ctx, "SELECT count(*) FROM comment WHERE source_task_id=$1 AND issue_id=$2 AND author_id=$3", task, issue, agent).Scan(&n); err != nil {
			t.Fatal(err)
		}
		return n
	}
	var previous *Task
	var previousReport, previousDir string
	for _, candidate := range []string{"C1", "C2"} {
		task, _ := claim(candidate, false)
		path := "/api/daemon/tasks/" + task.ID + "/complete"
		if candidate == "C2" {
			lock.Lock()
			failAckPath = path
			lock.Unlock()
		}
		d.handleTask(ctx, *task, 0)
		status, output, dir := state(task.ID)
		original, err := os.ReadFile(reportPath(candidate))
		if err != nil {
			t.Fatal(err)
		}
		if status != "completed" || output != strings.TrimSpace(string(original)) {
			t.Fatalf("%s status=%s unexpected terminal output: %q", candidate, status, output)
		}
		copied, err := os.ReadFile(filepath.Join(dir, "observed-report.json"))
		if err != nil || !bytes.Equal(copied, original) {
			t.Fatalf("workspace copy: %s %v", dir, err)
		}
		if n := commentCount(task.ID); n != 1 {
			t.Fatalf("%s comments=%d", candidate, n)
		}
		lock.Lock()
		deliveries := counts[path]
		lock.Unlock()
		want := 1
		if candidate == "C2" {
			want = 2
			lock.Lock()
			pending := pendingWhenAckLost
			lock.Unlock()
			stats, err := outbox.stats()
			if err != nil || pending != 1 || stats.PendingCount != 0 {
				t.Fatalf("outbox when ACK lost=%d, after retry=%d: %v", pending, stats.PendingCount, err)
			}
			t.Log("C2 terminal outbox contained one report at lost acknowledgement, zero after acknowledged replay")
		}
		if deliveries != want {
			t.Fatalf("%s completion HTTP attempts=%d expected %d", candidate, deliveries, want)
		}
		var observation struct {
			Verdict string `json:"verdict"`
		}
		if err := json.Unmarshal(original, &observation); err != nil {
			t.Fatal(err)
		}
		if (candidate == "C1" && observation.Verdict != "rework") || (candidate == "C2" && observation.Verdict != "pass") {
			t.Fatalf("unexpected order verdict %s", observation.Verdict)
		}
		t.Logf("%s technical=%s verdict=%s callback attempts=%d comments=1 source bytes sha256=%x", candidate, status, observation.Verdict, deliveries, sha256.Sum256(original))
		if candidate == "C1" {
			previous, previousReport, previousDir = task, output, dir
		} else {
			if previousDir != dir {
				t.Fatalf("same Issue/Agent did not reuse workdir")
			}
			previousFile, err := os.ReadFile(filepath.Join(previousDir, "observed-report.json"))
			if err != nil || !bytes.Equal(previousFile, original) || strings.TrimSpace(string(previousFile)) == previousReport {
				t.Fatal("reused file did not move to C2")
			}
			t.Log("same local path now reads C2 bytes; earlier C1 task still has its original report")
			err = d.client.CompleteTask(ctx, previous.ID, previousReport, "", "", "", false, "", "")
			if err != nil {
				t.Fatal(err)
			}
			_, first, _ := state(previous.ID)
			_, second, _ := state(task.ID)
			if first != previousReport || second != output || commentCount(previous.ID) != 1 || commentCount(task.ID) != 1 {
				t.Fatal("late C1 disturbed existing task or comment")
			}
			t.Log("late C1 replay after C2: HTTP success, both original results and comment counts preserved")
		}
	}
	// Hold the response to one real status poll until the controller has revoked
	// the share. This makes the slice between the DB cancellation and local exit observable.
	blocked, started := claim("C2", true)
	lock.Lock()
	stopTask = "/api/daemon/tasks/" + blocked.ID + "/status"
	lock.Unlock()
	sent := make(chan struct{})
	go func() { d.handleTask(ctx, *blocked, 0); close(sent) }()
	release := sync.OnceFunc(func() { close(holdStatus) })
	defer release()
	var pid int
	until := time.Now().Add(8 * time.Second)
	for time.Now().Before(until) {
		b, err := os.ReadFile(started)
		if err == nil {
			pid, _ = strconv.Atoi(string(b))
			if pid != 0 {
				break
			}
		}
		time.Sleep(20 * time.Millisecond)
	}
	if pid == 0 {
		t.Fatal("child did not start")
	}
	select {
	case <-seenStatus:
	case <-ctx.Done():
		t.Fatal(ctx.Err())
	}
	request("PATCH", "/api/runtimes/"+rt, pat, map[string]any{"shared_with": []string{}}, 409)
	request("POST", "/api/runtimes/"+rt+"/revoke-workspace-access", pat, map[string]any{"shared_with": []string{}, "expected_nonowner_agent_ids": []string{agent}, "expected_task_ids": []string{blocked.ID}}, 200)
	request("GET", "/api/issues/"+issue, blocked.AuthToken, nil, 401)
	if st, _, _ := state(blocked.ID); st != "cancelled" {
		t.Fatalf("revoked row %s", st)
	}
	if err := syscall.Kill(pid, 0); err != nil {
		t.Fatalf("expected live child before releasing status reply: %v", err)
	}
	release()
	select {
	case <-sent:
	case <-ctx.Done():
		t.Fatal(ctx.Err())
	}
	if err := syscall.Kill(pid, 0); err != syscall.ESRCH {
		t.Fatalf("child still exists: %v", err)
	}
	ackPath := "/api/daemon/tasks/" + blocked.ID + "/cancel-ack"
	lock.Lock()
	acks := counts[ackPath]
	lock.Unlock()
	if acks != 1 {
		t.Fatalf("acks=%d", acks)
	}
	if err := d.client.CompleteTask(ctx, blocked.ID, previousReport, "", "", "", false, "", ""); err != nil {
		t.Fatal(err)
	}
	if st, out, _ := state(blocked.ID); st != "cancelled" || out != "" || commentCount(blocked.ID) != 0 {
		t.Fatalf("late callback altered cancelled row: %s %q", st, out)
	}
	t.Log("revoked: cancelled DB row and task credential 401 while child alive; after poll: child exited, cancel ACK=1; delayed daemon complete received HTTP success, late comments=0")
}
