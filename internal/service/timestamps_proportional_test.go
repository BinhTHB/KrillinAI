package service

import (
	"fmt"
	"strings"
	"testing"

	"krillin-ai/internal/types"
	"krillin-ai/pkg/util"
)

func TestGenerateTimestampsUsesProportionalFallbackForCorruptedCJKWords(t *testing.T) {
	words := []types.Word{
		{Num: 0, Text: "你", Start: 0.0, End: 0.2},
		{Num: 1, Text: "��", Start: 0.2, End: 0.4},
		{Num: 2, Text: "好", Start: 0.4, End: 0.6},
		{Num: 3, Text: "世", Start: 0.6, End: 0.8},
		{Num: 4, Text: "�", Start: 0.8, End: 1.0},
		{Num: 5, Text: "界", Start: 1.0, End: 1.2},
	}
	blocks := []*util.SrtBlock{
		{Index: 1, OriginLanguageSentence: "你好"},
		{Index: 2, OriginLanguageSentence: "世界"},
	}

	gen := NewTimestampGenerator()
	result, err := gen.GenerateTimestamps(blocks, words, types.LanguageNameSimplifiedChinese, 0)
	if err != nil {
		t.Fatalf("GenerateTimestamps returned error: %v", err)
	}

	if len(result) != len(blocks) {
		t.Fatalf("expected %d blocks, got %d", len(blocks), len(result))
	}

	lastEnd := 0.0
	for i, block := range result {
		start, end := parseTestTimestamp(t, block.Timestamp)
		if end <= start {
			t.Fatalf("block %d has invalid timestamp %s", i, block.Timestamp)
		}
		if start < lastEnd-0.01 {
			t.Fatalf("block %d is non-monotonic: start=%f lastEnd=%f", i, start, lastEnd)
		}
		lastEnd = end
	}
	if lastEnd > words[len(words)-1].End+0.01 {
		t.Fatalf("last timestamp %.2f exceeds last word end %.2f", lastEnd, words[len(words)-1].End)
	}
}

func TestGenerateTimestampsGreedyMergesConsecutiveFailures(t *testing.T) {
	words := []types.Word{{Text: "end", Start: 0, End: 4}}
	blocks := []*util.SrtBlock{
		{Index: 1, OriginLanguageSentence: "a"},
		{Index: 2, OriginLanguageSentence: "bbb"},
		{Index: 3, OriginLanguageSentence: "c"},
	}

	gen := NewTimestampGenerator()
	lang := types.StandardLanguageCode("test-greedy")
	gen.RegisterMatcher(lang, greedyMergeTestMatcher{})
	result, err := gen.GenerateTimestamps(blocks, words, lang, 0)
	if err != nil {
		t.Fatalf("GenerateTimestamps returned error: %v", err)
	}

	start1, end1 := parseTestTimestamp(t, result[0].Timestamp)
	start2, end2 := parseTestTimestamp(t, result[1].Timestamp)
	start3, end3 := parseTestTimestamp(t, result[2].Timestamp)
	if start1 != 1.0 || end2 != 3.0 {
		t.Fatalf("expected failed blocks to use merged hard anchors 1.0-3.0, got %.3f-%.3f", start1, end2)
	}
	if end1 >= end2 || start2 < end1-0.01 {
		t.Fatalf("expected merged blocks to be monotonic, got %s then %s", result[0].Timestamp, result[1].Timestamp)
	}
	if start3 < end2-0.01 || end3 <= start3 {
		t.Fatalf("expected following matched block after merged failures, got %s", result[2].Timestamp)
	}
}

type greedyMergeTestMatcher struct{}

func (greedyMergeTestMatcher) MatchSentenceTimestamp(sentence string, _ []types.Word, _ float64) (float64, float64, error) {
	switch sentence {
	case "abbb":
		return 1.0, 3.0, nil
	case "c":
		return 3.0, 4.0, nil
	default:
		return 0, 0, fmt.Errorf("forced mismatch")
	}
}

func (greedyMergeTestMatcher) GetLanguageType() types.StandardLanguageCode {
	return types.StandardLanguageCode("test-greedy")
}

func parseTestTimestamp(t *testing.T, timestamp string) (float64, float64) {
	t.Helper()
	parts := strings.Split(timestamp, " --> ")
	if len(parts) != 2 {
		t.Fatalf("invalid timestamp: %s", timestamp)
	}
	return parseTestClock(t, parts[0]), parseTestClock(t, parts[1])
}

func parseTestClock(t *testing.T, value string) float64 {
	t.Helper()
	var h, m, s, ms int
	if _, err := fmt.Sscanf(value, "%d:%d:%d,%d", &h, &m, &s, &ms); err != nil {
		t.Fatalf("parse clock %s: %v", value, err)
	}
	return float64(h)*3600 + float64(m)*60 + float64(s) + float64(ms)/1000
}
