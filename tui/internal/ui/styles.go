package ui

import "charm.land/lipgloss/v2"

// Dark theme palette matching the Agent Studio UI.
var (
	ColorRail    = lipgloss.Color("#080810")
	ColorPanel   = lipgloss.Color("#0F0F1E")
	ColorContent = lipgloss.Color("#12121E")
	ColorCard    = lipgloss.Color("#1A1A2E")
	ColorBorder  = lipgloss.Color("#2A2A40")
	ColorPrimary = lipgloss.Color("#3B6FE0")
	ColorText    = lipgloss.Color("#E0E0F0")
	ColorTextDim = lipgloss.Color("#666680")
	ColorSuccess = lipgloss.Color("#4CAF50")
	ColorWarning = lipgloss.Color("#FF9800")
	ColorError   = lipgloss.Color("#EF5350")

	StyleTitle = lipgloss.NewStyle().
			Foreground(ColorPrimary).
			Bold(true)

	StyleDim = lipgloss.NewStyle().
			Foreground(ColorTextDim)

	StyleBorder = lipgloss.NewStyle().
			BorderStyle(lipgloss.RoundedBorder()).
			BorderForeground(ColorBorder)

	StyleActiveTab = lipgloss.NewStyle().
			Foreground(ColorPrimary).
			Bold(true).
			Underline(true)

	StyleInactiveTab = lipgloss.NewStyle().
				Foreground(ColorTextDim)

	StyleUserMsg = lipgloss.NewStyle().
			Foreground(ColorPrimary)

	StyleAssistantMsg = lipgloss.NewStyle().
				Foreground(ColorText)

	StyleStatus = lipgloss.NewStyle().
			Foreground(ColorSuccess)

	StyleError = lipgloss.NewStyle().
			Foreground(ColorError)
)
