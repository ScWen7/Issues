package runtime

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"agentflow/internal/domain"
)

// Both services are permitted lab inputs. Only the project service is the
// authoritative source for this order check.
func TestOrderAliasNeedsUniqueService(t *testing.T) {
	newService := func(id string, count *atomic.Int32) *httptest.Server {
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			var req struct {
				ID     int             `json:"id"`
				Method string          `json:"method"`
				Params json.RawMessage `json:"params"`
			}
			if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
				t.Error(err)
				w.WriteHeader(http.StatusBadRequest)
				return
			}
			w.Header().Set("Content-Type", "application/json")
			var result any
			switch req.Method {
			case "initialize":
				result = map[string]any{}
			case "notifications/initialized":
				w.WriteHeader(http.StatusAccepted)
				return
			case "tools/call":
				var call struct {
					Name string `json:"name"`
					Args struct {
						Candidate string `json:"candidate"`
					} `json:"arguments"`
				}
				if err := json.Unmarshal(req.Params, &call); err != nil || call.Name != "inspect_order" || call.Args.Candidate != "C2" {
					t.Errorf("wrong invocation: %s", req.Params)
				}
				count.Add(1)
				result = map[string]any{"content": []map[string]string{{"type": "text", "text": id}}}
			default:
				t.Errorf("unexpected method %q", req.Method)
			}
			if err := json.NewEncoder(w).Encode(map[string]any{"jsonrpc": "2.0", "id": req.ID, "result": result}); err != nil {
				t.Error(err)
			}
		}))
		t.Cleanup(srv.Close)
		return srv
	}
	var teamCalls, memberCalls atomic.Int32
	project := newService("project-receipt", &teamCalls)
	member := newService("member-receipt", &memberCalls)
	targets := []domain.MCPServerDefinition{
		{ID: "project-install", Name: "Orders", URL: project.URL, Transport: "http"},
		{ID: "member-install", Name: "Orders", URL: member.URL, Transport: "http"},
	}
	workspace := t.TempDir()
	env, err := ScriptMCPEnvironment(&localSandbox{workspace: workspace}, workspace, targets)
	if err != nil {
		t.Fatal(err)
	}
	for k, v := range env {
		t.Setenv(k, v)
	}
	call := func(server string) (string, string, int) {
		return captureMCPCall(t, []string{"call", server, "inspect_order", `{"candidate":"C2"}`})
	}
	if _, stderr, code := call("Orders"); code != 1 || !strings.Contains(stderr, "匹配到多个") || teamCalls.Load() != 0 || memberCalls.Load() != 0 {
		t.Fatalf("ambiguous alias: code=%d stderr=%q calls=%d/%d", code, stderr, teamCalls.Load(), memberCalls.Load())
	}
	if stdout, stderr, code := call("project-install"); code != 0 || strings.TrimSpace(stdout) != "project-receipt" || teamCalls.Load() != 1 || memberCalls.Load() != 0 {
		t.Fatalf("explicit project: code=%d stderr=%q stdout=%q calls=%d/%d", code, stderr, stdout, teamCalls.Load(), memberCalls.Load())
	}
	if stdout, stderr, code := call("member-install"); code != 0 || strings.TrimSpace(stdout) != "member-receipt" || teamCalls.Load() != 1 || memberCalls.Load() != 1 {
		t.Fatalf("explicit member: code=%d stderr=%q stdout=%q calls=%d/%d", code, stderr, stdout, teamCalls.Load(), memberCalls.Load())
	}
}
