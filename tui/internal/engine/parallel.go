package engine

import (
	"fmt"
	"os/exec"
	"strings"
	"sync"
)

type WorkerResult struct {
	TaskID string
	Output string
	Err    error
}

type ParallelExecutor struct {
	maxWorkers int
	events     chan Event
}

func NewParallelExecutor(maxWorkers int, events chan Event) *ParallelExecutor {
	return &ParallelExecutor{maxWorkers: maxWorkers, events: events}
}

func (pe *ParallelExecutor) Execute(tasks []TaskState) []WorkerResult {
	results := make([]WorkerResult, len(tasks))
	sem := make(chan struct{}, pe.maxWorkers)
	var wg sync.WaitGroup

	for i, task := range tasks {
		wg.Add(1)
		go func(idx int, t TaskState) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			pe.emit(WorkerStarted, map[string]interface{}{"task_id": t.ID, "worker": idx})

			result := WorkerResult{TaskID: t.ID}
			// In production: create git worktree, run agent, merge back
			result.Output = fmt.Sprintf("Parallel completed: %s", t.Title)

			pe.emit(WorkerCompleted, map[string]interface{}{"task_id": t.ID, "worker": idx})
			results[idx] = result
		}(i, task)
	}

	wg.Wait()
	return results
}

func (pe *ParallelExecutor) CreateWorktree(branch string, dir string) error {
	cmd := exec.Command("git", "worktree", "add", dir, "-b", branch)
	return cmd.Run()
}

func (pe *ParallelExecutor) RemoveWorktree(dir string) error {
	cmd := exec.Command("git", "worktree", "remove", dir, "--force")
	return cmd.Run()
}

func (pe *ParallelExecutor) DetectConflicts(branch string) bool {
	cmd := exec.Command("git", "merge", "--no-commit", "--no-ff", branch)
	err := cmd.Run()
	// Abort the test merge
	exec.Command("git", "merge", "--abort").Run()
	return err != nil
}

func (pe *ParallelExecutor) emit(t EventType, data map[string]interface{}) {
	select {
	case pe.events <- NewEvent(t, data):
	default:
	}
}

func GitBranch() string {
	out, err := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD").Output()
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(out))
}

func GitIsDirty() bool {
	out, err := exec.Command("git", "status", "--porcelain").Output()
	if err != nil {
		return false
	}
	return len(strings.TrimSpace(string(out))) > 0
}
