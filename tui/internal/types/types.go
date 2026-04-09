package types

// Agent represents an agentic-core agent persona.
type Agent struct {
	Name          string `json:"name"`
	Slug          string `json:"slug"`
	Role          string `json:"role"`
	Description   string `json:"description"`
	GraphTemplate string `json:"graph_template"`
}

// ChatMessage holds a single message in a conversation.
type ChatMessage struct {
	Role    string
	Content string
}

// HealthResponse is the payload returned by the /api/health endpoint.
type HealthResponse struct {
	Status string `json:"status"`
}
