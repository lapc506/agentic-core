package ui

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"

	"github.com/lapc506/agentic-core/tui/internal/api"
)

// Tab identifies the active view.
type Tab int

const (
	TabChat Tab = iota
	TabAgents
	TabSettings
)

// connectedMsg carries the health-check result.
type connectedMsg struct{ status string }

// AppModel is the top-level Bubble Tea model that manages tab switching.
type AppModel struct {
	client   *api.Client
	baseURL  string
	tab      Tab
	chat     ChatModel
	agents   AgentsModel
	settings SettingsModel
	width    int
	height   int
	status   string
}

// NewAppModel returns the root application model.
func NewAppModel(baseURL string) AppModel {
	client := api.NewClient(baseURL)
	return AppModel{
		client:   client,
		baseURL:  baseURL,
		chat:     NewChatModel(client, "asistente-demo"),
		agents:   NewAgentsModel(client),
		settings: NewSettingsModel(baseURL),
		status:   "connecting...",
	}
}

// Init fires the initial commands (textarea blink, health check, agent fetch).
func (m AppModel) Init() tea.Cmd {
	client := m.client
	return tea.Batch(
		m.chat.Init(),
		m.agents.Init(),
		func() tea.Msg {
			health, err := client.Health()
			if err != nil {
				return connectedMsg{status: "offline"}
			}
			return connectedMsg{status: health.Status}
		},
	)
}

// Update routes messages to the active tab's sub-model.
func (m AppModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height

	case tea.KeyPressMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit
		case "tab":
			m.tab = (m.tab + 1) % 3
		case "shift+tab":
			m.tab = (m.tab + 2) % 3
		}

	case connectedMsg:
		m.status = msg.status
	}

	// Delegate to the active tab.
	var cmd tea.Cmd
	switch m.tab {
	case TabChat:
		m.chat, cmd = m.chat.Update(msg)
	case TabAgents:
		m.agents, cmd = m.agents.Update(msg)
	case TabSettings:
		m.settings, cmd = m.settings.Update(msg)
	}
	return m, cmd
}

// View returns the full terminal UI as a tea.View (Bubble Tea v2).
func (m AppModel) View() tea.View {
	tabs := m.renderTabs()
	statusBar := m.renderStatusBar()

	var content string
	switch m.tab {
	case TabChat:
		content = m.chat.View()
	case TabAgents:
		content = m.agents.View()
	case TabSettings:
		content = m.settings.View()
	}

	body := fmt.Sprintf("%s\n%s\n%s", tabs, content, statusBar)

	v := tea.NewView(body)
	v.AltScreen = true
	v.MouseMode = tea.MouseModeCellMotion
	return v
}

// renderTabs draws the tab bar.
func (m AppModel) renderTabs() string {
	labels := []string{"Chat", "Agents", "Settings"}
	var rendered []string
	for i, label := range labels {
		if Tab(i) == m.tab {
			rendered = append(rendered, StyleActiveTab.Render(" "+label+" "))
		} else {
			rendered = append(rendered, StyleInactiveTab.Render(" "+label+" "))
		}
	}
	return lipgloss.NewStyle().
		Padding(0, 1).
		Render(strings.Join(rendered, " \u2502 "))
}

// renderStatusBar draws the bottom status line.
func (m AppModel) renderStatusBar() string {
	statusColor := ColorSuccess
	if m.status != "ok" {
		statusColor = ColorError
	}
	return lipgloss.NewStyle().
		Foreground(ColorTextDim).
		Padding(0, 1).
		Render(fmt.Sprintf(
			"Agent Studio TUI \u2502 %s \u2502 Tab: switch view \u2502 Ctrl+C: quit",
			lipgloss.NewStyle().Foreground(statusColor).Render("\u25cf "+m.status),
		))
}
