package engine

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type SessionState string

const (
	StateIdle      SessionState = "idle"
	StateRunning   SessionState = "running"
	StatePaused    SessionState = "paused"
	StateCompleted SessionState = "completed"
	StateFailed    SessionState = "failed"
)

type TaskState struct {
	ID          string `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	Status      string `json:"status"` // pending, running, completed, failed, skipped
	Result      string `json:"result,omitempty"`
	Iteration   int    `json:"iteration"`
}

type Session struct {
	ID            string       `json:"id"`
	State         SessionState `json:"state"`
	Agent         string       `json:"agent"`
	Model         string       `json:"model"`
	Tasks         []TaskState  `json:"tasks"`
	CurrentTask   int          `json:"current_task"`
	TotalTokens   int          `json:"total_tokens"`
	EstimatedCost float64      `json:"estimated_cost"`
	StartedAt     time.Time    `json:"started_at"`
	UpdatedAt     time.Time    `json:"updated_at"`
	Iterations    int          `json:"iterations"`
}

type SessionManager struct {
	dir     string
	session *Session
}

func NewSessionManager(dir string) *SessionManager {
	return &SessionManager{dir: dir}
}

func (sm *SessionManager) Dir() string { return sm.dir }

func (sm *SessionManager) Load() (*Session, error) {
	path := filepath.Join(sm.dir, "session.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var s Session
	if err := json.Unmarshal(data, &s); err != nil {
		return nil, err
	}
	sm.session = &s
	return &s, nil
}

func (sm *SessionManager) Save(s *Session) error {
	if err := os.MkdirAll(sm.dir, 0755); err != nil {
		return err
	}
	s.UpdatedAt = time.Now()
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	tmp := filepath.Join(sm.dir, "session.json.tmp")
	if err := os.WriteFile(tmp, data, 0644); err != nil {
		return err
	}
	return os.Rename(tmp, filepath.Join(sm.dir, "session.json"))
}

func (sm *SessionManager) AcquireLock() error {
	lockPath := filepath.Join(sm.dir, ".lock")
	if err := os.MkdirAll(sm.dir, 0755); err != nil {
		return err
	}
	// Check stale lock (>30s)
	if info, err := os.Stat(lockPath); err == nil {
		if time.Since(info.ModTime()) > 30*time.Second {
			os.Remove(lockPath)
		} else {
			data, _ := os.ReadFile(lockPath)
			return fmt.Errorf("session locked by PID %s", strings.TrimSpace(string(data)))
		}
	}
	return os.WriteFile(lockPath, []byte(strconv.Itoa(os.Getpid())), 0644)
}

func (sm *SessionManager) ReleaseLock() {
	os.Remove(filepath.Join(sm.dir, ".lock"))
}

func (sm *SessionManager) Current() *Session { return sm.session }
