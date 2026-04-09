package engine

import (
	"bytes"
	"os"
	"path/filepath"
	"text/template"
)

type TemplateData struct {
	TaskTitle       string
	TaskDescription string
	Context         string
	Constraints     string
	Agent           string
	Model           string
	Iteration       int
}

type TemplateManager struct {
	templates map[string]*template.Template
	dir       string
}

func NewTemplateManager(dir string) *TemplateManager {
	tm := &TemplateManager{dir: dir, templates: make(map[string]*template.Template)}
	tm.loadDefaults()
	tm.loadFromDir()
	return tm
}

func (tm *TemplateManager) loadDefaults() {
	defaultTpl := `Task: {{.TaskTitle}}

{{.TaskDescription}}

{{if .Context}}Context:
{{.Context}}
{{end}}
{{if .Constraints}}Constraints:
{{.Constraints}}
{{end}}
When complete, output TASK_COMPLETE on its own line.`

	t, _ := template.New("default").Parse(defaultTpl)
	tm.templates["default"] = t
}

func (tm *TemplateManager) loadFromDir() {
	if tm.dir == "" {
		return
	}
	entries, err := os.ReadDir(tm.dir)
	if err != nil {
		return
	}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		data, err := os.ReadFile(filepath.Join(tm.dir, name))
		if err != nil {
			continue
		}
		t, err := template.New(name).Parse(string(data))
		if err != nil {
			continue
		}
		tm.templates[name] = t
	}
}

func (tm *TemplateManager) Render(templateName string, data TemplateData) (string, error) {
	t, ok := tm.templates[templateName]
	if !ok {
		t = tm.templates["default"]
	}
	var buf bytes.Buffer
	if err := t.Execute(&buf, data); err != nil {
		return "", err
	}
	return buf.String(), nil
}

func (tm *TemplateManager) Available() []string {
	names := make([]string, 0, len(tm.templates))
	for k := range tm.templates {
		names = append(names, k)
	}
	return names
}
