package service

import (
	"testing"

	"go.uber.org/zap"
	"krillin-ai/internal/types"
	"krillin-ai/log"
	"krillin-ai/pkg/util"
)

func TestGenerateTimestampsAdvancesAfterLongBlocks(t *testing.T) {
	log.Logger = zap.NewNop()
	words := []types.Word{
		{Num: 0, Text: "甲", Start: 0, End: 1},
		{Num: 1, Text: "乙", Start: 1, End: 2},
		{Num: 2, Text: "丙", Start: 2, End: 3},
		{Num: 3, Text: "丁", Start: 3, End: 4},
		{Num: 4, Text: "戊", Start: 4, End: 5},
		{Num: 5, Text: "己", Start: 5, End: 6},
		{Num: 6, Text: "庚", Start: 6, End: 7},
		{Num: 7, Text: "辛", Start: 7, End: 8},
		{Num: 8, Text: "壬", Start: 8, End: 9},
		{Num: 9, Text: "癸", Start: 9, End: 10},
		{Num: 10, Text: "甲", Start: 12, End: 13},
		{Num: 11, Text: "乙", Start: 13, End: 14},
	}
	blocks := []*util.SrtBlock{
		{Index: 1, OriginLanguageSentence: "甲乙丙丁戊己庚辛壬癸", TargetLanguageSentence: "long"},
		{Index: 2, OriginLanguageSentence: "甲乙", TargetLanguageSentence: "repeat"},
	}
	updated, err := NewTimestampGenerator().GenerateTimestamps(blocks, words, types.LanguageNameSimplifiedChinese, 0)
	if err != nil {
		t.Fatalf("GenerateTimestamps() error = %v", err)
	}
	if got := updated[1].Timestamp; got == "00:00:00,000 --> 00:00:02,000" {
		t.Fatalf("second repeated sentence timestamp = %q, reused a pre-long-block match", got)
	}
	if got := updated[1].Timestamp; got != "00:00:12,000 --> 00:00:14,000" {
		t.Fatalf("second repeated sentence timestamp = %q, want word-level matched timing from CJKSentenceMatcher", got)
	}
}

func TestGenerateTimestampsDoesNotMutateInputBlocks(t *testing.T) {
	log.Logger = zap.NewNop()
	words := []types.Word{{Text: "甲", Start: 0, End: 1}}
	blocks := []*util.SrtBlock{{Index: 1, OriginLanguageSentence: "甲", TargetLanguageSentence: "one"}}

	updated, err := NewTimestampGenerator().GenerateTimestamps(blocks, words, types.LanguageNameSimplifiedChinese, 0)
	if err != nil {
		t.Fatalf("GenerateTimestamps() error = %v", err)
	}
	if blocks[0].Timestamp != "" {
		t.Fatalf("input block timestamp was mutated: %q", blocks[0].Timestamp)
	}
	if updated[0].Timestamp == "" {
		t.Fatalf("updated block timestamp is empty")
	}
}

func TestFuzzyMatchCapsWideRepeatedCharacterMatches(t *testing.T) {
	matcher := &BaseLanguageMatcher{}
	words := []types.Word{
		{Text: "那个", Start: 0.05, End: 0.90},
		{Text: "男", Start: 0.90, End: 1.35},
		{Text: "人", Start: 1.35, End: 1.77},
		{Text: "了", Start: 302.0, End: 302.66},
	}

	start, end, err := matcher.fuzzyMatchSentence("那个男人韩贝塔又回来了", words, 0)
	if err != nil {
		t.Fatalf("fuzzyMatchSentence() error = %v", err)
	}
	if start != 0.05 {
		t.Fatalf("start = %v, want 0.05", start)
	}
	if end > 15.05 {
		t.Fatalf("end = %v, fuzzy match spanned far repeated character", end)
	}
}
