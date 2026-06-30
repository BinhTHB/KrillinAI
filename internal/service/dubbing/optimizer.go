package dubbing

import (
	"context"
	"fmt"
	"krillin-ai/internal/types"
	"strings"
)

type LLMOptimizer struct {
	chat types.ChatCompleter
}

func NewLLMOptimizer(chat types.ChatCompleter) *LLMOptimizer {
	return &LLMOptimizer{chat: chat}
}

func (o *LLMOptimizer) Optimize(ctx context.Context, text string, availableSeconds float64, reason string) (string, error) {
	if ctx != nil {
		if err := ctx.Err(); err != nil {
			return "", err
		}
	}
	if o == nil || o.chat == nil {
		return text, nil
	}
	prompt := fmt.Sprintf(`Rewrite the subtitle below into a single, concise sentence optimized for text-to-speech (TTS) voiceover.

Constraints:
1. Target duration: MUST be readable naturally within %.2f seconds
2. Preserve core meaning exactly — no added facts, no omitted key information
3. Output target language text ONLY — no explanations, no formatting
4. Single line of plain text
5. Use natural spoken language — contractions, conversational flow, simple sentence structure
6. Typical speech rate: ~150 words/min (English) / ~220 chars/min (Chinese) — choose wording that fits the time budget
7. If the original is already short enough, return it unchanged

Trigger reason: %s

Subtitle:
%s`, availableSeconds, reason, text)
	resp, err := o.chat.ChatCompletion(prompt)
	if err != nil {
		return "", err
	}
	resp = strings.TrimSpace(resp)
	resp = strings.ReplaceAll(resp, "\r", " ")
	resp = strings.ReplaceAll(resp, "\n", " ")
	resp = strings.Join(strings.Fields(resp), " ")
	if resp == "" {
		return text, nil
	}
	return resp, nil
}
