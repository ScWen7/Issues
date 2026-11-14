package phase4artifact_test

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
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
	db "github.com/multica-ai/multica/server/pkg/db/generated"
)

// Compare Multica's Issue attachment with the producer bytes. Identity and scope
// are seeded in a disposable database; all HTTP operations use its task token.
func TestOrderWorkbookIssueAttachment(t *testing.T) {
	workbook, err := os.ReadFile(os.Getenv("AP_ORDER_WORKBOOK"))
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, os.Getenv("DATABASE_URL"))
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	q := db.New(pool)
	seed := testutil.New(pool, "", "")
	tag := uuid.NewString()
	owner := seed.User(t, "Order verifier", tag+"@example.test")
	ws := seed.Workspace(t, "Orders", "orders-"+tag, testutil.Cols{"issue_prefix": "ORD"})
	fx := testutil.New(pool, ws, owner)
	fx.Member(t, ws, owner, "owner")
	rt := fx.Runtime(t, "Test runner")
	actor := fx.Agent(t, "Validator", rt, testutil.Cols{"owner_id": owner})
	issue := fx.Issue(t, "C2 export")
	run := fx.Task(t, actor, testutil.Cols{"runtime_id": rt, "issue_id": issue, "status": "running", "originator_user_id": owner, "accountable_user_id": owner})
	token, err := authlib.GenerateAgentTaskToken()
	if err != nil {
		t.Fatal(err)
	}
	fx.Insert(t, "task_token", testutil.Cols{"id": uuid.NewString(), "token_hash": authlib.HashToken(token), "workspace_id": ws, "agent_id": actor, "task_id": run, "user_id": owner, "expires_at": time.Now().Add(time.Hour)})
	t.Setenv("LOCAL_UPLOAD_DIR", t.TempDir())
	t.Setenv("LOCAL_UPLOAD_BASE_URL", "")
	hub := realtime.NewHub()
	go hub.Run()
	h := handler.New(q, pool, hub, events.New(), service.NewEmailService(), nil, nil, analytics.NoopClient{}, handler.Config{AttachmentDownloadMode: "proxy"})
	h.Storage = storage.NewLocalStorageFromEnv()
	routes := chi.NewRouter()
	routes.Use(middleware.Auth(q, nil, nil, nil))
	routes.Post("/api/upload-file", h.UploadFile)
	routes.Get("/api/attachments/{id}/download", h.DownloadAttachment)
	server := httptest.NewServer(routes)
	defer server.Close()
	client := server.Client()
	upload := func() string {
		t.Helper()
		var form bytes.Buffer
		writer := multipart.NewWriter(&form)
		if err := writer.WriteField("issue_id", issue); err != nil {
			t.Fatal(err)
		}
		part, err := writer.CreateFormFile("file", "orders.xlsx")
		if err != nil {
			t.Fatal(err)
		}
		if _, err := part.Write(workbook); err != nil {
			t.Fatal(err)
		}
		if err := writer.Close(); err != nil {
			t.Fatal(err)
		}
		req, err := http.NewRequest(http.MethodPost, server.URL+"/api/upload-file", &form)
		if err != nil {
			t.Fatal(err)
		}
		req.Header.Set("Content-Type", writer.FormDataContentType())
		req.Header.Set("Authorization", "Bearer "+token)
		res, err := client.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if res.StatusCode != 200 {
			t.Fatalf("upload HTTP %d", res.StatusCode)
		}
		var meta handler.AttachmentResponse
		if err := json.NewDecoder(res.Body).Decode(&meta); err != nil {
			t.Fatal(err)
		}
		if meta.ID == "" || meta.IssueID == nil || *meta.IssueID != issue || meta.UploaderType != "agent" || meta.UploaderID != actor || meta.SizeBytes != int64(len(workbook)) {
			t.Fatal("wrong attachment identity, issue, actor or length")
		}
		return meta.ID
	}
	before := upload()
	req, err := http.NewRequest(http.MethodGet, server.URL+"/api/attachments/"+before+"/download", nil)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Authorization", "Bearer "+token)
	res, err := client.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	body, err := io.ReadAll(res.Body)
	if err != nil || res.StatusCode != 200 || !bytes.Equal(body, workbook) {
		t.Fatalf("download HTTP %d; source byte equality=%t; error=%v", res.StatusCode, bytes.Equal(body, workbook), err)
	}
	again := upload()
	if before == again {
		t.Fatal("expected separate attachment identities on two native uploads")
	}
	t.Logf("Issue attachment round trip %d bytes sha256=%x; uploader=agent; two uploads produced distinct attachment IDs", len(body), sha256.Sum256(body))
}
