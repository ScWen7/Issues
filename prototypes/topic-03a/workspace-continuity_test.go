// Integration tests for a fixed Multica checkout. See workspace-continuity.md.
package workspace_test

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/multica-ai/multica/server/internal/analytics"
	"github.com/multica-ai/multica/server/internal/daemon/execenv"
	"github.com/multica-ai/multica/server/internal/events"
	"github.com/multica-ai/multica/server/internal/handler"
	"github.com/multica-ai/multica/server/internal/realtime"
	"github.com/multica-ai/multica/server/internal/service"
	"github.com/multica-ai/multica/server/internal/testutil"
	db "github.com/multica-ai/multica/server/pkg/db/generated"
)

var log = slog.New(slog.NewTextHandler(io.Discard, nil))

// The parent holds the env root lock. The child runs the same JSON helper
// entry point as the real daemon's short-lived prepare / reuse subprocess.
func TestMain(m *testing.M) {
	if len(os.Args) == 2 && os.Args[1] == "prepare-helper" {
		if err := execenv.RunPreparationHelper(os.Stdin, os.Stdout, log); err != nil {
			os.Stderr.WriteString(err.Error())
			os.Exit(1)
		}
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func id(value string) pgtype.UUID {
	return pgtype.UUID{Bytes: uuid.MustParse(value), Valid: true}
}

func git(t *testing.T, dir string, args ...string) string {
	t.Helper()
	out, err := exec.Command("git", append([]string{"-C", dir}, args...)...).CombinedOutput()
	if err != nil {
		t.Fatalf("git %v: %v: %s", args, err, out)
	}
	return strings.TrimSpace(string(out))
}

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func exists(t *testing.T, path string, expected bool) {
	t.Helper()
	_, err := os.Stat(path)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		t.Fatal(err)
	}
	if (err == nil) != expected {
		t.Fatalf("exists(%s)=%v, want %v", path, err == nil, expected)
	}
}

func TestReclaimedGenerationAndExistingWorktree(t *testing.T) {
	ctx := context.Background()
	if os.Getenv("DATABASE_URL") == "" {
		t.Fatal("set DATABASE_URL to a disposable migrated PostgreSQL database")
	}
	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	must(t, err)
	t.Cleanup(pool.Close)
	q := db.New(pool)
	seed := testutil.New(pool, "", "")
	user := seed.User(t, "Workspace test", uuid.NewString()+"@example.test")
	ws := seed.Workspace(t, "Workspace fixture", uuid.NewString(), testutil.Cols{"issue_prefix": "WKP"})
	fx := testutil.New(pool, ws, user)
	fx.Member(t, ws, user, "owner")
	rt := fx.Runtime(t, "Local runtime", testutil.Cols{"runtime_mode": "local", "provider": "claude"})
	main := fx.Agent(t, "Verifier", rt, testutil.Cols{"runtime_mode": "local", "max_concurrent_tasks": 3})
	peer := fx.Agent(t, "Peer", rt, testutil.Cols{"runtime_mode": "local"})
	issue := fx.Issue(t, "Order export verification")
	queue := func(agent string) string {
		return fx.Task(t, agent, testutil.Cols{"runtime_id": rt, "issue_id": issue, "originator_user_id": user, "accountable_user_id": user})
	}
	first := queue(main)
	claim := func(agent string, lease float64) (db.AgentTaskQueue, error) {
		return q.ClaimAgentTask(ctx, db.ClaimAgentTaskParams{
			AgentID: id(agent), RuntimeID: id(rt), PrepareLeaseSecs: lease, RuntimeStaleSecs: 150,
		})
	}
	// Short test durations exercise the actual clock predicates without editing
	// timestamps. Production defaults for initial leases and recovery differ.
	old, err := claim(main, 0.025)
	must(t, err)
	if old.ID != id(first) {
		t.Fatal("wrong first claim")
	}
	waiting := fx.Task(t, main, testutil.Cols{
		"runtime_id": rt, "issue_id": issue, "originator_user_id": user, "accountable_user_id": user,
		"trigger_comment_id": fx.Comment(t, issue, "Second independent discussion"),
	})
	if _, err := claim(main, 45); !errors.Is(err, pgx.ErrNoRows) {
		t.Fatalf("same Issue/same Agent second claim: %v", err)
	}
	queued, err := q.GetAgentTask(ctx, id(waiting))
	must(t, err)
	if queued.Status != "queued" {
		t.Fatal("waiting task lost its queue position")
	}
	peerTask := queue(peer)
	other, err := claim(peer, 45)
	must(t, err)
	if other.ID != id(peerTask) {
		t.Fatal("different Agent could not claim its own node")
	}

	source := t.TempDir()
	git(t, source, "init", "-q", "-b", "main")
	git(t, source, "config", "user.email", "author@example.test")
	git(t, source, "config", "user.name", "Author")
	must(t, os.WriteFile(filepath.Join(source, "base.txt"), []byte("accepted base\n"), 0644))
	git(t, source, "add", "base.txt")
	git(t, source, "commit", "-qm", "baseline")
	base := git(t, source, "rev-parse", "HEAD")
	local := func() (string, string) {
		root, checkout := t.TempDir(), filepath.Join(t.TempDir(), "source")
		git(t, source, "clone", "--no-local", "--quiet", source, checkout)
		return root, checkout
	}
	oldRoot, oldRepo := local()
	newRoot, newRepo := local()
	envKey := func(root string) execenv.RootDirParams {
		return execenv.RootDirParams{WorkspacesRoot: root, WorkspaceID: ws, TaskID: first, IssueIdentifier: "ORD-4"}
	}
	oldLock, err := execenv.ClaimEnvRoot(envKey(oldRoot))
	must(t, err)
	defer oldLock.Release()

	hub := realtime.NewHub()
	go hub.Run()
	h := handler.New(q, pool, hub, events.New(), service.NewEmailService(), nil, nil, analytics.NoopClient{}, handler.Config{})
	callback := func(generation db.AgentTaskQueue, want int) {
		// Start handler receives a fixture-authenticated daemon owner.
		body, err := json.Marshal(map[string]string{"runtime_id": rt, "dispatched_at": generation.DispatchedAt.Time.UTC().Format(time.RFC3339Nano)})
		must(t, err)
		req := testutil.WithURLParams(httptest.NewRequest("POST", "/api/daemon/tasks/"+first+"/start", bytes.NewReader(body)), "taskId", first)
		req.Header.Set("X-User-ID", user)
		req.Header.Set("X-Workspace-ID", ws)
		w := httptest.NewRecorder()
		h.StartTask(w, req)
		if w.Code != want {
			t.Fatalf("Start = %d, want %d: %s", w.Code, want, w.Body.String())
		}
	}

	// A holds its directory but has not finished preparing. B recovers the same
	// task with a fresh generation and begins work in a separate filesystem root.
	var fresh db.AgentTaskQueue
	deadline := time.Now().Add(3 * time.Second)
	for {
		fresh, err = q.ReclaimStaleDispatchedTaskForRuntime(ctx, db.ReclaimStaleDispatchedTaskForRuntimeParams{
			RuntimeID: id(rt), PrepareLeaseSecs: 45, ClaimRecoverySecs: 0.025, RuntimeStaleSecs: 150,
		})
		if err == nil {
			break
		}
		if !errors.Is(err, pgx.ErrNoRows) || time.Now().After(deadline) {
			t.Fatalf("reclaim: %v", err)
		}
		time.Sleep(5 * time.Millisecond)
	}
	if fresh.ID != old.ID || !fresh.DispatchedAt.Time.After(old.DispatchedAt.Time) {
		t.Fatal("expected a new generation of same Task")
	}
	duplicate, err := execenv.ClaimEnvRoot(envKey(oldRoot))
	if err == nil {
		duplicate.Release()
		t.Fatal("two active parents claimed same root")
	}
	newLock, err := execenv.ClaimEnvRoot(envKey(newRoot))
	must(t, err)
	defer newLock.Release()
	prepare := func(root, repo string) *execenv.Environment {
		e, err := execenv.PrepareIsolated(ctx, []string{os.Args[0], "prepare-helper"}, execenv.PrepareParams{
			WorkspacesRoot: root, WorkspaceID: ws, TaskID: first, IssueIdentifier: "ORD-4", AgentName: "Verifier",
			Provider: "claude", EnvRootPreclaimed: true, Task: execenv.TaskContextForEnv{AgentID: main, IssueID: issue},
			LocalWorktree: &execenv.LocalWorktreeParams{LocalPath: repo},
		}, log)
		must(t, err)
		if e.LocalWorktree == nil {
			t.Fatal("missing Git worktree")
		}
		return e
	}
	current := prepare(newRoot, newRepo)
	callback(fresh, 200)
	// Release the old helper after B started. A's local prepare still
	// materializes its own marker; the subsequent server Start rejects A.
	late := prepare(oldRoot, oldRepo)
	exists(t, filepath.Join(late.WorkDir, execenv.TaskContextMarkerRelPath), true)
	callback(old, 409)
	// Once Prepare returned, runTask defers cleanup of configuration and
	// sidecars and Finalize, including when Start is rejected before launch.
	must(t, execenv.CleanupRuntimeConfig(late.WorkDir, "claude"))
	must(t, execenv.CleanupSidecars(late.RootDir))
	abandoned, err := late.LocalWorktree.Finalize(log)
	must(t, err)
	if abandoned.Branch != "" {
		t.Fatal("unstarted run delivered a branch")
	}
	if git(t, oldRepo, "branch", "--list", late.LocalWorktree.Branch) != "" {
		t.Fatal("old empty task branch still exists")
	}
	exists(t, late.WorkDir, false)
	exists(t, current.WorkDir, true)
	must(t, os.WriteFile(filepath.Join(current.WorkDir, "candidate.txt"), []byte("C2 accepted input\n"), 0644))
	must(t, execenv.CleanupRuntimeConfig(current.WorkDir, "claude"))
	must(t, execenv.CleanupSidecars(current.RootDir))
	outcome, err := current.LocalWorktree.Finalize(log)
	must(t, err)
	if outcome.Branch == "" || git(t, newRepo, "diff", "--name-only", base, outcome.Branch) != "candidate.txt" {
		t.Fatal("unexpected branch delivery")
	}
	state, err := q.GetAgentTask(ctx, id(first))
	must(t, err)
	if state.Status != "running" || !state.DispatchedAt.Time.Equal(fresh.DispatchedAt.Time) {
		t.Fatal("late start changed active task")
	}
	if git(t, oldRepo, "rev-parse", "HEAD") != base || git(t, newRepo, "rev-parse", "HEAD") != base {
		t.Fatal("a source checkout moved")
	}
	t.Log("same Issue/same Agent queued; peer Agent dispatched; overlapping same-root claim refused")
	t.Log("fresh Start 200; old helper wrote its marker locally after new Start; old Start 409; old empty branch dropped at Finalize; new branch contains only candidate.txt")
}

func TestManagedDirectoryReuse(t *testing.T) {
	root := t.TempDir()
	task, agent, issue := uuid.NewString(), uuid.NewString(), uuid.NewString()
	r := execenv.RootDirParams{WorkspacesRoot: root, WorkspaceID: uuid.NewString(), TaskID: task, IssueIdentifier: "ORD-4"}
	holder, err := execenv.ClaimEnvRoot(r)
	must(t, err)
	defer holder.Release()
	cli := []string{os.Args[0], "prepare-helper"}
	tc := execenv.TaskContextForEnv{AgentID: agent, IssueID: issue}
	env, err := execenv.PrepareIsolated(context.Background(), cli, execenv.PrepareParams{
		WorkspacesRoot: root, WorkspaceID: r.WorkspaceID, TaskID: task, IssueIdentifier: r.IssueIdentifier,
		Provider: "claude", Task: tc, EnvRootPreclaimed: true,
	}, log)
	must(t, err)
	artifact := filepath.Join(env.WorkDir, "checkpoint.txt")
	must(t, os.WriteFile(artifact, []byte("C1 workspace checkpoint"), 0644))
	wsroot, err := os.OpenRoot(root)
	must(t, err)
	defer wsroot.Close()
	rel, err := filepath.Rel(root, env.RootDir)
	must(t, err)
	lock, _, err := execenv.LockEnvRootForReuse(wsroot, rel, env.RootDir)
	if err == nil {
		lock.Release()
		t.Fatal("active predecessor lost its directory")
	}
	if !errors.Is(err, execenv.ErrEnvRootBusy) {
		t.Fatalf("unexpected lock error: %v", err)
	}
	holder.Release()
	lock, _, err = execenv.LockEnvRootForReuse(wsroot, rel, env.RootDir)
	must(t, err)
	defer lock.Release()
	reused, err := execenv.ReuseIsolated(context.Background(), cli, execenv.ReuseParams{WorkspacesRoot: root, WorkDir: env.WorkDir, Provider: "claude", Task: tc}, log)
	must(t, err)
	if reused == nil || reused.WorkDir != env.WorkDir {
		t.Fatal("managed path not reused")
	}
	contents, err := os.ReadFile(filepath.Join(reused.WorkDir, "checkpoint.txt"))
	must(t, err)
	if string(contents) != "C1 workspace checkpoint" {
		t.Fatal("local checkpoint lost")
	}
	t.Log("live parent excluded reuse; after release, the isolated reuse helper preserved the local checkpoint")
}
