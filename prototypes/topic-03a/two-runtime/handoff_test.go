//go:build linux

// Overlay this file in the pinned Multica server/internal/daemon package.
package daemon

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/multica-ai/multica/server/internal/analytics"
	authlib "github.com/multica-ai/multica/server/internal/auth"
	"github.com/multica-ai/multica/server/internal/events"
	"github.com/multica-ai/multica/server/internal/handler"
	"github.com/multica-ai/multica/server/internal/middleware"
	"github.com/multica-ai/multica/server/internal/realtime"
	"github.com/multica-ai/multica/server/internal/service"
	"github.com/multica-ai/multica/server/internal/storage"
	"github.com/multica-ai/multica/server/internal/testutil"
	"github.com/multica-ai/multica/server/internal/util"
	db "github.com/multica-ai/multica/server/pkg/db/generated"
)

func h5Check(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}
func h5ID(t *testing.T, id string) pgtype.UUID {
	t.Helper()
	value, err := util.ParseUUID(id)
	h5Check(t, err)
	return value
}

type h5Transport struct{}

func (h5Transport) RoundTrip(*http.Request) (*http.Response, error) {
	return nil, fmt.Errorf("fixture: A network link disconnected")
}

type h5Client struct {
	t         *testing.T
	server    *httptest.Server
	workspace string
}

func (c h5Client) request(method, path, token, kind string, body io.Reader, want int) []byte {
	c.t.Helper()
	req, err := http.NewRequest(method, c.server.URL+path, body)
	h5Check(c.t, err)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("X-Workspace-ID", c.workspace)
	if kind != "" {
		req.Header.Set("Content-Type", kind)
	}
	res, err := c.server.Client().Do(req)
	h5Check(c.t, err)
	defer res.Body.Close()
	raw, err := io.ReadAll(res.Body)
	h5Check(c.t, err)
	if res.StatusCode != want {
		c.t.Fatalf("%s %s returned %d; want %d", method, path, res.StatusCode, want)
	}
	return raw
}
func (c h5Client) post(method, path, token string, payload any, want int) []byte {
	c.t.Helper()
	data, err := json.Marshal(payload)
	h5Check(c.t, err)
	return c.request(method, path, token, "application/json", bytes.NewReader(data), want)
}
func (c h5Client) upload(issue, token string, data []byte) string {
	c.t.Helper()
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)
	h5Check(c.t, writer.WriteField("issue_id", issue))
	part, err := writer.CreateFormFile("file", "orders.xlsx")
	h5Check(c.t, err)
	_, err = part.Write(data)
	h5Check(c.t, err)
	h5Check(c.t, writer.Close())
	body := c.request("POST", "/api/upload-file", token, writer.FormDataContentType(), &buf, 200)
	var att handler.AttachmentResponse
	h5Check(c.t, json.Unmarshal(body, &att))
	if att.ID == "" || att.IssueID == nil || *att.IssueID != issue || att.SizeBytes != int64(len(data)) {
		c.t.Fatal("unbound attachment")
	}
	return att.ID
}

type h5Peer struct {
	runtime, agent, user, token string
	cfg                         Config
	daemon                      *Daemon
}

func TestTwoRuntimeOrderHandoff(t *testing.T) {
	testutil.RedirectUserHome(t, t.TempDir())
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	h5Check(t, err)
	defer pool.Close()
	q := db.New(pool)
	seed := testutil.New(pool, "", "")
	tag := uuid.NewString()
	alice := seed.User(t, "Machine owner A", "a-"+tag+"@example.test")
	bob := seed.User(t, "Receiver B", "b-"+tag+"@example.test")
	verifier := seed.User(t, "Verifier for A", "v-"+tag+"@example.test")
	issueWS := seed.Workspace(t, "Order handoff", "duo-"+tag, testutil.Cols{"issue_prefix": "ORD"})
	fx := testutil.New(pool, issueWS, alice)
	fx.Member(t, issueWS, alice, "owner")
	fx.Member(t, issueWS, bob, "member")
	fx.Member(t, issueWS, verifier, "member")
	issue := fx.Issue(t, "Verify order export under D2")
	privateProject := fx.Project(t, "A restricted project", testutil.Cols{"visibility": "private"})
	privateIssue := fx.Issue(t, "Other project orders", testutil.Cols{"project_id": privateProject})
	exp := pgtype.Timestamptz{Time: time.Now().Add(time.Hour), Valid: true}
	makePAT := func(user string) string {
		t.Helper()
		value, err := authlib.GeneratePATToken()
		h5Check(t, err)
		_, err = q.CreatePersonalAccessToken(ctx, db.CreatePersonalAccessTokenParams{UserID: h5ID(t, user), TokenHash: authlib.HashToken(value), TokenPrefix: value[:8], Name: "local test", ExpiresAt: exp})
		h5Check(t, err)
		return value
	}
	patA, patB, patV := makePAT(alice), makePAT(bob), makePAT(verifier)
	hub := realtime.NewHub()
	go hub.Run()
	h := handler.New(q, pool, hub, events.New(), service.NewEmailService(), nil, nil, analytics.NoopClient{}, handler.Config{AttachmentDownloadMode: "proxy"})
	t.Setenv("LOCAL_UPLOAD_DIR", t.TempDir())
	t.Setenv("LOCAL_UPLOAD_BASE_URL", "")
	h.Storage = storage.NewLocalStorageFromEnv()
	router := chi.NewRouter()
	router.Group(func(r chi.Router) {
		r.Use(middleware.Auth(q, nil, nil, nil))
		r.Get("/api/issues/{id}", h.GetIssue)
		r.Post("/api/issues/{id}/comments", h.CreateComment)
		r.Post("/api/upload-file", h.UploadFile)
		r.Get("/api/attachments/{id}/download", h.DownloadAttachment)
		r.Get("/api/runtimes/{runtimeId}/usage", h.GetRuntimeUsage)
		r.Patch("/api/runtimes/{runtimeId}", h.UpdateAgentRuntime)
		r.Post("/api/runtimes/{runtimeId}/revoke-workspace-access", h.RevokeRuntimeWorkspaceAccess)
	})
	router.Route("/api/daemon", func(r chi.Router) {
		r.Use(middleware.DaemonAuth(q, nil, nil, nil))
		r.Post("/runtimes/{runtimeId}/tasks/claim", h.ClaimTaskByRuntime)
		r.Post("/tasks/{taskId}/start", h.StartTask)
		r.Post("/tasks/{taskId}/complete", h.CompleteTask)
		r.Post("/heartbeat", h.DaemonHeartbeat)
	})
	srv := httptest.NewServer(router)
	defer srv.Close()
	c := h5Client{t, srv, issueWS}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	makePeer := func(label, owner, agentOwner string) h5Peer {
		t.Helper()
		machine := "fixture-" + label + "-" + tag
		rt := fx.Runtime(t, "Runtime "+label, testutil.Cols{"owner_id": owner, "runtime_mode": "local", "provider": "claude", "daemon_id": machine})
		agent := fx.Agent(t, "Order verifier "+label, rt, testutil.Cols{"owner_id": agentOwner, "runtime_mode": "local"})
		tok, err := authlib.GenerateDaemonToken()
		h5Check(t, err)
		_, err = q.CreateDaemonToken(ctx, db.CreateDaemonTokenParams{TokenHash: authlib.HashToken(tok), WorkspaceID: h5ID(t, issueWS), DaemonID: machine, OwnerID: h5ID(t, owner), ExpiresAt: exp})
		h5Check(t, err)
		cfg := Config{ServerBaseURL: srv.URL, WorkspacesRoot: t.TempDir(), DaemonID: machine, Profile: label}
		d := New(cfg, logger)
		d.client.SetToken(tok)
		return h5Peer{rt, agent, owner, tok, cfg, d}
	}
	a, b := makePeer("A", alice, verifier), makePeer("B", bob, bob)
	c.post("PATCH", "/api/runtimes/"+a.runtime, patA, map[string]any{"shared_with": []string{verifier}}, 200)
	// Publication is performed before the network fault. The restricted copy
	// deliberately has identical content, isolating access from content identity.
	data, err := os.ReadFile(os.Getenv("AP_ORDER_WORKBOOK"))
	h5Check(t, err)
	published := c.upload(issue, patA, data)
	hidden := c.upload(privateIssue, patA, data)
	if published == hidden {
		t.Fatal("expected independent delivery identities")
	}
	c.request("GET", "/api/attachments/"+hidden+"/download", patA, "", nil, 200)
	makeRun := func(p h5Peer, pat, requester, candidate string) *Task {
		t.Helper()
		content := fmt.Sprintf("[@Verifier](mention://agent/%s) Verify order export %s under D2.", p.agent, candidate)
		c.post("POST", "/api/issues/"+issue+"/comments", pat, map[string]string{"content": content}, 201)
		task, err := p.daemon.client.ClaimTask(ctx, p.runtime)
		h5Check(t, err)
		if task == nil || task.AuthToken == "" || task.Agent == nil || task.Agent.ID != p.agent || task.IssueID != issue {
			t.Fatal("member dispatch did not create an independently claimable task for ", candidate)
		}
		var boundOwner, requestAuthor string
		err = pool.QueryRow(ctx, `SELECT tok.user_id::text,c.author_id::text
			FROM task_token tok JOIN agent_task_queue t ON t.id=tok.task_id
			JOIN comment c ON c.id=t.trigger_comment_id
			WHERE t.id=$1 AND tok.token_hash=$2 AND t.agent_id=$3 AND t.runtime_id=$4`,
			task.ID, authlib.HashToken(task.AuthToken), p.agent, p.runtime).Scan(&boundOwner, &requestAuthor)
		h5Check(t, err)
		if boundOwner != p.user || requestAuthor != requester {
			t.Fatal("unexpected token owner or dispatching member")
		}
		_, err = p.daemon.client.StartTask(ctx, *task)
		h5Check(t, err)
		return task
	}
	assertState := func(task *Task, status, result string, comments int) {
		t.Helper()
		var st, res string
		var n int
		err = pool.QueryRow(ctx, `SELECT t.status,coalesce(t.result->>'output',''),(SELECT count(*) FROM comment c WHERE c.source_task_id=t.id AND c.issue_id=t.issue_id AND c.author_id=t.agent_id) FROM agent_task_queue t WHERE t.id=$1`, task.ID).Scan(&st, &res, &n)
		h5Check(t, err)
		if st != status || res != result || n != comments {
			t.Fatalf("unexpected source task: state %s (wanted %s), comments %d (wanted %d), result matches %t", st, status, n, comments, res == result)
		}
	}
	readReport := func(path string) string {
		t.Helper()
		data, err := os.ReadFile(os.Getenv(path))
		h5Check(t, err)
		return string(bytes.TrimSpace(data))
	}
	c1, c2 := readReport("AP_C1_REPORT"), readReport("AP_C2_REPORT")
	old := makeRun(a, patV, verifier, "C1")
	// The native client now has no network link; keep the real disk-backed
	// outbox and production report/ack semantics. Omit wall-clock retry delays.
	schedule := defaultTerminalRetrySchedule
	defaultTerminalRetrySchedule = nil
	t.Cleanup(func() { defaultTerminalRetrySchedule = schedule })
	queueReport := func(peer *h5Peer, task *Task, output string) {
		t.Helper()
		peer.daemon.client.client.Transport = h5Transport{}
		if err := peer.daemon.reportTerminalTask(ctx, terminalTaskReport{kind: terminalTaskReportComplete, taskID: task.ID, output: output}); err == nil {
			t.Fatal("offline send succeeded")
		}
		items, err := peer.daemon.terminalReports.list()
		h5Check(t, err)
		if len(items) != 1 || items[0].report.taskID != task.ID || items[0].report.output != output {
			t.Fatal("outbox did not retain original report")
		}
	}
	queueReport(&a, old, c1)
	markOffline := func(peer *h5Peer, age time.Duration) {
		t.Helper()
		_, err := pool.Exec(ctx, "UPDATE agent_runtime SET last_seen_at=now()-make_interval(secs=>$2) WHERE id=$1", peer.runtime, age.Seconds())
		h5Check(t, err)
		offline, err := q.MarkRuntimesOfflineByIDs(ctx, db.MarkRuntimesOfflineByIDsParams{Ids: []pgtype.UUID{h5ID(t, peer.runtime)}, StaleSeconds: 30})
		h5Check(t, err)
		if len(offline) != 1 {
			t.Fatal("runtime offline transition missing")
		}
	}
	sweep := func(task *Task, wantExpired bool) {
		t.Helper()
		expired, err := h.TaskService.FailTasksForOfflineRuntimes(ctx, db.FailTasksForOfflineRuntimesParams{ReconnectGraceSecs: 1200, MaxPerTick: 100})
		h5Check(t, err)
		found := false
		for _, row := range expired {
			if util.UUIDToString(row.ID) == task.ID {
				found = true
			}
		}
		if found != wantExpired {
			t.Fatalf("unexpected offline-grace outcome: expired=%v", found)
		}
		h.TaskService.HandleFailedTasks(ctx, expired)
	}
	markOffline(&a, 2*time.Minute)
	sweep(old, false)
	assertState(old, "running", "", 0)
	before, err := b.daemon.client.ClaimTask(ctx, b.runtime)
	h5Check(t, err)
	if before != nil {
		t.Fatal("B found a run before explicit dispatch")
	}
	current := makeRun(b, patB, bob, "C2")
	if current.ID == old.ID || current.AuthToken == old.AuthToken {
		t.Fatal("tasks or task credentials shared")
	}
	get := func(path string, want int) []byte { return c.request("GET", path, current.AuthToken, "", nil, want) }
	get("/api/issues/"+issue, 200)
	get("/api/issues/"+privateIssue, 404)
	restored := get("/api/attachments/"+published+"/download", 200)
	if !bytes.Equal(restored, data) {
		t.Fatal("download is not the published workbook")
	}
	get("/api/attachments/"+hidden+"/download", 404)
	get("/api/runtimes/"+a.runtime+"/usage", 404)
	get("/api/runtimes/"+b.runtime+"/usage", 200)
	hash := fmt.Sprintf("%x", sha256.Sum256(data))
	c2 = checkIndependentReceiver(t, ctx, c2, map[string]any{"base_url": srv.URL, "token": current.AuthToken, "workspace": issueWS, "target": issue, "private_issue": privateIssue, "published": published, "unshared": hidden, "runtime_a": a.runtime, "runtime_b": b.runtime, "size": len(data), "sha256": hash})
	t.Logf("A offline with pending C1; B initially no task then member mention produced a distinct run. B task: own Runtime/visible Issue/attachment HTTP 200; A Runtime/hidden Issue/identical hidden attachment HTTP 404. Received %d bytes sha256=%s", len(data), hash)
	h5Check(t, b.daemon.reportTerminalTask(ctx, terminalTaskReport{kind: terminalTaskReportComplete, taskID: current.ID, output: c2}))
	assertState(current, "completed", c2, 1)
	assertState(old, "running", "", 0)
	reconnect := func(p *h5Peer) {
		t.Helper()
		p.daemon = New(p.cfg, logger)
		p.daemon.client.SetToken(p.token)
		_, err := p.daemon.client.SendHeartbeat(ctx, p.runtime)
		h5Check(t, err)
		pending, delivered := p.daemon.replayPendingTerminalReports(ctx)
		if pending != 0 || delivered != 1 {
			t.Fatalf("replay pending=%d, delivered=%d", pending, delivered)
		}
	}
	reconnect(&a)
	assertState(old, "completed", c1, 1)
	assertState(current, "completed", c2, 1)
	h5Check(t, a.daemon.client.CompleteTask(ctx, old.ID, c1, "", "", "", false, "", ""))
	assertState(old, "completed", c1, 1)
	assertState(current, "completed", c2, 1)
	t.Log("new A daemon loaded the original outbox; after B had completed, live C1 was attached only to its own task, 1 comment per task after duplicate replay")
	blocked := makeRun(a, patV, verifier, "C1 cancellation control")
	queueReport(&a, blocked, c1)
	c.post("POST", "/api/runtimes/"+a.runtime+"/revoke-workspace-access", patA, map[string]any{"shared_with": []string{}, "expected_nonowner_agent_ids": []string{a.agent}, "expected_task_ids": []string{blocked.ID}}, 200)
	c.request("GET", "/api/issues/"+issue, blocked.AuthToken, "", nil, 401)
	assertState(blocked, "cancelled", "", 0)
	reconnect(&a)
	assertState(blocked, "cancelled", "", 0)
	assertState(current, "completed", c2, 1)
	t.Log("share revoked while A queued a report: task credential 401, machine replay acknowledged, old task remains cancelled, late comments zero, B preserved")
	expired := makeRun(b, patB, bob, "grace-expiration control")
	queueReport(&b, expired, c1)
	markOffline(&b, 21*time.Minute)
	sweep(expired, true)
	var reason string
	h5Check(t, pool.QueryRow(ctx, "SELECT failure_reason FROM agent_task_queue WHERE id=$1", expired.ID).Scan(&reason))
	if reason != "runtime_offline" {
		t.Fatal("wrong terminal reason after grace")
	}
	var childCount int
	h5Check(t, pool.QueryRow(ctx, "SELECT count(*) FROM agent_task_queue WHERE parent_task_id=$1 AND retry_of_task_id=$1 AND agent_id=$2 AND status='deferred' AND attempt=2", expired.ID, b.agent).Scan(&childCount))
	if childCount != 1 {
		t.Fatal("expected a same-agent deferred retry")
	}
	var beforeReplay int
	err = pool.QueryRow(ctx, "SELECT count(*) FROM comment WHERE source_task_id=$1", expired.ID).Scan(&beforeReplay)
	h5Check(t, err)
	reconnect(&b)
	assertState(expired, "failed", "", beforeReplay)
	assertState(current, "completed", c2, 1)
	t.Logf("fixture grace 20m, last heartbeat age 21m: runtime_offline failure persisted after machine replay; source comments remained %d; one deferred second attempt for the same agent", beforeReplay)

}

// The optional Python receiver runs as another process against the same HTTP server.
// The input file exists only in the mode-0700 temp directory for this test.
func checkIndependentReceiver(t *testing.T, ctx context.Context, expectedReport string, req map[string]any) string {
	t.Helper()
	script := os.Getenv("AP5_RECEIVER_SCRIPT")
	if script == "" {
		return expectedReport
	}
	root := t.TempDir()
	ids := map[string]string{}
	for _, n := range []string{"net", "pid", "mnt"} {
		id, err := os.Readlink("/proc/self/ns/" + n)
		h5Check(t, err)
		ids[n] = fmt.Sprintf("%x", sha256.Sum256([]byte(id)))[:16]
	}
	req["namespaces"] = ids
	file := filepath.Join(root, "b-request.json")
	raw, err := json.Marshal(req)
	h5Check(t, err)
	h5Check(t, os.WriteFile(file+".tmp", raw, 0600))
	h5Check(t, os.Rename(file+".tmp", file))
	defer os.Remove(file)
	cmd := exec.CommandContext(ctx, "python3", script, root)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("B receiver exited: %v: %s", err, out)
	}
	var got struct {
		Target        int
		PrivateIssue  int `json:"private_issue"`
		Published     int
		Unshared      int
		RuntimeA      int `json:"runtime_a"`
		RuntimeB      int `json:"runtime_b"`
		Sha256        string
		Size          int
		Different     map[string]bool `json:"different_namespace"`
		CurrentReport *string         `json:"current_report"`
	}
	data, err := os.ReadFile(filepath.Join(root, "b-result.json"))
	h5Check(t, err)
	h5Check(t, json.Unmarshal(data, &got))
	if got.Target != 200 || got.PrivateIssue != 404 || got.Published != 200 || got.Unshared != 404 || got.RuntimeA != 404 || got.RuntimeB != 200 || got.Sha256 != req["sha256"] || got.Size != req["size"] {
		t.Fatal("independent B receiver observations mismatch")
	}
	t.Logf("separate Python receiver verified six HTTP reads, workbook digest and ZIP structure; distinct kernel namespaces=%v", got.Different)
	if got.CurrentReport != nil {
		if *got.CurrentReport != expectedReport {
			t.Fatal("receiver supplied a different C2 report")
		}
		t.Log("received exact C2 report from B; passing it to the native B daemon terminal callback")
		return *got.CurrentReport
	}
	return expectedReport
}
