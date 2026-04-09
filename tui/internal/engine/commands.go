package engine

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/pelletier/go-toml/v2"
)

type CustomCommand struct {
	Name        string `toml:"name"`
	Description string `toml:"description"`
	Prompt      string `toml:"prompt"`
	Group       string `toml:"-"`
}

type CommandRegistry struct {
	commands map[string]CustomCommand
}

func NewCommandRegistry() *CommandRegistry {
	return &CommandRegistry{commands: make(map[string]CustomCommand)}
}

func (cr *CommandRegistry) LoadFromDir(dir string) error {
	return filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !strings.HasSuffix(path, ".toml") {
			return nil
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return nil
		}
		var cmd CustomCommand
		if err := toml.Unmarshal(data, &cmd); err != nil {
			return nil
		}
		// Group from subdirectory
		rel, _ := filepath.Rel(dir, path)
		parts := strings.Split(rel, string(os.PathSeparator))
		if len(parts) > 1 {
			cmd.Group = parts[0]
		}
		if cmd.Name == "" {
			cmd.Name = strings.TrimSuffix(filepath.Base(path), ".toml")
		}
		key := cmd.Name
		if cmd.Group != "" {
			key = cmd.Group + ":" + cmd.Name
		}
		cr.commands[key] = cmd
		return nil
	})
}

func (cr *CommandRegistry) Execute(name string, args string) (string, error) {
	cmd, ok := cr.commands[name]
	if !ok {
		return "", fmt.Errorf("command not found: %s", name)
	}
	prompt := cmd.Prompt
	// Substitute {{args}}
	prompt = strings.ReplaceAll(prompt, "{{args}}", args)
	// Substitute !{command} with shell output
	for {
		start := strings.Index(prompt, "!{")
		if start == -1 {
			break
		}
		end := strings.Index(prompt[start:], "}")
		if end == -1 {
			break
		}
		shellCmd := prompt[start+2 : start+end]
		out, err := exec.Command("sh", "-c", shellCmd).Output()
		if err != nil {
			out = []byte(fmt.Sprintf("(error: %v)", err))
		}
		prompt = prompt[:start] + strings.TrimSpace(string(out)) + prompt[start+end+1:]
	}
	return prompt, nil
}

func (cr *CommandRegistry) List() []CustomCommand {
	cmds := make([]CustomCommand, 0, len(cr.commands))
	for _, cmd := range cr.commands {
		cmds = append(cmds, cmd)
	}
	return cmds
}

func (cr *CommandRegistry) Get(name string) (CustomCommand, bool) {
	cmd, ok := cr.commands[name]
	return cmd, ok
}
