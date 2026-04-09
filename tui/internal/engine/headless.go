package engine

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"time"
)

type HeadlessRunner struct {
	executor *Executor
	events   chan Event
	output   io.Writer
}

func NewHeadlessRunner(executor *Executor, events chan Event) *HeadlessRunner {
	return &HeadlessRunner{
		executor: executor,
		events:   events,
		output:   os.Stdout,
	}
}

func (hr *HeadlessRunner) Run() error {
	// Start event logger in background
	done := make(chan struct{})
	go func() {
		defer close(done)
		encoder := json.NewEncoder(hr.output)
		for event := range hr.events {
			entry := map[string]interface{}{
				"type":      event.Type,
				"timestamp": event.Timestamp.Format(time.RFC3339),
				"data":      event.Data,
			}
			encoder.Encode(entry)
		}
	}()

	// Run executor
	err := hr.executor.Start(nil)

	// Close events channel and wait for logger
	close(hr.events)
	<-done

	if err != nil {
		fmt.Fprintf(os.Stderr, "Execution failed: %v\n", err)
		return err
	}

	return nil
}
