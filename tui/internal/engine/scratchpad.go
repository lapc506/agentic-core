package engine

import (
	"os"
	"path/filepath"
	"strings"
)

type Scratchpad struct {
	dir string
}

func NewScratchpad(dir string) *Scratchpad {
	return &Scratchpad{dir: dir}
}

func (sp *Scratchpad) Init() error {
	return os.MkdirAll(sp.dir, 0755)
}

func (sp *Scratchpad) Write(filename string, content string) error {
	if err := sp.Init(); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(sp.dir, filename), []byte(content), 0644)
}

func (sp *Scratchpad) Read(filename string) (string, error) {
	data, err := os.ReadFile(filepath.Join(sp.dir, filename))
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func (sp *Scratchpad) ReadAll() (map[string]string, error) {
	files := make(map[string]string)
	entries, err := os.ReadDir(sp.dir)
	if err != nil {
		if os.IsNotExist(err) {
			return files, nil
		}
		return nil, err
	}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		data, err := os.ReadFile(filepath.Join(sp.dir, e.Name()))
		if err != nil {
			continue
		}
		files[e.Name()] = string(data)
	}
	return files, nil
}

func (sp *Scratchpad) AppendTodo(item string) error {
	existing, _ := sp.Read("TODO.md")
	if !strings.HasSuffix(existing, "\n") && len(existing) > 0 {
		existing += "\n"
	}
	existing += "- [ ] " + item + "\n"
	return sp.Write("TODO.md", existing)
}

func (sp *Scratchpad) CompleteTodo(item string) error {
	content, err := sp.Read("TODO.md")
	if err != nil {
		return err
	}
	content = strings.ReplaceAll(content, "- [ ] "+item, "- [x] "+item)
	return sp.Write("TODO.md", content)
}

func (sp *Scratchpad) Summary() string {
	files, _ := sp.ReadAll()
	if len(files) == 0 {
		return "(empty scratchpad)"
	}
	var sb strings.Builder
	for name, content := range files {
		sb.WriteString("--- " + name + " ---\n")
		// Truncate to first 500 chars
		if len(content) > 500 {
			content = content[:500] + "..."
		}
		sb.WriteString(content + "\n\n")
	}
	return sb.String()
}

func (sp *Scratchpad) Clear() error {
	return os.RemoveAll(sp.dir)
}

func (sp *Scratchpad) Dir() string { return sp.dir }
