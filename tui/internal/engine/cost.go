package engine

import "fmt"

type ModelTier string

const (
	TierLow    ModelTier = "low"
	TierMedium ModelTier = "medium"
	TierHigh   ModelTier = "high"
)

type ModelPricing struct {
	InputPer1K  float64
	OutputPer1K float64
}

type CostTracker struct {
	TierModels  map[ModelTier]string
	Pricing     map[string]ModelPricing
	TotalCost   float64
	TotalInput  int
	TotalOutput int
}

func NewCostTracker() *CostTracker {
	return &CostTracker{
		TierModels: map[ModelTier]string{
			TierLow:    "meta-llama/llama-3.2-3b-instruct:free",
			TierMedium: "anthropic/claude-sonnet-4-6",
			TierHigh:   "anthropic/claude-opus-4-6",
		},
		Pricing: map[string]ModelPricing{
			"meta-llama/llama-3.2-3b-instruct:free": {InputPer1K: 0, OutputPer1K: 0},
			"anthropic/claude-sonnet-4-6":            {InputPer1K: 0.003, OutputPer1K: 0.015},
			"anthropic/claude-opus-4-6":              {InputPer1K: 0.015, OutputPer1K: 0.075},
		},
	}
}

func (ct *CostTracker) ModelForTier(tier string) string {
	t := ModelTier(tier)
	if model, ok := ct.TierModels[t]; ok {
		return model
	}
	return ct.TierModels[TierMedium]
}

func (ct *CostTracker) RecordUsage(model string, inputTokens, outputTokens int) float64 {
	ct.TotalInput += inputTokens
	ct.TotalOutput += outputTokens

	pricing, ok := ct.Pricing[model]
	if !ok {
		return 0
	}

	cost := (float64(inputTokens) / 1000 * pricing.InputPer1K) +
		(float64(outputTokens) / 1000 * pricing.OutputPer1K)
	ct.TotalCost += cost
	return cost
}

func (ct *CostTracker) Summary() string {
	return fmt.Sprintf("Tokens: %d in / %d out | Cost: $%.4f",
		ct.TotalInput, ct.TotalOutput, ct.TotalCost)
}

func (ct *CostTracker) SetTierModel(tier ModelTier, model string) {
	ct.TierModels[tier] = model
}

func (ct *CostTracker) SetPricing(model string, inputPer1K, outputPer1K float64) {
	ct.Pricing[model] = ModelPricing{InputPer1K: inputPer1K, OutputPer1K: outputPer1K}
}
