package ui

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

// DashboardData holds all the data rendered by DashboardModel.
type DashboardData struct {
	Status      string
	Agent       string
	Model       string
	Branch      string
	BranchDirty bool
	Iteration   int
	TotalTasks  int
	DoneTasks   int
	Tokens      int
	Cost        float64
	Phase       string
}

// DashboardModel is the Bubble Tea model for the dashboard view.
type DashboardModel struct {
	data   DashboardData
	width  int
	height int
}

// NewDashboardModel returns a DashboardModel with sensible defaults.
func NewDashboardModel() DashboardModel {
	return DashboardModel{
		data: DashboardData{
			Status: "idle",
			Agent:  "none",
			Model:  "none",
			Branch: "main",
		},
	}
}

// Init is a no-op for the dashboard (data arrives via DashboardData messages).
func (m DashboardModel) Init() tea.Cmd { return nil }

// Update handles window resize and DashboardData update messages.
func (m DashboardModel) Update(msg tea.Msg) (DashboardModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	case DashboardData:
		m.data = msg
	}
	return m, nil
}

// View renders the dashboard panel.
func (m DashboardModel) View() string {
	d := m.data

	statusColor := ColorSuccess
	statusIcon := "●"
	switch d.Status {
	case "running":
		statusColor = ColorPrimary
		statusIcon = "●"
	case "paused":
		statusColor = ColorWarning
		statusIcon = "◐"
	case "failed":
		statusColor = ColorError
		statusIcon = "✕"
	case "idle":
		statusColor = ColorTextDim
		statusIcon = "○"
	}

	header := StyleTitle.Render("  Dashboard")

	// Status row
	branchDirtyMarker := ""
	if d.BranchDirty {
		branchDirtyMarker = StyleError.Render(" *")
	}
	statusLine := fmt.Sprintf("  %s %s  │  Agent: %s  │  Model: %s  │  Branch: %s%s",
		lipgloss.NewStyle().Foreground(statusColor).Render(statusIcon),
		lipgloss.NewStyle().Foreground(statusColor).Render(d.Status),
		StyleAssistantMsg.Render(d.Agent),
		StyleDim.Render(d.Model),
		d.Branch,
		branchDirtyMarker,
	)

	// Progress bar
	progress := 0.0
	if d.TotalTasks > 0 {
		progress = float64(d.DoneTasks) / float64(d.TotalTasks)
	}
	barWidth := 40
	filled := int(progress * float64(barWidth))
	if filled > barWidth {
		filled = barWidth
	}
	bar := fmt.Sprintf("  [%s%s] %d/%d tasks  │  Iteration: %d  │  Phase: %s",
		lipgloss.NewStyle().Foreground(ColorPrimary).Render(strings.Repeat("█", filled)),
		lipgloss.NewStyle().Foreground(ColorBorder).Render(strings.Repeat("░", barWidth-filled)),
		d.DoneTasks, d.TotalTasks,
		d.Iteration,
		StyleDim.Render(d.Phase),
	)

	// Cost line
	costLine := fmt.Sprintf("  Tokens: %s  │  Est. cost: %s",
		StyleAssistantMsg.Render(fmt.Sprintf("%d", d.Tokens)),
		lipgloss.NewStyle().Foreground(ColorWarning).Render(fmt.Sprintf("$%.4f", d.Cost)),
	)

	dividerWidth := m.width - 2
	if dividerWidth < 1 {
		dividerWidth = 1
	}
	divider := lipgloss.NewStyle().Foreground(ColorBorder).Render(strings.Repeat("─", dividerWidth))

	return fmt.Sprintf("%s\n%s\n\n%s\n\n%s\n\n%s", header, divider, statusLine, bar, costLine)
}
