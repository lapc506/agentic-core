package engine

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type PRDTask struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Description  string   `json:"description"`
	Priority     string   `json:"priority"` // high, medium, low
	Status       string   `json:"status"`   // pending, running, completed, failed, skipped
	Dependencies []string `json:"dependencies,omitempty"`
	Tier         string   `json:"tier,omitempty"` // low, medium, high (for model selection)
	Tags         []string `json:"tags,omitempty"`
}

type PRD struct {
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Tasks       []PRDTask `json:"tasks"`
	Version     string    `json:"version"`
}

func LoadPRD(path string) (*PRD, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var prd PRD
	if err := json.Unmarshal(data, &prd); err != nil {
		return nil, err
	}
	return &prd, nil
}

func (p *PRD) Save(path string) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func (p *PRD) NextPending() *PRDTask {
	completed := make(map[string]bool)
	for _, t := range p.Tasks {
		if t.Status == "completed" {
			completed[t.ID] = true
		}
	}
	for i := range p.Tasks {
		t := &p.Tasks[i]
		if t.Status != "pending" {
			continue
		}
		// Check dependencies
		ready := true
		for _, dep := range t.Dependencies {
			if !completed[dep] {
				ready = false
				break
			}
		}
		if ready {
			return t
		}
	}
	return nil
}

func (p *PRD) UpdateStatus(taskID string, status string) {
	for i := range p.Tasks {
		if p.Tasks[i].ID == taskID {
			p.Tasks[i].Status = status
			return
		}
	}
}

func (p *PRD) Progress() (done int, total int) {
	total = len(p.Tasks)
	for _, t := range p.Tasks {
		if t.Status == "completed" || t.Status == "skipped" {
			done++
		}
	}
	return
}

func (p *PRD) ToSessionTasks() []TaskState {
	tasks := make([]TaskState, len(p.Tasks))
	for i, t := range p.Tasks {
		tasks[i] = TaskState{
			ID:          t.ID,
			Title:       t.Title,
			Description: t.Description,
			Status:      t.Status,
		}
	}
	return tasks
}

func DefaultPRD() *PRD {
	return &PRD{
		Name:        "Agent Studio Tasks",
		Description: "Default task list",
		Version:     "1.0",
		Tasks:       []PRDTask{},
	}
}
