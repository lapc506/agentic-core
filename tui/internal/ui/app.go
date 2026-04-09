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
	TabDashboard
	TabAgents
	TabSettings

	tabCount = 4
)

// connectedMsg carries the health-check result.
type connectedMsg struct{ status string }

// AppModel is the top-level Bubble Tea model that manages tab switching.
type AppModel struct {
	client    *api.Client
	baseURL   string
	tab       Tab
	chat      ChatModel
	dashboard DashboardModel
	agents    AgentsModel
	settings  SettingsModel
	width     int
	height    int
	status    string
	showTree  bool
	treeRoot  *TreeNode
}

// NewAppModel returns the root application model.
func NewAppModel(baseURL string) AppModel {
	client := api.NewClient(baseURL)

	// Sample tree for demonstration; replaced by real data via messages.
	sampleTree := &TreeNode{
		ID:       "root",
		Label:    "Session",
		Status:   "running",
		Expanded: true,
		Children: []*TreeNode{
			{ID: "p1", Label: "Planner", Status: "completed", Expanded: false},
			{
				ID:       "e1",
				Label:    "Executor",
				Status:   "running",
				Expanded: true,
				Children: []*TreeNode{
					{ID: "t1", Label: "Tool: read_file", Status: "completed"},
					{ID: "t2", Label: "Tool: write_file", Status: "running"},
				},
			},
		},
	}

	return AppModel{
		client:    client,
		baseURL:   baseURL,
		chat:      NewChatModel(client, "asistente-demo"),
		dashboard: NewDashboardModel(),
		agents:    NewAgentsModel(client),
		settings:  NewSettingsModel(baseURL),
		status:    "connecting...",
		treeRoot:  sampleTree,
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

// inputFocused returns true when the chat textarea has focus (text input mode).
// In that state single-key navigation shortcuts are suppressed so characters
// are delivered to the textarea instead.
func (m AppModel) inputFocused() bool {
	return m.tab == TabChat && m.chat.input.Focused()
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

		// Tab / shift+tab always cycle through tabs.
		case "tab":
			m.tab = (m.tab + 1) % tabCount
		case "shift+tab":
			m.tab = (m.tab + tabCount - 1) % tabCount

		default:
			// Single-key shortcuts are only active when the text input is NOT focused.
			if !m.inputFocused() {
				switch msg.String() {
				case "q":
					return m, tea.Quit
				case "d":
					m.tab = TabDashboard
				case "T":
					m.showTree = !m.showTree
				case "s":
					// "start": update dashboard data to running state as a demo action.
					m.dashboard, _ = m.dashboard.Update(DashboardData{
						Status:     "running",
						Agent:      m.dashboard.data.Agent,
						Model:      m.dashboard.data.Model,
						Branch:     m.dashboard.data.Branch,
						Iteration:  m.dashboard.data.Iteration + 1,
						TotalTasks: m.dashboard.data.TotalTasks,
						DoneTasks:  m.dashboard.data.DoneTasks,
						Tokens:     m.dashboard.data.Tokens,
						Cost:       m.dashboard.data.Cost,
						Phase:      "executing",
					})
				case "p":
					// "pause": flip running → paused.
					current := m.dashboard.data
					if current.Status == "running" {
						current.Status = "paused"
					} else {
						current.Status = "running"
					}
					m.dashboard, _ = m.dashboard.Update(current)
				}
			}
		}

	case connectedMsg:
		m.status = msg.status

	// Allow external code to push DashboardData directly to the app.
	case DashboardData:
		var cmd tea.Cmd
		m.dashboard, cmd = m.dashboard.Update(msg)
		return m, cmd
	}

	// Delegate to the active tab.
	var cmd tea.Cmd
	switch m.tab {
	case TabChat:
		m.chat, cmd = m.chat.Update(msg)
	case TabDashboard:
		m.dashboard, cmd = m.dashboard.Update(msg)
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
	case TabDashboard:
		content = m.dashboard.View()
	case TabAgents:
		content = m.agents.View()
	case TabSettings:
		content = m.settings.View()
	}

	// Optionally overlay the agent tree panel on the right.
	if m.showTree && m.treeRoot != nil {
		content = m.renderWithTree(content)
	}

	body := fmt.Sprintf("%s\n%s\n%s", tabs, content, statusBar)

	v := tea.NewView(body)
	v.AltScreen = true
	v.MouseMode = tea.MouseModeCellMotion
	return v
}

// renderWithTree splits the screen: main content on the left, tree on the right.
func (m AppModel) renderWithTree(content string) string {
	treeWidth := 36
	if m.width < treeWidth+20 {
		// Terminal too narrow — render tree below content instead.
		var sb strings.Builder
		sb.WriteString(content)
		sb.WriteString("\n")
		sb.WriteString(StyleTitle.Render("  Agent Tree") + "\n")
		sb.WriteString(StyleDim.Render(strings.Repeat("─", m.width-2)) + "\n")
		sb.WriteString(RenderTree(m.treeRoot, "", true))
		return sb.String()
	}

	treePanel := StyleTitle.Render("Agent Tree") + "\n" +
		StyleDim.Render(strings.Repeat("─", treeWidth-2)) + "\n" +
		RenderTree(m.treeRoot, "", true)

	// Join side-by-side using lipgloss.
	mainStyle := lipgloss.NewStyle().Width(m.width - treeWidth - 1)
	treeStyle := lipgloss.NewStyle().
		Width(treeWidth).
		BorderStyle(lipgloss.NormalBorder()).
		BorderLeft(true).
		BorderForeground(ColorBorder).
		Padding(0, 1)

	return lipgloss.JoinHorizontal(lipgloss.Top, mainStyle.Render(content), treeStyle.Render(treePanel))
}

// renderTabs draws the tab bar.
func (m AppModel) renderTabs() string {
	labels := []string{"Chat", "Dashboard", "Agents", "Settings"}
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

	hints := "Tab: switch  s: start  p: pause  d: dashboard  T: tree  q: quit  Ctrl+C: quit"
	if m.inputFocused() {
		hints = "Tab: switch view  Ctrl+C: quit"
	}

	return lipgloss.NewStyle().
		Foreground(ColorTextDim).
		Padding(0, 1).
		Render(fmt.Sprintf(
			"Agent Studio TUI \u2502 %s \u2502 %s",
			lipgloss.NewStyle().Foreground(statusColor).Render("\u25cf "+m.status),
			hints,
		))
}
