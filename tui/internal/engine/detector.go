package engine

import (
	"regexp"
	"strings"
)

type CompletionDetector struct {
	patterns []*regexp.Regexp
}

func NewCompletionDetector(patterns []string) *CompletionDetector {
	cd := &CompletionDetector{}
	if len(patterns) == 0 {
		patterns = []string{
			`<promise>COMPLETE</promise>`,
			`TASK_COMPLETE`,
			`✅\s*(?:Done|Complete|Finished)`,
		}
	}
	for _, p := range patterns {
		if re, err := regexp.Compile(p); err == nil {
			cd.patterns = append(cd.patterns, re)
		}
	}
	return cd
}

func (cd *CompletionDetector) IsComplete(output string) bool {
	for _, re := range cd.patterns {
		if re.MatchString(output) {
			return true
		}
	}
	return false
}

func (cd *CompletionDetector) IsError(output string) bool {
	errorSignals := []string{"TASK_FAILED", "ERROR:", "panic:", "fatal:"}
	lower := strings.ToLower(output)
	for _, sig := range errorSignals {
		if strings.Contains(lower, strings.ToLower(sig)) {
			return true
		}
	}
	return false
}
