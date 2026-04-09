package engine

import (
	"fmt"
	"math"
	"time"
)

type ErrorStrategy string

const (
	StrategyRetry ErrorStrategy = "retry"
	StrategySkip  ErrorStrategy = "skip"
	StrategyAbort ErrorStrategy = "abort"
)

type ErrorHandler struct {
	Strategy   ErrorStrategy
	MaxRetries int
	BaseDelay  time.Duration
}

func NewErrorHandler(strategy string, maxRetries int, baseDelayMs int) *ErrorHandler {
	s := StrategyRetry
	switch strategy {
	case "skip":
		s = StrategySkip
	case "abort":
		s = StrategyAbort
	}
	return &ErrorHandler{
		Strategy:   s,
		MaxRetries: maxRetries,
		BaseDelay:  time.Duration(baseDelayMs) * time.Millisecond,
	}
}

type ErrorAction string

const (
	ActionRetry ErrorAction = "retry"
	ActionSkip  ErrorAction = "skip"
	ActionAbort ErrorAction = "abort"
)

func (h *ErrorHandler) Handle(err error, attempt int) (ErrorAction, time.Duration) {
	switch h.Strategy {
	case StrategyRetry:
		if attempt >= h.MaxRetries {
			return ActionSkip, 0 // Exhaust retries → skip
		}
		delay := h.backoff(attempt)
		return ActionRetry, delay
	case StrategySkip:
		return ActionSkip, 0
	case StrategyAbort:
		return ActionAbort, 0
	default:
		return ActionAbort, 0
	}
}

func (h *ErrorHandler) backoff(attempt int) time.Duration {
	delay := h.BaseDelay * time.Duration(math.Pow(2, float64(attempt)))
	cap := 30 * time.Second
	if delay > cap {
		delay = cap
	}
	return delay
}

func (h *ErrorHandler) Describe() string {
	return fmt.Sprintf("strategy=%s max_retries=%d base_delay=%s", h.Strategy, h.MaxRetries, h.BaseDelay)
}
