// Run as an overlay in the pinned LoopForge internal/runtime package.
package runtime

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agentflow/internal/domain"
)

func TestOrderRulesAndSkillAtMaterialization(t *testing.T) {
	workspace := t.TempDir()
	const (
		current = "导出五列，第五列为付款时间。"
		old     = "导出四列，省略付款时间。"
		method  = "分别核对东区与西区账号的订单集合。"
	)
	assets := domain.AgentAssetBundle{
		Rules: []domain.RuleDefinition{
			{ID: "legacy", Name: "历史标准", Content: old, Priority: 1},
			{ID: "d2", Name: "订单 D2", Content: current, Priority: 9},
		},
		Skills: []domain.SkillDefinition{
			{ID: "order-check", Name: "订单核验", Description: "检查导出文件", Content: method},
		},
	}
	role := domain.AgentDefinition{ID: "verifier", Name: "核验者"}
	_, err := materialize(workspace, "order-control", domain.ExecutorDefinition{Kind: "codex"}, role, assets)
	if err != nil {
		t.Fatal(err)
	}
	read := func(rel string) string {
		t.Helper()
		b, err := os.ReadFile(filepath.Join(workspace, ".agentflow", rel))
		if err != nil {
			t.Fatal(err)
		}
		return string(b)
	}
	brief := read("config/verifier/agent-system.md")
	if strings.Count(brief, current) != 1 || strings.Count(brief, old) != 1 || strings.Index(brief, current) >= strings.Index(brief, old) {
		t.Fatalf("expected both conflicting rule bodies in priority order, got %q", brief)
	}
	if !strings.Contains(brief, "name: `order-check`") || strings.Contains(brief, method) {
		t.Fatalf("expected the skill reference and no body in the system file, got %q", brief)
	}
	if !strings.Contains(read("bindings/verifier/skills/order-check/SKILL.md"), method) {
		t.Fatal("skill body missing from its separate bound entry")
	}
	t.Log("materialization succeeded: D2 and the contradicting legacy rule both present; skill listed, body separate")
}
