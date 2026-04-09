package api

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"

	"github.com/lapc506/agentic-core/tui/internal/types"
)

// Client talks to the agentic-core REST API.
type Client struct {
	BaseURL string
}

// NewClient returns a Client pointing at baseURL (e.g. "http://localhost:8080").
func NewClient(baseURL string) *Client {
	return &Client{BaseURL: baseURL}
}

// Health calls GET /api/health and returns the server status.
func (c *Client) Health() (*types.HealthResponse, error) {
	resp, err := http.Get(c.BaseURL + "/api/health")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result types.HealthResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result, nil
}

// ListAgents calls GET /api/agents and returns the registered agents.
func (c *Client) ListAgents() ([]types.Agent, error) {
	resp, err := http.Get(c.BaseURL + "/api/agents")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var agents []types.Agent
	if err := json.NewDecoder(resp.Body).Decode(&agents); err != nil {
		return nil, err
	}
	return agents, nil
}

// ChatStream sends a message via the Ollama-compatible /api/chat endpoint
// and calls callback with each streamed content chunk.
func (c *Client) ChatStream(model string, messages []types.ChatMessage, callback func(string)) error {
	type ollamaMsg struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	}
	type ollamaReq struct {
		Model    string      `json:"model"`
		Messages []ollamaMsg `json:"messages"`
		Stream   bool        `json:"stream"`
	}

	var msgs []ollamaMsg
	for _, m := range messages {
		msgs = append(msgs, ollamaMsg{Role: m.Role, Content: m.Content})
	}

	body, err := json.Marshal(ollamaReq{Model: model, Messages: msgs, Stream: true})
	if err != nil {
		return err
	}

	resp, err := http.Post(c.BaseURL+"/api/chat", "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	decoder := json.NewDecoder(resp.Body)
	for {
		var chunk map[string]interface{}
		if err := decoder.Decode(&chunk); err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
		if msg, ok := chunk["message"].(map[string]interface{}); ok {
			if content, ok := msg["content"].(string); ok && content != "" {
				callback(content)
			}
		}
		if done, ok := chunk["done"].(bool); ok && done {
			break
		}
	}
	return nil
}
