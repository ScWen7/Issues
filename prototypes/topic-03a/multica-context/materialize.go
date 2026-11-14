// This probe calls the same public Go entry used by the Multica daemon.
// It writes only into a caller-supplied temporary project.
package main

import (
	"fmt"
	"os"

	"github.com/multica-ai/multica/server/internal/daemon/execenv"
)

func main() {
	if len(os.Args) != 4 {
		panic("expected project directory, provider and fixture marker")
	}
	task := execenv.TaskContextForEnv{
		IssueID:           "order-export-validation",
		AgentName:         "order-check",
		AgentInstructions: "Check the payment-time column for candidate C2. Rule: " + os.Args[3],
	}
	if _, err := execenv.InjectRuntimeConfig(os.Args[1], os.Args[2], task); err != nil {
		panic(err)
	}
	fmt.Println("wrote", execenv.RuntimeConfigRelPath(os.Args[1], os.Args[2]))
}
