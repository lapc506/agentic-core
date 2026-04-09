package main

import (
	"flag"
	"fmt"
	"os"

	tea "charm.land/bubbletea/v2"

	"github.com/lapc506/agentic-core/tui/internal/ui"
)

func main() {
	baseURL := flag.String("url", "http://localhost:8080", "agentic-core API URL")
	flag.Parse()

	p := tea.NewProgram(ui.NewAppModel(*baseURL))

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
