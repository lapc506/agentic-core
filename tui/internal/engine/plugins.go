package engine

import "fmt"

type AgentPlugin interface {
	Name() string
	Execute(prompt string) (string, error)
	DetectCompletion(output string) bool
	ValidateModel(model string) bool
}

type TrackerPlugin interface {
	Name() string
	GetTasks() ([]TaskState, error)
	GetNextTask() (*TaskState, error)
	UpdateTaskStatus(taskID string, status string) error
}

type PluginRegistry struct {
	agents   map[string]AgentPlugin
	trackers map[string]TrackerPlugin
}

func NewPluginRegistry() *PluginRegistry {
	return &PluginRegistry{
		agents:   make(map[string]AgentPlugin),
		trackers: make(map[string]TrackerPlugin),
	}
}

func (pr *PluginRegistry) RegisterAgent(plugin AgentPlugin) {
	pr.agents[plugin.Name()] = plugin
}

func (pr *PluginRegistry) RegisterTracker(plugin TrackerPlugin) {
	pr.trackers[plugin.Name()] = plugin
}

func (pr *PluginRegistry) GetAgent(name string) (AgentPlugin, error) {
	p, ok := pr.agents[name]
	if !ok {
		return nil, fmt.Errorf("agent plugin not found: %s", name)
	}
	return p, nil
}

func (pr *PluginRegistry) GetTracker(name string) (TrackerPlugin, error) {
	p, ok := pr.trackers[name]
	if !ok {
		return nil, fmt.Errorf("tracker plugin not found: %s", name)
	}
	return p, nil
}

func (pr *PluginRegistry) ListAgents() []string {
	names := make([]string, 0, len(pr.agents))
	for k := range pr.agents {
		names = append(names, k)
	}
	return names
}

func (pr *PluginRegistry) ListTrackers() []string {
	names := make([]string, 0, len(pr.trackers))
	for k := range pr.trackers {
		names = append(names, k)
	}
	return names
}
