package ui

import "charm.land/lipgloss/v2"

type StatusIndicator struct {
	State string
}

func (s StatusIndicator) Render() string {
	switch s.State {
	case "connected":
		return lipgloss.NewStyle().Foreground(ColorSuccess).Render("●")
	case "connecting":
		return lipgloss.NewStyle().Foreground(ColorWarning).Render("◐")
	case "reconnecting":
		return lipgloss.NewStyle().Foreground(ColorWarning).Render("↻")
	case "disconnected":
		return lipgloss.NewStyle().Foreground(ColorError).Render("○")
	default:
		return lipgloss.NewStyle().Foreground(ColorTextDim).Render("?")
	}
}

func (s StatusIndicator) Label() string {
	switch s.State {
	case "connected":
		return lipgloss.NewStyle().Foreground(ColorSuccess).Render("connected")
	case "connecting":
		return lipgloss.NewStyle().Foreground(ColorWarning).Render("connecting...")
	case "reconnecting":
		return lipgloss.NewStyle().Foreground(ColorWarning).Render("reconnecting...")
	case "disconnected":
		return lipgloss.NewStyle().Foreground(ColorError).Render("disconnected")
	default:
		return lipgloss.NewStyle().Foreground(ColorTextDim).Render("unknown")
	}
}

func RenderRemoteTab(name string, state string, active bool) string {
	indicator := StatusIndicator{State: state}
	nameStyle := StyleInactiveTab
	if active {
		nameStyle = StyleActiveTab
	}
	return indicator.Render() + " " + nameStyle.Render(name)
}
