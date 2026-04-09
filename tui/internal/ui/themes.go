package ui

import (
	"image/color"

	"charm.land/lipgloss/v2"
)

// Theme holds all the colour tokens for a named theme.
type Theme struct {
	Name    string
	Rail    color.Color
	Panel   color.Color
	Content color.Color
	Card    color.Color
	Border  color.Color
	Primary color.Color
	Text    color.Color
	TextDim color.Color
	Success color.Color
	Warning color.Color
	Error   color.Color
}

// Themes is the built-in set of named colour themes.
var Themes = map[string]Theme{
	"dark": {
		Name: "dark", Rail: lipgloss.Color("#080810"), Panel: lipgloss.Color("#0F0F1E"), Content: lipgloss.Color("#12121E"),
		Card: lipgloss.Color("#1A1A2E"), Border: lipgloss.Color("#2A2A40"), Primary: lipgloss.Color("#3B6FE0"), Text: lipgloss.Color("#E0E0F0"),
		TextDim: lipgloss.Color("#666680"), Success: lipgloss.Color("#4CAF50"), Warning: lipgloss.Color("#FF9800"), Error: lipgloss.Color("#EF5350"),
	},
	"catppuccin": {
		Name: "catppuccin", Rail: lipgloss.Color("#1E1E2E"), Panel: lipgloss.Color("#181825"), Content: lipgloss.Color("#1E1E2E"),
		Card: lipgloss.Color("#313244"), Border: lipgloss.Color("#45475A"), Primary: lipgloss.Color("#89B4FA"), Text: lipgloss.Color("#CDD6F4"),
		TextDim: lipgloss.Color("#6C7086"), Success: lipgloss.Color("#A6E3A1"), Warning: lipgloss.Color("#F9E2AF"), Error: lipgloss.Color("#F38BA8"),
	},
	"dracula": {
		Name: "dracula", Rail: lipgloss.Color("#21222C"), Panel: lipgloss.Color("#282A36"), Content: lipgloss.Color("#282A36"),
		Card: lipgloss.Color("#44475A"), Border: lipgloss.Color("#6272A4"), Primary: lipgloss.Color("#BD93F9"), Text: lipgloss.Color("#F8F8F2"),
		TextDim: lipgloss.Color("#6272A4"), Success: lipgloss.Color("#50FA7B"), Warning: lipgloss.Color("#F1FA8C"), Error: lipgloss.Color("#FF5555"),
	},
	"solarized": {
		Name: "solarized", Rail: lipgloss.Color("#002B36"), Panel: lipgloss.Color("#073642"), Content: lipgloss.Color("#002B36"),
		Card: lipgloss.Color("#073642"), Border: lipgloss.Color("#586E75"), Primary: lipgloss.Color("#268BD2"), Text: lipgloss.Color("#839496"),
		TextDim: lipgloss.Color("#586E75"), Success: lipgloss.Color("#859900"), Warning: lipgloss.Color("#B58900"), Error: lipgloss.Color("#DC322F"),
	},
	"high-contrast": {
		Name: "high-contrast", Rail: lipgloss.Color("#000000"), Panel: lipgloss.Color("#0A0A0A"), Content: lipgloss.Color("#000000"),
		Card: lipgloss.Color("#1A1A1A"), Border: lipgloss.Color("#FFFFFF"), Primary: lipgloss.Color("#00BFFF"), Text: lipgloss.Color("#FFFFFF"),
		TextDim: lipgloss.Color("#AAAAAA"), Success: lipgloss.Color("#00FF00"), Warning: lipgloss.Color("#FFFF00"), Error: lipgloss.Color("#FF0000"),
	},
}

// ApplyTheme updates the global colour variables and rebuilds style objects.
func ApplyTheme(name string) {
	theme, ok := Themes[name]
	if !ok {
		theme = Themes["dark"]
	}
	ColorRail = theme.Rail
	ColorPanel = theme.Panel
	ColorContent = theme.Content
	ColorCard = theme.Card
	ColorBorder = theme.Border
	ColorPrimary = theme.Primary
	ColorText = theme.Text
	ColorTextDim = theme.TextDim
	ColorSuccess = theme.Success
	ColorWarning = theme.Warning
	ColorError = theme.Error
	// Rebuild styles with the new colours.
	StyleTitle = lipgloss.NewStyle().Foreground(ColorPrimary).Bold(true)
	StyleDim = lipgloss.NewStyle().Foreground(ColorTextDim)
	StyleActiveTab = lipgloss.NewStyle().Foreground(ColorPrimary).Bold(true).Underline(true)
	StyleInactiveTab = lipgloss.NewStyle().Foreground(ColorTextDim)
	StyleUserMsg = lipgloss.NewStyle().Foreground(ColorPrimary)
	StyleAssistantMsg = lipgloss.NewStyle().Foreground(ColorText)
	StyleStatus = lipgloss.NewStyle().Foreground(ColorSuccess)
	StyleError = lipgloss.NewStyle().Foreground(ColorError)
}
