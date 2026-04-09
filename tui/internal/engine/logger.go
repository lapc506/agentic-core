package engine

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type IterationLog struct {
	Iteration int                    `json:"iteration"`
	Phase     string                 `json:"phase"`
	Timestamp time.Time              `json:"timestamp"`
	TaskID    string                 `json:"task_id,omitempty"`
	Output    string                 `json:"output,omitempty"`
	Error     string                 `json:"error,omitempty"`
	Tokens    int                    `json:"tokens,omitempty"`
	Duration  time.Duration          `json:"duration_ms,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

type IterationLogger struct {
	dir     string
	file    *os.File
	encoder *json.Encoder
	runID   string
}

func NewIterationLogger(dir string) (*IterationLogger, error) {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, err
	}

	runID := time.Now().Format("20060102-150405")
	path := filepath.Join(dir, fmt.Sprintf("%s.jsonl", runID))
	file, err := os.Create(path)
	if err != nil {
		return nil, err
	}

	return &IterationLogger{
		dir:     dir,
		file:    file,
		encoder: json.NewEncoder(file),
		runID:   runID,
	}, nil
}

func (il *IterationLogger) Log(entry IterationLog) error {
	entry.Timestamp = time.Now()
	return il.encoder.Encode(entry)
}

func (il *IterationLogger) LogEvent(event Event) error {
	entry := IterationLog{
		Phase:    string(event.Type),
		Metadata: event.Data,
	}
	if taskID, ok := event.Data["task_id"].(string); ok {
		entry.TaskID = taskID
	}
	if output, ok := event.Data["output"].(string); ok {
		entry.Output = output
	}
	return il.Log(entry)
}

func (il *IterationLogger) Close() error {
	if il.file != nil {
		return il.file.Close()
	}
	return nil
}

func (il *IterationLogger) RunID() string { return il.runID }
func (il *IterationLogger) Path() string {
	return filepath.Join(il.dir, fmt.Sprintf("%s.jsonl", il.runID))
}
