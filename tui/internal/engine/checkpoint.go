package engine

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type Checkpoint struct {
	ID           string    `json:"id"`
	Message      string    `json:"message"`
	Timestamp    time.Time `json:"timestamp"`
	ToolCall     string    `json:"tool_call,omitempty"`
	FilesChanged []string  `json:"files_changed,omitempty"`
}

type CheckpointManager struct {
	shadowDir   string
	projectDir  string
	checkpoints []Checkpoint
}

func NewCheckpointManager(projectDir string) *CheckpointManager {
	home, _ := os.UserHomeDir()
	// Hash project dir for unique shadow repo
	hash := fmt.Sprintf("%x", []byte(projectDir))[:12]
	shadowDir := filepath.Join(home, ".agentic-studio", "history", hash)
	return &CheckpointManager{shadowDir: shadowDir, projectDir: projectDir}
}

func (cm *CheckpointManager) Init() error {
	if err := os.MkdirAll(cm.shadowDir, 0755); err != nil {
		return err
	}
	// Init shadow git repo if not exists
	gitDir := filepath.Join(cm.shadowDir, ".git")
	if _, err := os.Stat(gitDir); os.IsNotExist(err) {
		cmd := exec.Command("git", "init")
		cmd.Dir = cm.shadowDir
		return cmd.Run()
	}
	return nil
}

func (cm *CheckpointManager) Save(message string, toolCall string) (*Checkpoint, error) {
	// Copy project files to shadow dir (excluding .git, node_modules, etc.)
	cmd := exec.Command("rsync", "-a", "--exclude=.git", "--exclude=node_modules",
		"--exclude=__pycache__", "--exclude=.venv", "--exclude=build",
		cm.projectDir+"/", cm.shadowDir+"/")
	if err := cmd.Run(); err != nil {
		// Fallback if rsync not available
		return nil, fmt.Errorf("rsync failed: %w", err)
	}

	// Stage and commit
	stageCmd := exec.Command("git", "add", "-A")
	stageCmd.Dir = cm.shadowDir
	stageCmd.Run()

	id := time.Now().Format("20060102-150405")
	commitMsg := fmt.Sprintf("[checkpoint:%s] %s", id, message)
	commitCmd := exec.Command("git", "commit", "-m", commitMsg, "--allow-empty")
	commitCmd.Dir = cm.shadowDir
	commitCmd.Run()

	cp := Checkpoint{
		ID: id, Message: message, Timestamp: time.Now(), ToolCall: toolCall,
	}
	cm.checkpoints = append(cm.checkpoints, cp)
	return &cp, nil
}

func (cm *CheckpointManager) List() []Checkpoint {
	return cm.checkpoints
}

func (cm *CheckpointManager) Restore(checkpointID string) error {
	// Find the commit with this checkpoint ID
	cmd := exec.Command("git", "log", "--oneline", "--all")
	cmd.Dir = cm.shadowDir
	out, err := cmd.Output()
	if err != nil {
		return err
	}

	for _, line := range strings.Split(string(out), "\n") {
		if strings.Contains(line, fmt.Sprintf("[checkpoint:%s]", checkpointID)) {
			hash := strings.Fields(line)[0]
			// Checkout that commit
			checkoutCmd := exec.Command("git", "checkout", hash, "--", ".")
			checkoutCmd.Dir = cm.shadowDir
			if err := checkoutCmd.Run(); err != nil {
				return err
			}
			// Copy back to project
			copyCmd := exec.Command("rsync", "-a", "--exclude=.git",
				cm.shadowDir+"/", cm.projectDir+"/")
			return copyCmd.Run()
		}
	}
	return fmt.Errorf("checkpoint not found: %s", checkpointID)
}

func (cm *CheckpointManager) ShadowDir() string { return cm.shadowDir }
