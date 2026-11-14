package phase3auth_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/multica-ai/multica/server/internal/analytics"
	authlib "github.com/multica-ai/multica/server/internal/auth"
	"github.com/multica-ai/multica/server/internal/events"
	"github.com/multica-ai/multica/server/internal/handler"
	"github.com/multica-ai/multica/server/internal/middleware"
	"github.com/multica-ai/multica/server/internal/realtime"
	"github.com/multica-ai/multica/server/internal/service"
	"github.com/multica-ai/multica/server/internal/testutil"
	db "github.com/multica-ai/multica/server/pkg/db/generated"
)

func TestPhase3SharedRunIdentity(t *testing.T) {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		t.Fatal("set DATABASE_URL to a disposable migrated PostgreSQL database")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	q := db.New(pool)
	hub := realtime.NewHub()
	go hub.Run()
	h := handler.New(q, pool, hub, events.New(), service.NewEmailService(), nil, nil, analytics.NoopClient{}, handler.Config{})

	seed := testutil.New(pool, "", "")
	suffix := uuid.NewString()
	owner := seed.User(t, "Runtime owner", "owner-"+suffix+"@example.test")
	issuer := seed.User(t, "Verifier", "verify-"+suffix+"@example.test")
	ws := seed.Workspace(t, "Order validation fixture", "observation-"+suffix, testutil.Cols{"issue_prefix": "ORD"})
	fx := testutil.New(pool, ws, owner)
	fx.Member(t, ws, owner, "owner")
	fx.Member(t, ws, issuer, "member")
	rt := fx.Runtime(t, "Shared Runtime", testutil.Cols{"runtime_mode": "local", "provider": "claude"})
	agent := fx.Agent(t, "Order verifier", rt, testutil.Cols{"owner_id": issuer, "runtime_mode": "local"})
	target := fx.Issue(t, "Verify C2 under D2", testutil.Cols{"description": "D2 includes payment time. Check the A3 payment-time column on C2."})
	peer := fx.Issue(t, "Coordinate the same C2 candidate")
	excluded := fx.Project(t, "Private project", testutil.Cols{"visibility": "private"})
	personal := fx.Issue(t, "Private project item", testutil.Cols{"project_id": excluded})

	call := func(method, path string, responder http.Handler, payload any, member, token, param, id string, want int) []byte {
		t.Helper()
		var body bytes.Buffer
		if payload != nil {
			if err := json.NewEncoder(&body).Encode(payload); err != nil {
				t.Fatal(err)
			}
		}
		req := testutil.WithURLParams(httptest.NewRequest(method, path, &body), param, id)
		req.Header.Set("Content-Type", "application/json")
		if token != "" {
			req.Header.Set("Authorization", "Bearer "+token)
		}
		if member != "" {
			req.Header.Set("X-User-ID", member)
			req.Header.Set("X-Workspace-ID", ws)
		}
		res := httptest.NewRecorder()
		responder.ServeHTTP(res, req)
		if res.Code != want {
			t.Fatalf("%s %s: HTTP %d, expected %d", method, path, res.Code, want)
		}
		return res.Body.Bytes()
	}
	// Runtime owner/daemon endpoints receive the authenticated-member context in these handler tests.
	// Business requests below go through the real middleware with the opaque token minted at claim.
	control := func(method, path string, f http.HandlerFunc, payload any, param, id string) []byte {
		return call(method, path, f, payload, owner, "", param, id, http.StatusOK)
	}
	control("PATCH", "/api/runtimes/"+rt, h.UpdateAgentRuntime, map[string]any{"shared_with": []string{issuer}}, "runtimeId", rt)
	task := fx.Task(t, agent, testutil.Cols{"runtime_id": rt, "issue_id": target, "status": "queued", "originator_user_id": issuer, "accountable_user_id": issuer})
	claim := control("POST", "/api/daemon/runtimes/"+rt+"/tasks/claim", h.ClaimTaskByRuntime, nil, "runtimeId", rt)
	var delivered struct {
		Task struct {
			ID        string
			AuthToken string `json:"auth_token"`
		}
	}
	if err := json.Unmarshal(claim, &delivered); err != nil {
		t.Fatal(err)
	}
	if delivered.Task.ID != task || delivered.Task.AuthToken == "" {
		t.Fatal("expected claim and task-scoped credential")
	}
	var dispatched time.Time
	var tokenUser, sourceUser string
	err = pool.QueryRow(ctx, `SELECT atq.dispatched_at, tt.user_id::text, atq.originator_user_id::text
        FROM agent_task_queue atq JOIN task_token tt ON tt.task_id=atq.id WHERE atq.id=$1`, task).Scan(&dispatched, &tokenUser, &sourceUser)
	if err != nil || tokenUser != owner || sourceUser != issuer {
		t.Fatal("task identity mismatch", err)
	}
	control("POST", "/api/daemon/tasks/"+task+"/start", h.StartTask, map[string]any{"runtime_id": rt, "dispatched_at": dispatched.Format(time.RFC3339Nano)}, "taskId", task)
	auth := middleware.Auth(q, nil, nil, nil)
	material := call("GET", "/api/issues/"+target, auth(http.HandlerFunc(h.GetIssue)), nil, "", delivered.Task.AuthToken, "id", target, 200)
	if !bytes.Contains(material, []byte("D2 includes payment time")) {
		t.Fatal("expected C2/D2 issue context")
	}

	report := []byte(`{"results":{"multica-materialized":{"payment_time_check":false}}}`)
	reportSource := "embedded_fixture"
	if path := os.Getenv("AP_CANDIDATE_REPORT"); path != "" {
		report, err = os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		reportSource = "supplied_report"
	}
	var observation struct {
		Results map[string]struct {
			PaymentTimeCheck *bool `json:"payment_time_check"`
		} `json:"results"`
	}
	if err := json.Unmarshal(report, &observation); err != nil {
		t.Fatal(err)
	}
	payment := observation.Results["multica-materialized"].PaymentTimeCheck
	if payment == nil {
		t.Fatal("missing multica-materialized.payment_time_check")
	}
	digest := sha256.Sum256(report)
	receipt := fmt.Sprintf("C2/D2 candidate report sha256=%x payment_time_check=%t", digest, *payment)
	for _, entry := range []struct{ issue, content string }{
		{target, receipt},
		{peer, "Coordinate C2 verification on the originating Issue."},
	} {
		issue := entry.issue
		body := call("POST", "/api/issues/"+issue+"/comments", auth(http.HandlerFunc(h.CreateComment)), map[string]any{"content": entry.content}, "", delivered.Task.AuthToken, "id", issue, 201)
		var posted handler.CommentResponse
		if err := json.Unmarshal(body, &posted); err != nil {
			t.Fatal(err)
		}
		if posted.Content != entry.content || posted.IssueID != issue || posted.AuthorType != "agent" || posted.AuthorID != agent || posted.SourceTaskID == nil || *posted.SourceTaskID != task {
			t.Fatal("unexpected report provenance")
		}
	}
	listed := call("GET", "/api/issues/"+target+"/comments", auth(http.HandlerFunc(h.ListComments)), nil, "", delivered.Task.AuthToken, "id", target, 200)
	var comments []handler.CommentResponse
	if err := json.Unmarshal(listed, &comments); err != nil {
		t.Fatal(err)
	}
	found := false
	for _, comment := range comments {
		if comment.Content == receipt && comment.IssueID == target && comment.AuthorID == agent && comment.SourceTaskID != nil && *comment.SourceTaskID == task {
			found = true
			break
		}
	}
	if !found {
		t.Fatal("source Issue did not return the submitted digest, result and task identity")
	}
	t.Logf("%s: source Issue read back candidate sha256=%x payment_time_check=%t", reportSource, digest, *payment)
	call("GET", "/api/issues/"+personal, auth(http.HandlerFunc(h.GetIssue)), nil, "", delivered.Task.AuthToken, "id", personal, 404)
	t.Log("C2/D2 read 200; source and authorized peer Issue comments 201 with same Agent and source task; private project read 404")

	// Compare an expired fixture and the live claim token while the same task is running.
	expired, err := authlib.GenerateAgentTaskToken()
	if err != nil {
		t.Fatal(err)
	}
	fx.Insert(t, "task_token", testutil.Cols{"id": uuid.NewString(), "token_hash": authlib.HashToken(expired), "workspace_id": ws, "agent_id": agent, "task_id": task, "user_id": owner, "expires_at": time.Now().Add(-time.Minute)})
	call("GET", "/api/issues/"+target, auth(http.HandlerFunc(h.GetIssue)), nil, "", expired, "id", target, 401)
	call("GET", "/api/issues/"+target, auth(http.HandlerFunc(h.GetIssue)), nil, "", delivered.Task.AuthToken, "id", target, 200)
	t.Log("expiry control on active Run: aged fixture 401, live claim token 200")

	control("POST", "/api/runtimes/"+rt+"/revoke-workspace-access", h.RevokeRuntimeWorkspaceAccess,
		map[string]any{"shared_with": []string{}, "expected_nonowner_agent_ids": []string{agent}, "expected_task_ids": []string{task}}, "runtimeId", rt)
	var status string
	var bound bool
	var activeCredentialRows int
	err = pool.QueryRow(ctx, `SELECT t.status,a.runtime_id IS NOT NULL,
        (SELECT count(*) FROM task_token WHERE task_id=t.id AND expires_at>now())
        FROM agent_task_queue t JOIN agent a ON a.id=t.agent_id WHERE t.id=$1`, task).Scan(&status, &bound, &activeCredentialRows)
	if err != nil || status != "cancelled" || bound || activeCredentialRows != 0 {
		t.Fatal("unexpected revocation state", status, bound, err)
	}
	call("GET", "/api/runtimes/"+rt+"/usage", http.HandlerFunc(h.GetRuntimeUsage), nil, issuer, "", "runtimeId", rt, 404)
	t.Logf("revocation: task cancelled, Agent unbound, former recipient Runtime read 404; unexpired token rows at observation: %d", activeCredentialRows)

	call("GET", "/api/issues/"+target, auth(http.HandlerFunc(h.GetIssue)), nil, "", delivered.Task.AuthToken, "id", target, 401)
	call("POST", "/api/issues/"+target+"/comments", auth(http.HandlerFunc(h.CreateComment)), map[string]any{"content": "late fixture receipt"}, "", delivered.Task.AuthToken, "id", target, 401)
	var late int
	if err := pool.QueryRow(ctx, `SELECT count(*) FROM comment WHERE issue_id=$1 AND content=$2`, target, "late fixture receipt").Scan(&late); err != nil || late != 0 {
		t.Fatal("late receipt was accepted", err)
	}
	t.Log("revoked credential: previous Issue read and report both 401, late rows 0")
}
