package ui

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"

	"github.com/lapc506/agentic-core/tui/internal/api"
	"github.com/lapc506/agentic-core/tui/internal/types"
)

// agentsLoadedMsg carries the agent list from the API.
type agentsLoadedMsg struct {
	agents []types.Agent
	err    error
}

// AgentsModel is the Bubble Tea model for the agent list view.
type AgentsModel struct {
	client   *api.Client
	agents   []types.Agent
	cursor   int
	loading  bool
	err      error
	width    int
	height   int
}

// NewAgentsModel returns an AgentsModel wired to the given API client.
func NewAgentsModel(client *api.Client) AgentsModel {
	return AgentsModel{
		client:  client,
		loading: true,
	}
}

// Init fetches the agent list from the API.
func (m AgentsModel) Init() tea.Cmd {
	return m.fetchAgents()
}

func (m AgentsModel) fetchAgents() tea.Cmd {
	client := m.client
	return func() tea.Msg {
		agents, err := client.ListAgents()
		return agentsLoadedMsg{agents: agents, err: err}
	}
}

// Update handles messages for the agent list view.
func (m AgentsModel) Update(msg tea.Msg) (AgentsModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case agentsLoadedMsg:
		m.loading = false
		if msg.err != nil {
			m.err = msg.err
		} else {
			m.agents = msg.agents
		}

	case tea.KeyPressMsg:
		switch msg.String() {
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			if m.cursor < len(m.agents)-1 {
				m.cursor++
			}
		case "r":
			m.loading = true
			m.err = nil
			return m, m.fetchAgents()
		}
	}

	return m, nil
}

// View renders the agent list view.
func (m AgentsModel) View() string {
	var sb strings.Builder

	sb.WriteString(StyleTitle.Render("  Agent Personas") + "\n")
	if m.width > 2 {
		sb.WriteString(StyleDim.Render(strings.Repeat("\u2500", m.width-2)) + "\n\n")
	}

	if m.loading {
		sb.WriteString(StyleDim.Render("  Loading agents...") + "\n")
		return sb.String()
	}

	if m.err != nil {
		sb.WriteString(StyleError.Render(fmt.Sprintf("  Error: %v", m.err)) + "\n")
		sb.WriteString(StyleDim.Render("  Press r to retry") + "\n")
		return sb.String()
	}

	if len(m.agents) == 0 {
		sb.WriteString(StyleDim.Render("  No agents registered.") + "\n")
		sb.WriteString(StyleDim.Render("  Press r to refresh") + "\n")
		return sb.String()
	}

	for i, a := range m.agents {
		cursor := "  "
		nameStyle := StyleDim
		if i == m.cursor {
			cursor = "> "
			nameStyle = StyleTitle
		}

		sb.WriteString(fmt.Sprintf(
			"%s%s  %s\n",
			cursor,
			nameStyle.Render(a.Name),
			StyleDim.Render(a.Role),
		))
		if a.Description != "" {
			sb.WriteString(fmt.Sprintf("    %s\n", StyleDim.Render(a.Description)))
		}
		if a.GraphTemplate != "" {
			sb.WriteString(fmt.Sprintf("    %s\n", StyleDim.Render("graph: "+a.GraphTemplate)))
		}
		sb.WriteString("\n")
	}

	sb.WriteString(StyleDim.Render("  j/k: navigate | r: refresh") + "\n")

	return sb.String()
}
