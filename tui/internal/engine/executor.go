package engine

import (
	"context"
	"fmt"
	"time"
)

type ExecutionPhase string

const (
	PhaseSelectTask  ExecutionPhase = "select_task"
	PhaseBuildPrompt ExecutionPhase = "build_prompt"
	PhaseExecute     ExecutionPhase = "execute"
	PhaseDetect      ExecutionPhase = "detect"
	PhaseAdvance     ExecutionPhase = "advance"
)

type Executor struct {
	session  *SessionManager
	detector *CompletionDetector
	events   chan Event
	phase    ExecutionPhase
	running  bool
}

func NewExecutor(session *SessionManager, detector *CompletionDetector, events chan Event) *Executor {
	return &Executor{
		session:  session,
		detector: detector,
		events:   events,
		phase:    PhaseSelectTask,
	}
}

func (e *Executor) Start(ctx context.Context) error {
	s := e.session.Current()
	if s == nil {
		return fmt.Errorf("no session loaded")
	}
	e.running = true
	s.State = StateRunning
	s.StartedAt = time.Now()
	e.emit(EngineStarted, nil)
	e.session.Save(s)

	for e.running {
		select {
		case <-ctx.Done():
			e.running = false
			s.State = StatePaused
			e.emit(EnginePaused, nil)
			e.session.Save(s)
			return ctx.Err()
		default:
			if err := e.runIteration(s); err != nil {
				return err
			}
			if s.CurrentTask >= len(s.Tasks) {
				e.running = false
				s.State = StateCompleted
				e.emit(EngineStopped, map[string]interface{}{"reason": "all_tasks_complete"})
				e.session.Save(s)
				return nil
			}
		}
	}
	return nil
}

func (e *Executor) Pause() {
	e.running = false
}

func (e *Executor) IsRunning() bool        { return e.running }
func (e *Executor) Phase() ExecutionPhase  { return e.phase }

func (e *Executor) runIteration(s *Session) error {
	s.Iterations++
	e.emit(IterationStarted, map[string]interface{}{"iteration": s.Iterations})

	// Phase 1: Select task
	e.phase = PhaseSelectTask
	if s.CurrentTask >= len(s.Tasks) {
		return nil
	}
	task := &s.Tasks[s.CurrentTask]
	task.Status = "running"
	e.emit(TaskSelected, map[string]interface{}{"task_id": task.ID, "title": task.Title})

	// Phase 2: Build prompt (placeholder — in production, uses templates)
	e.phase = PhaseBuildPrompt
	_ = fmt.Sprintf("Task: %s\nDescription: %s", task.Title, task.Description)

	// Phase 3: Execute (placeholder — in production, calls agent API)
	e.phase = PhaseExecute
	e.emit(AgentStarted, map[string]interface{}{"task_id": task.ID})
	// Simulated agent output for now
	output := fmt.Sprintf("Completed task: %s", task.Title)
	e.emit(AgentOutput, map[string]interface{}{"output": output})
	e.emit(AgentCompleted, map[string]interface{}{"task_id": task.ID})

	// Phase 4: Detect completion
	e.phase = PhaseDetect
	task.Status = "completed"
	task.Result = output
	task.Iteration = s.Iterations

	// Phase 5: Advance
	e.phase = PhaseAdvance
	s.CurrentTask++
	e.emit(TaskCompleted, map[string]interface{}{"task_id": task.ID})
	e.emit(IterationCompleted, map[string]interface{}{"iteration": s.Iterations})
	e.session.Save(s)

	return nil
}

func (e *Executor) emit(t EventType, data map[string]interface{}) {
	select {
	case e.events <- NewEvent(t, data):
	default:
		// Non-blocking: drop event if channel full
	}
}
