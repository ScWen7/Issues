package runner

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"agentflow/internal/domain"
)

// Exercise the runner's ordinary named-output completion path with the order
// fixture's workbook and a UTF-8 control. The loopback peer records decoded bytes.
func TestOrderWorkbookRunnerTransport(t *testing.T) {
	workbook, err := os.ReadFile(os.Getenv("AP_ORDER_WORKBOOK"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := zip.NewReader(bytes.NewReader(workbook), int64(len(workbook))); err != nil {
		t.Fatal(err)
	}
	text := []byte("C2 付款时间核验\n")
	dir := t.TempDir()
	for name, body := range map[string][]byte{"order.xlsx": workbook, "summary.txt": text} {
		if err := os.WriteFile(filepath.Join(dir, name), body, 0600); err != nil {
			t.Fatal(err)
		}
	}
	output := collectTaskOutputs(dir, &domain.RunnerInvocation{
		ReportOutputs: true, OutputFiles: []string{"order.xlsx", "summary.txt"},
	})
	if !bytes.Equal([]byte(output.Files["order.xlsx"]), workbook) {
		t.Fatal("runner collected different bytes")
	}
	received := make(chan CompleteRequest, 1)
	peer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/runners/tasks/probe/complete" {
			w.WriteHeader(404)
			return
		}
		var body CompleteRequest
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}
		received <- body
		w.WriteHeader(204)
	}))
	defer peer.Close()
	code := 0
	if err := NewClient(peer.URL).Complete(context.Background(), "probe", CompleteRequest{
		Status: "succeeded", ExitCode: &code, Outputs: output,
	}); err != nil {
		t.Fatal(err)
	}
	decoded := (<-received).Outputs.Files
	if !bytes.Equal([]byte(decoded["summary.txt"]), text) {
		t.Fatal("UTF-8 control changed in transport")
	}
	after := []byte(decoded["order.xlsx"])
	_, zipErr := zip.NewReader(bytes.NewReader(after), int64(len(after)))
	t.Logf("runner input %d bytes sha256=%x; decoded %d bytes sha256=%x; ZIP directory readable=%t",
		len(workbook), sha256.Sum256(workbook), len(after), sha256.Sum256(after), zipErr == nil)
	if bytes.Equal(after, workbook) {
		t.Fatal("fixture did not reproduce the measured workbook/text transport difference")
	}
}
