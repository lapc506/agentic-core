package ui

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
)

// SettingsModel is the Bubble Tea model for the settings view.
type SettingsModel struct {
	baseURL string
	width   int
	height  int
}

// NewSettingsModel returns a SettingsModel showing the current configuration.
func NewSettingsModel(baseURL string) SettingsModel {
	return SettingsModel{baseURL: baseURL}
}

// Init returns nil (nothing to initialize).
func (m SettingsModel) Init() tea.Cmd {
	return nil
}

// Update handles messages for the settings view.
func (m SettingsModel) Update(msg tea.Msg) (SettingsModel, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	}
	return m, nil
}

// View renders the settings view.
func (m SettingsModel) View() string {
	var sb strings.Builder

	sb.WriteString(StyleTitle.Render("  Settings") + "\n")
	if m.width > 2 {
		sb.WriteString(StyleDim.Render(strings.Repeat("\u2500", m.width-2)) + "\n\n")
	}

	sb.WriteString(fmt.Sprintf("  API URL:  %s\n\n", StyleAssistantMsg.Render(m.baseURL)))

	sb.WriteString(StyleDim.Render("  Configuration is read-only for now.") + "\n")
	sb.WriteString(StyleDim.Render("  Pass --url <address> at startup to change the API endpoint.") + "\n")

	return sb.String()
}
