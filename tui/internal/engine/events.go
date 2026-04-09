package engine

import "time"

type EventType string

const (
	EngineStarted      EventType = "engine:started"
	EngineStopped      EventType = "engine:stopped"
	EnginePaused       EventType = "engine:paused"
	EngineResumed      EventType = "engine:resumed"
	IterationStarted   EventType = "iteration:started"
	IterationCompleted EventType = "iteration:completed"
	IterationFailed    EventType = "iteration:failed"
	TaskSelected       EventType = "task:selected"
	TaskCompleted      EventType = "task:completed"
	TaskFailed         EventType = "task:failed"
	TaskSkipped        EventType = "task:skipped"
	AgentStarted       EventType = "agent:started"
	AgentOutput        EventType = "agent:output"
	AgentCompleted     EventType = "agent:completed"
	AgentError         EventType = "agent:error"
	WorkerStarted      EventType = "worker:started"
	WorkerCompleted    EventType = "worker:completed"
	MergeCompleted     EventType = "merge:completed"
	ConflictDetected   EventType = "conflict:detected"
	SessionSaved       EventType = "session:saved"
	SessionRestored    EventType = "session:restored"
	CostUpdated        EventType = "cost:updated"
)

type Event struct {
	Type      EventType              `json:"type"`
	Timestamp time.Time              `json:"timestamp"`
	Data      map[string]interface{} `json:"data,omitempty"`
}

func NewEvent(t EventType, data map[string]interface{}) Event {
	return Event{Type: t, Timestamp: time.Now(), Data: data}
}
