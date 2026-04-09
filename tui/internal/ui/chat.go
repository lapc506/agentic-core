package ui

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
	"charm.land/bubbles/v2/textarea"
	"charm.land/bubbles/v2/viewport"

	"github.com/lapc506/agentic-core/tui/internal/api"
	"github.com/lapc506/agentic-core/tui/internal/types"
)

// streamChunkMsg carries a single chunk of streamed assistant text.
type streamChunkMsg string

// streamDoneMsg signals that the stream has finished.
type streamDoneMsg struct{}

// streamErrMsg signals a streaming error.
type streamErrMsg struct{ err error }

// ChatModel is the Bubble Tea model for the chat view.
type ChatModel struct {
	client    *api.Client
	input     textarea.Model
	viewport  viewport.Model
	messages  []types.ChatMessage
	agent     string
	streaming bool
	width     int
	height    int
	ready     bool
}

// NewChatModel returns a ChatModel wired to the given API client and agent slug.
func NewChatModel(client *api.Client, agent string) ChatModel {
	ta := textarea.New()
	ta.Placeholder = "Send a message..."
	ta.SetHeight(3)

	return ChatModel{
		client: client,
		input:  ta,
		agent:  agent,
	}
}

// Init returns the initial command (textarea focus/cursor blink).
func (m ChatModel) Init() tea.Cmd {
	return m.input.Focus()
}

// Update handles messages for the chat view.
func (m ChatModel) Update(msg tea.Msg) (ChatModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		if !m.ready {
			m.viewport = viewport.New(
				viewport.WithWidth(msg.Width-4),
				viewport.WithHeight(msg.Height-10),
			)
			m.ready = true
		} else {
			m.viewport.SetWidth(msg.Width - 4)
			m.viewport.SetHeight(msg.Height - 10)
		}
		m.input.SetWidth(msg.Width - 4)

	case tea.KeyPressMsg:
		if msg.String() == "enter" && !m.streaming {
			content := strings.TrimSpace(m.input.Value())
			if content != "" {
				m.messages = append(m.messages, types.ChatMessage{Role: "user", Content: content})
				m.input.Reset()
				m.streaming = true
				m.messages = append(m.messages, types.ChatMessage{Role: "assistant", Content: ""})
				m.updateViewport()
				return m, m.sendMessage()
			}
		}

	case streamChunkMsg:
		if len(m.messages) > 0 {
			m.messages[len(m.messages)-1].Content += string(msg)
			m.updateViewport()
		}

	case streamDoneMsg:
		m.streaming = false

	case streamErrMsg:
		m.streaming = false
		m.messages = append(m.messages, types.ChatMessage{
			Role:    "system",
			Content: fmt.Sprintf("Error: %v", msg.err),
		})
		m.updateViewport()
	}

	// Forward to textarea when not streaming.
	if !m.streaming {
		var cmd tea.Cmd
		m.input, cmd = m.input.Update(msg)
		cmds = append(cmds, cmd)
	}

	// Forward to viewport for scrolling.
	var vpCmd tea.Cmd
	m.viewport, vpCmd = m.viewport.Update(msg)
	cmds = append(cmds, vpCmd)

	return m, tea.Batch(cmds...)
}

// updateViewport rebuilds the viewport content from the message history.
func (m *ChatModel) updateViewport() {
	var sb strings.Builder
	for i, msg := range m.messages {
		switch msg.Role {
		case "user":
			sb.WriteString(StyleUserMsg.Render("You: ") + msg.Content + "\n\n")
		case "assistant":
			sb.WriteString(StyleAssistantMsg.Render("Agent: ") + msg.Content)
			if m.streaming && i == len(m.messages)-1 {
				sb.WriteString("\u258c") // blinking cursor block
			}
			sb.WriteString("\n\n")
		case "system":
			sb.WriteString(StyleError.Render("System: ") + msg.Content + "\n\n")
		}
	}
	m.viewport.SetContent(sb.String())
	m.viewport.GotoBottom()
}

// sendMessage returns a tea.Cmd that streams the assistant response.
func (m ChatModel) sendMessage() tea.Cmd {
	// Capture values needed by the goroutine.
	client := m.client
	agent := m.agent
	// Copy messages minus the trailing empty assistant placeholder.
	msgs := make([]types.ChatMessage, len(m.messages)-1)
	copy(msgs, m.messages[:len(m.messages)-1])

	return func() tea.Msg {
		var collected strings.Builder
		err := client.ChatStream(agent, msgs, func(chunk string) {
			collected.WriteString(chunk)
		})
		if err != nil {
			return streamErrMsg{err: err}
		}
		// Return the full collected response as a single chunk
		// (real streaming would use tea.Program.Send from a goroutine).
		if collected.Len() > 0 {
			return streamChunkMsg(collected.String())
		}
		return streamDoneMsg{}
	}
}

// View renders the chat view.
func (m ChatModel) View() string {
	if !m.ready {
		return "Loading..."
	}

	header := StyleTitle.Render(fmt.Sprintf("  Chat - %s", m.agent))
	status := ""
	if m.streaming {
		status = StyleDim.Render(" (streaming...)")
	}

	separator := ""
	if m.width > 2 {
		separator = StyleDim.Render(strings.Repeat("\u2500", m.width-2))
	}

	return fmt.Sprintf(
		"%s%s\n%s\n%s\n%s",
		header, status,
		separator,
		m.viewport.View(),
		m.input.View(),
	)
}
