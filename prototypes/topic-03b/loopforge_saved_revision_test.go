// Overlay in LoopForge internal/engine at the commit listed in native-assets.md.
package engine

import (
	"testing"

	"agentflow/internal/domain"
)

func TestAgentPlatformSavedRevisionAndRunningEvidence(t *testing.T) {
	e, catalog := newRecoveryEngine(t)
	e.executeRuns = false // exercise native start/refresh, without starting a worker.
	const first = "printf 'check-v1'"
	const edited = "printf 'check-v2'"
	wf := domain.WorkflowDefinition{
		ID: "fixture-order-verify", Name: "Verify an order export", Status: "draft",
		Nodes: []domain.WorkflowNode{{ID: "check", Type: "script", Name: "Verify", Script: first}},
	}
	if err := catalog.PutWorkflow(wf); err != nil {
		t.Fatal(err)
	}
	released, err := catalog.PublishWorkflow(wf.ID)
	if err != nil {
		t.Fatal(err)
	}
	old, err := e.Start(wf.ID, "original run")
	if err != nil {
		t.Fatal(err)
	}
	if old.WorkflowSnapshot.Nodes[0].Script != first {
		t.Fatalf("original Run did not get the published script")
	}
	released.Nodes[0].Script = edited
	if err := catalog.PutWorkflow(released); err != nil { // Save only.
		t.Fatal(err)
	}
	saved, _ := catalog.Workflow(wf.ID)
	if saved.Revision == saved.PublishedRevision || saved.Version != released.Version {
		t.Fatalf("expected an unpublished edit to the same publication")
	}
	stillOld, _ := catalog.RunState(old.ID)
	if stillOld.WorkflowSnapshot.Nodes[0].Script != first {
		t.Fatal("an existing run changed before refresh")
	}
	current, err := e.Start(wf.ID, "new run")
	if err != nil || current.WorkflowSnapshot.Nodes[0].Script != edited ||
		current.WorkflowSnapshot.Revision != saved.Revision {
		t.Fatalf("new Run did not observe the saved edit: %v", err)
	}
	if err := e.RefreshRunSOP(old.ID); err == nil {
		t.Fatal("refresh on a running Run unexpectedly succeeded")
	}
	stillOld.Status = "waiting"
	stillOld.Nodes["check"].Status = "succeeded"
	stillOld.Nodes["check"].Output = "original result under check-v1"
	if err := catalog.PutRun(stillOld); err != nil {
		t.Fatal(err)
	}
	if err := e.RefreshRunSOP(old.ID); err != nil {
		t.Fatal(err)
	}
	refreshed, _ := catalog.RunState(old.ID)
	if refreshed.WorkflowSnapshot.Nodes[0].Script != edited ||
		refreshed.Nodes["check"].Status != "succeeded" ||
		refreshed.Nodes["check"].Output != "original result under check-v1" {
		t.Fatal("same-ID old result was not retained across the script revision")
	}
	t.Logf("published v%d revision %d; saved revision %d, publishedRevision %d; existing Run kept check-v1, new Run picked check-v2; explicit stopped refresh kept prior success with old output",
		released.Version, released.Revision, saved.Revision, saved.PublishedRevision)
}
