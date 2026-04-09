package config

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/pelletier/go-toml/v2"
)

type Config struct {
	API      APIConfig      `toml:"api"`
	Agent    AgentConfig    `toml:"agent"`
	Theme    string         `toml:"theme"`
	Headless bool           `toml:"headless"`
	Error    ErrorConfig    `toml:"error"`
	Parallel ParallelConfig `toml:"parallel"`
}

type APIConfig struct {
	URL     string `toml:"url"`
	Timeout int    `toml:"timeout"`
}

type AgentConfig struct {
	Model            string   `toml:"model"`
	MaxIterations    int      `toml:"max_iterations"`
	CompletionTokens []string `toml:"completion_tokens"`
}

type ErrorConfig struct {
	Strategy   string `toml:"strategy"` // retry, skip, abort
	MaxRetries int    `toml:"max_retries"`
	BackoffMs  int    `toml:"backoff_ms"`
}

type ParallelConfig struct {
	Enabled    bool `toml:"enabled"`
	MaxWorkers int  `toml:"max_workers"`
}

func DefaultConfig() Config {
	return Config{
		API:   APIConfig{URL: "http://localhost:8080", Timeout: 30},
		Agent: AgentConfig{Model: "default", MaxIterations: 100, CompletionTokens: []string{"TASK_COMPLETE", "✅ Done"}},
		Theme: "dark",
		Error: ErrorConfig{Strategy: "retry", MaxRetries: 3, BackoffMs: 1000},
		Parallel: ParallelConfig{Enabled: false, MaxWorkers: 3},
	}
}

func Load() Config {
	cfg := DefaultConfig()

	// Tier 2: Global config
	if home, err := os.UserHomeDir(); err == nil {
		loadTOML(filepath.Join(home, ".config", "agentic-studio", "config.toml"), &cfg)
	}

	// Tier 3: Project config
	loadTOML(filepath.Join(".agentic-studio", "config.toml"), &cfg)

	// Tier 4: Environment variables
	applyEnv(&cfg)

	return cfg
}

func loadTOML(path string, cfg *Config) {
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	toml.Unmarshal(data, cfg)
}

func applyEnv(cfg *Config) {
	if v := os.Getenv("AGENTIC_STUDIO_URL"); v != "" {
		cfg.API.URL = v
	}
	if v := os.Getenv("AGENTIC_STUDIO_MODEL"); v != "" {
		cfg.Agent.Model = v
	}
	if v := os.Getenv("AGENTIC_STUDIO_THEME"); v != "" {
		cfg.Theme = v
	}
	if strings.ToLower(os.Getenv("AGENTIC_STUDIO_HEADLESS")) == "true" {
		cfg.Headless = true
	}
}
