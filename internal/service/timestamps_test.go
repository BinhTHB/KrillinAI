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
		{Text: "甲", Start: 0, End: 1},
		{Text: "乙", Start: 1, End: 2},
		{Text: "丙", Start: 2, End: 3},
		{Text: "丁", Start: 3, End: 4},
		{Text: "戊", Start: 4, End: 5},
		{Text: "己", Start: 5, End: 6},
		{Text: "庚", Start: 6, End: 7},
		{Text: "辛", Start: 7, End: 8},
		{Text: "壬", Start: 8, End: 9},
		{Text: "癸", Start: 9, End: 10},
		{Text: "甲", Start: 12, End: 13},
		{Text: "乙", Start: 13, End: 14},
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
	if got := updated[1].Timestamp; got != "00:00:10,000 --> 00:00:11,000" && got != "00:00:12,000 --> 00:00:14,000" {
		t.Fatalf("second repeated sentence timestamp = %q, want monotonic post-long-block timing", got)
	}
}
