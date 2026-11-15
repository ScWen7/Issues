package handler

import (
	"net/http"
	"slices"
	"testing"

	"github.com/multica-ai/multica/server/internal/testutil"
)

// Test only with Multica's handler tests, via an overlay at the pinned revision.
func TestKnowledgeReaderRevokedAfterSnapshot(t *testing.T) {
	f := newPrivateProjectFixture(t)
	request := func(user, method, url string, body any) *http.Request {
		return asUser(searchIndexRequest(method, url, testWorkspaceID, body), user)
	}
	manifest := testutil.Decode[SearchIndexManifestResponse](t, testHandler.GetSearchIndexManifest,
		request(f.insider, http.MethodGet, "/api/search-index/manifest", nil), http.StatusOK)
	get := func(user string) *testutil.Response {
		return testutil.Call(t, testHandler.GetIssue, testutil.WithURLParams(
			request(user, http.MethodGet, "/api/issues/"+f.secretIssue, nil), "id", f.secretIssue))
	}
	agent := dbfx.Agent(t, f.marker+" knowledge agent", testRuntimeID, testutil.Cols{"owner_id": f.insider})
	task := dbfx.Task(t, agent, testutil.Cols{
		"runtime_id": testRuntimeID, "issue_id": f.secretIssue, "status": "running",
		"originator_user_id": testUserID, "accountable_user_id": testUserID,
	})
	readAsRun := func() *testutil.Response {
		req := testutil.WithURLParams(request(testUserID, http.MethodGet, "/api/issues/"+f.secretIssue, nil), "id", f.secretIssue)
		req.Header.Set("X-Actor-Source", "task_token")
		req.Header.Set("X-Task-ID", task)
		req.Header.Set("X-Agent-ID", agent)
		return testutil.Call(t, testHandler.GetIssue, req)
	}
	get(f.insider).Want(http.StatusOK)
	readAsRun().Want(http.StatusOK)
	removeProjectMemberAsOwner(t, f, f.insider)
	get(f.insider).Want(http.StatusNotFound)
	get(testUserID).Want(http.StatusOK)
	readAsRun().Want(http.StatusNotFound)

	changes := testutil.Decode[SearchIndexChangesResponse](t, testHandler.ListSearchIndexChanges,
		request(f.insider, http.MethodPost, "/api/search-index/changes", map[string]any{"cursor": manifest.Cursor, "limit": 1000}), http.StatusOK)
	for _, item := range []struct {
		label string
		ids   []string
		want  string
	}{
		{"project", changes.Deleted.Projects, f.projectID},
		{"issue", changes.Deleted.Issues, f.secretIssue},
		{"comment", changes.Deleted.Comments, f.secretComment},
	} {
		if !slices.Contains(item.ids, item.want) {
			t.Errorf("%s missing from revoked user's deletions", item.label)
		}
	}
	if slices.Contains(issueIDs(changes.Issues), f.secretIssue) || slices.Contains(commentIDs(changes.Comments), f.secretComment) ||
		slices.Contains(changes.Deleted.Issues, f.publicIssue) {
		t.Fatal("the catch-up included hidden content or removed the public control")
	}
	for _, p := range changes.Projects {
		if p.ID == f.projectID {
			t.Fatal("the revoked project was also returned as readable")
		}
	}
}
