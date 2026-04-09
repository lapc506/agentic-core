package engine

import "fmt"

type RewindPoint struct {
	Index        int    `json:"index"`
	Description  string `json:"description"`
	CheckpointID string `json:"checkpoint_id,omitempty"`
	TurnNumber   int    `json:"turn_number"`
}

type RewindManager struct {
	points      []RewindPoint
	checkpoints *CheckpointManager
	session     *SessionManager
}

func NewRewindManager(checkpoints *CheckpointManager, session *SessionManager) *RewindManager {
	return &RewindManager{checkpoints: checkpoints, session: session}
}

func (rm *RewindManager) AddPoint(description string, checkpointID string, turnNumber int) {
	rm.points = append(rm.points, RewindPoint{
		Index: len(rm.points), Description: description,
		CheckpointID: checkpointID, TurnNumber: turnNumber,
	})
}

func (rm *RewindManager) List() []RewindPoint {
	return rm.points
}

func (rm *RewindManager) RewindTo(index int, revertFiles bool, revertConversation bool) error {
	if index < 0 || index >= len(rm.points) {
		return fmt.Errorf("invalid rewind index: %d", index)
	}
	point := rm.points[index]

	if revertFiles && point.CheckpointID != "" {
		if err := rm.checkpoints.Restore(point.CheckpointID); err != nil {
			return fmt.Errorf("file revert failed: %w", err)
		}
	}

	if revertConversation {
		s := rm.session.Current()
		if s != nil {
			s.CurrentTask = point.TurnNumber
			s.Iterations = point.TurnNumber
			rm.session.Save(s) //nolint:errcheck
		}
	}

	// Truncate rewind points
	rm.points = rm.points[:index+1]
	return nil
}

func (rm *RewindManager) CanRewind() bool {
	return len(rm.points) > 0
}
