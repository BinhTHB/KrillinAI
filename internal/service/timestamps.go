package service

import (
	"fmt"
	"strings"

	"krillin-ai/internal/types"
	"krillin-ai/log"

	"krillin-ai/pkg/util"

	"go.uber.org/zap"
)

// TimestampMatcher defines the interface for different language timestamp matching algorithms
type TimestampMatcher interface {
	// MatchSentenceTimestamp finds the start and end timestamps for a sentence
	// lastTs is the last known timestamp
	MatchSentenceTimestamp(sentence string, words []types.Word, lastTs float64) (startTime, endTime float64, err error)
	// GetLanguageType returns the language type this matcher supports
	GetLanguageType() types.StandardLanguageCode
}

// TimestampGenerator handles timestamp generation for multiple languages
type TimestampGenerator struct {
	matchers map[types.StandardLanguageCode]TimestampMatcher
}

// NewTimestampGenerator creates a new timestamp generator with default matchers
func NewTimestampGenerator() *TimestampGenerator {
	generator := &TimestampGenerator{
		matchers: make(map[types.StandardLanguageCode]TimestampMatcher),
	}

	// Register Base matcher
	baseMatcher := &BaseLanguageMatcher{language: types.StandardLanguageCode("base")}
	generator.RegisterMatcher(types.StandardLanguageCode("base"), baseMatcher)
	generator.RegisterMatcher(types.LanguageNameEnglish, baseMatcher)
	generator.RegisterMatcher(types.LanguageNameFinnish, baseMatcher)
	generator.RegisterMatcher(types.LanguageNameThai, baseMatcher)

	// Register CJK matcher that uses word-level timestamp matching instead of proportional division
	cjkMatcher := &CJKSentenceMatcher{}
	generator.RegisterMatcher(types.LanguageNameSimplifiedChinese, cjkMatcher)
	generator.RegisterMatcher(types.LanguageNameTraditionalChinese, cjkMatcher)
	generator.RegisterMatcher(types.LanguageNameJapanese, cjkMatcher)
	generator.RegisterMatcher(types.LanguageNameKorean, cjkMatcher)

	return generator
}

// RegisterMatcher registers a timestamp matcher for a specific language
func (tg *TimestampGenerator) RegisterMatcher(language types.StandardLanguageCode, matcher TimestampMatcher) {
	tg.matchers[language] = matcher
}

// GenerateTimestamps generates timestamps for SRT blocks using the appropriate language matcher
func (tg *TimestampGenerator) GenerateTimestamps(srtBlocks []*util.SrtBlock, words []types.Word, language types.StandardLanguageCode, tsOffset float64) ([]*util.SrtBlock, error) {
	matcher, exists := tg.matchers[language]
	if !exists {
		// Fallback to English matcher for unsupported languages
		matcher = tg.matchers[types.StandardLanguageCode("base")]
		if matcher == nil {
			return nil, fmt.Errorf("no timestamp matcher available for language: %s", language)
		}
		if logger := log.GetLogger(); logger != nil {
			logger.Warn("Using fallback base matcher for unsupported language",
				zap.String("language", string(language)))
		}
	}

	var lastEndTime float64
	updatedBlocks := make([]*util.SrtBlock, len(srtBlocks))

	for i, block := range srtBlocks {
		blockCopy := *block
		updatedBlocks[i] = &blockCopy

		if block.OriginLanguageSentence == "" {
			// Skip empty sentences
			continue
		}

		startTime, endTime, err := matcher.MatchSentenceTimestamp(block.OriginLanguageSentence, words, lastEndTime)
		if err != nil {
			if logger := log.GetLogger(); logger != nil {
				logger.Warn("Failed to match sentence timestamp",
					zap.String("sentence", block.OriginLanguageSentence),
					zap.Error(err))
			}
			// Use proportional fallback for remaining audio span instead of fixed 1s
			remainingBlocks := len(srtBlocks) - i
			if remainingBlocks > 0 && len(words) > 0 {
				remainingSpan := words[len(words)-1].End - lastEndTime
				if remainingSpan > 0 {
					fallbackDuration := remainingSpan / float64(remainingBlocks)
					if fallbackDuration < 0.35 {
						fallbackDuration = 0.35
					}
					startTime = lastEndTime
					endTime = lastEndTime + fallbackDuration
				} else {
					startTime = lastEndTime
					endTime = lastEndTime + 1.0
				}
			} else {
				startTime = lastEndTime
				endTime = lastEndTime + 1.0
			}
		} else {
			// Ensure timestamps don't overlap with previous block
			if startTime < lastEndTime {
				startTime = lastEndTime
			}
			if endTime <= startTime {
				endTime = startTime + 1.0 // Minimum 1 second duration
			}
		}

		// Generate timestamp string
		updatedBlocks[i].Timestamp = util.ConvertTimes(float32(startTime+tsOffset), float32(endTime+tsOffset))
		lastEndTime = endTime

		if logger := log.GetLogger(); logger != nil {
			logger.Debug("Generated timestamp for sentence",
				zap.Int("index", block.Index),
				zap.String("sentence", block.OriginLanguageSentence),
				zap.Any("startTime", startTime),
				zap.Any("endTime", endTime))
		}
	}

	return updatedBlocks, nil
}

// // AlphabeticLanguageMatcher handles timestamp matching for alphabetic languages (English, French, etc.)
// type AlphabeticLanguageMatcher struct {
// 	language types.StandardLanguageCode
// }

// func (alm *AlphabeticLanguageMatcher) GetLanguageType() types.StandardLanguageCode {
// 	return alm.language
// }

// func (alm *AlphabeticLanguageMatcher) MatchSentenceTimestamp(sentence string, words []types.Word, lastTs float64) (startTime, endTime float64, err error) {
// 	if sentence == "" || len(words) == 0 {
// 		return 0, 0, fmt.Errorf("empty sentence or words")
// 	}

// 	// Clean and split sentence into words
// 	sentenceWords := alm.extractWords(sentence)
// 	if len(sentenceWords) == 0 {
// 		return 0, 0, fmt.Errorf("no valid words found in sentence")
// 	}

// 	// Find matching words using fuzzy matching, prioritizing unused words
// 	matchedWords := alm.findMatchingWords(sentenceWords, words, lastTs)
// 	if len(matchedWords) == 0 {
// 		return 0, 0, fmt.Errorf("no matching words found")
// 	}

// 	// Find the maximum increasing subsequence for better accuracy
// 	beginWordIndex, endWordIndex := jumpFindMaxIncreasingSubArrayTs(matchedWords)
// 	if (endWordIndex - beginWordIndex) == 0 {
// 		log.GetLogger().Warn("getSentenceTimestamps no valid sentence",
// 			zap.String("sentence", sentence),
// 			zap.Int("beginWordIndex", beginWordIndex),
// 			zap.Int("endWordIndex", endWordIndex))
// 		return 0, 0, errors.New("getSentenceTimestamps no valid sentence")
// 	}

// 	// 找到最大连续子数组后，再去找整个句子开始和结束的时间戳
// 	beginWord := matchedWords[beginWordIndex]
// 	endWord := matchedWords[endWordIndex-1]
// 	if endWordIndex-beginWordIndex == len(matchedWords) {
// 		return beginWord.Start, endWord.End, nil
// 	}

// 	if beginWordIndex > 0 {
// 		for i, j := beginWordIndex-1, beginWord.Num-1; i >= 0 && j >= 0; {
// 			if words[j].Text == "" {
// 				j--
// 				continue
// 			}
// 			if strings.EqualFold(words[j].Text, matchedWords[i].Text) {
// 				beginWord = words[j]
// 				matchedWords[i] = beginWord
// 			} else {
// 				break
// 			}

// 			i--
// 			j--
// 		}
// 	}

// 	if endWordIndex < len(matchedWords) {
// 		for i, j := endWordIndex, endWord.Num+1; i < len(matchedWords) && j < len(words); {
// 			if words[j].Text == "" {
// 				j++
// 				continue
// 			}
// 			if strings.EqualFold(words[j].Text, matchedWords[i].Text) {
// 				endWord = words[j]
// 				matchedWords[i] = endWord
// 			} else {
// 				break
// 			}

// 			i++
// 			j++
// 		}
// 	}

// 	if beginWord.Num > matchedWords[0].Num && beginWord.Num-matchedWords[0].Num < 10 {
// 		beginWord = matchedWords[0]
// 	}

// 	if matchedWords[len(matchedWords)-1].Num > endWord.Num && matchedWords[len(matchedWords)-1].Num-endWord.Num < 10 {
// 		endWord = matchedWords[len(matchedWords)-1]
// 	}

// 	startTs := beginWord.Start
// 	endTs := endWord.End
// 	if startTs < lastTs {
// 		startTs = lastTs
// 	}
// 	if beginWord.Num != endWord.Num && endWord.End > lastTs {
// 		// Update lastTs for potential future use
// 		_ = endWord.End
// 	}

// 	return startTs, endTs, nil
// }

// func (alm *AlphabeticLanguageMatcher) extractWords(sentence string) []string {
// 	// Remove punctuation and split by whitespace
// 	cleaned := regexp.MustCompile(`[^\w\s']+`).ReplaceAllString(sentence, " ")
// 	words := strings.Fields(strings.ToLower(cleaned))

// 	var result []string
// 	for _, word := range words {
// 		if len(word) > 1 { // Filter out single characters
// 			result = append(result, word)
// 		}
// 	}
// 	return result
// }

// func (alm *AlphabeticLanguageMatcher) findMatchingWords(sentenceWords []string, words []types.Word, lastTs float64) []types.Word {
// 	newSentenceWords := make([]types.Word, 0)
// 	thisLastTs := lastTs
// 	sentenceWordIndex := 0
// 	wordNow := words[sentenceWordIndex]
// 	for _, sentenceWord := range sentenceWords {
// 		for sentenceWordIndex < len(words) {
// 			for sentenceWordIndex < len(words) && !strings.EqualFold(words[sentenceWordIndex].Text, sentenceWord) {
// 				sentenceWordIndex++
// 			}

// 			if sentenceWordIndex >= len(words) {
// 				break
// 			}

// 			wordNow = words[sentenceWordIndex]
// 			if wordNow.Start < thisLastTs {
// 				sentenceWordIndex++
// 				continue
// 			} else {
// 				break
// 			}
// 		}

// 		if sentenceWordIndex >= len(words) {
// 			newSentenceWords = append(newSentenceWords, types.Word{
// 				Text: sentenceWord,
// 			})
// 			sentenceWordIndex = 0
// 			continue
// 		}

// 		newSentenceWords = append(newSentenceWords, wordNow)
// 		sentenceWordIndex = 0
// 	}

// 	// for _, sentenceWord := range newSentenceWords {
// 	// 	// Find best matching word, prioritizing unused words
// 	// 	bestMatch, _, similarity := alm.findBestMatch(sentenceWord, words, lastTs)
// 	// 	if similarity > 0.6 { // Similarity threshold
// 	// 		matched = append(matched, bestMatch)
// 	// 	}
// 	// }

// 	return newSentenceWords
// }

// func (alm *AlphabeticLanguageMatcher) findBestMatch(target string, words []types.Word, lastTs float64) (types.Word, int, float64) {
// 	var bestWord types.Word
// 	var bestSimilarity float64
// 	bestIndex := -1

// 	// First pass: try to find unused words
// 	for i, word := range words {
// 		if word.End < lastTs {
// 			continue // Skip already used words
// 		}

// 		cleanWord := strings.ToLower(util.CleanPunctuation(word.Text))
// 		similarity := alm.calculateSimilarity(target, cleanWord)
// 		if similarity > bestSimilarity {
// 			bestSimilarity = similarity
// 			bestWord = word
// 			bestIndex = i
// 		}
// 	}

// 	// If no unused word found with good similarity, fallback to used words
// 	if bestSimilarity < 0.6 {
// 		for i, word := range words {
// 			cleanWord := strings.ToLower(util.CleanPunctuation(word.Text))
// 			similarity := alm.calculateSimilarity(target, cleanWord)
// 			if similarity > bestSimilarity {
// 				bestSimilarity = similarity
// 				bestWord = word
// 				bestIndex = i
// 			}
// 		}
// 	}

// 	return bestWord, bestIndex, bestSimilarity
// }

// // calculateSimilarity calculates the similarity between two strings
// // Currently unused but kept for potential future fuzzy matching features
// func (alm *AlphabeticLanguageMatcher) calculateSimilarity(s1, s2 string) float64 {
// 	if s1 == s2 {
// 		return 1.0
// 	}
// 	if strings.Contains(s2, s1) || strings.Contains(s1, s2) {
// 		return 0.8
// 	}
// 	// Simple edit distance based similarity
// 	maxLen := len(s1)
// 	if len(s2) > maxLen {
// 		maxLen = len(s2)
// 	}
// 	return 1.0 - float64(levenshteinDistance(s1, s2))/float64(maxLen)
// }

// BaseLanguageMatcher handles timestamp matching for Base
// CJKSentenceMatcher implements TimestampMatcher for Chinese, Japanese, and Korean
type CJKSentenceMatcher struct {
	language types.StandardLanguageCode
}

func (c *CJKSentenceMatcher) GetLanguageType() types.StandardLanguageCode {
	return c.language
}

func (c *CJKSentenceMatcher) MatchSentenceTimestamp(sentence string, words []types.Word, lastTs float64) (startTime, endTime float64, err error) {
	// Call getSentenceTimestamps from audio2subtitle.go for CJK word-level matching
	sentenceTs, _, _, err := getSentenceTimestamps(words, sentence, lastTs, c.language)
	if err != nil {
		return 0, 0, err
	}
	return sentenceTs.Start, sentenceTs.End, nil
}

type BaseLanguageMatcher struct {
	language types.StandardLanguageCode
}

func (jlm *BaseLanguageMatcher) GetLanguageType() types.StandardLanguageCode {
	return jlm.language
}

func shouldUseProportionalCJKTimestamps(language types.StandardLanguageCode, words []types.Word) bool {
	if language != types.LanguageNameSimplifiedChinese && language != types.LanguageNameTraditionalChinese && language != types.LanguageNameJapanese && language != types.LanguageNameKorean {
		return false
	}
	if len(words) == 0 {
		return false
	}
	bad := 0
	for _, word := range words {
		if strings.ContainsRune(word.Text, '\ufffd') {
			bad++
		}
	}
	if float64(bad)/float64(len(words)) > 0.01 {
		return true
	}
	return true
}

func generateProportionalTimestamps(srtBlocks []*util.SrtBlock, words []types.Word, tsOffset float64) []*util.SrtBlock {
	updatedBlocks := make([]*util.SrtBlock, len(srtBlocks))
	if len(srtBlocks) == 0 || len(words) == 0 {
		return updatedBlocks
	}

	startTime := words[0].Start
	endTime := words[len(words)-1].End
	if endTime <= startTime {
		endTime = startTime + float64(len(srtBlocks))
	}

	totalWeight := 0.0
	weights := make([]float64, len(srtBlocks))
	for i, block := range srtBlocks {
		weight := float64(len([]rune(block.OriginLanguageSentence)))
		if weight < 1 {
			weight = 1
		}
		weights[i] = weight
		totalWeight += weight
	}
	if totalWeight <= 0 {
		totalWeight = float64(len(srtBlocks))
	}

	span := endTime - startTime
	cursor := startTime
	for i, block := range srtBlocks {
		blockCopy := *block
		duration := span * weights[i] / totalWeight
		if duration < 0.35 {
			duration = 0.35
		}
		next := cursor + duration
		if i == len(srtBlocks)-1 || next > endTime {
			next = endTime
		}
		if next <= cursor {
			next = cursor + 0.35
		}
		blockCopy.Timestamp = util.ConvertTimes(float32(cursor+tsOffset), float32(next+tsOffset))
		updatedBlocks[i] = &blockCopy
		cursor = next
	}

	return updatedBlocks
}

func (jlm *BaseLanguageMatcher) MatchSentenceTimestamp(sentence string, words []types.Word, lastTs float64) (startTime, endTime float64, err error) {
	if sentence == "" || len(words) == 0 {
		return 0, 0, fmt.Errorf("empty sentence or words")
	}

	// 使用新的字符串匹配方法
	return jlm.matchSentenceByStringAlignment(sentence, words, lastTs)
}

// matchSentenceByStringAlignment 使用字符串对齐的方法匹配句子时间戳
func (jlm *BaseLanguageMatcher) matchSentenceByStringAlignment(sentence string, words []types.Word, lastTs float64) (startTime, endTime float64, err error) {
	// 步骤1: 合并 Whisper 的所有词文本
	whisperFullText := jlm.buildWhisperFullText(words)
	if whisperFullText == "" {
		return 0, 0, fmt.Errorf("no valid text from whisper words")
	}

	// 步骤2: 清理句子，移除多余的空格和标点符号
	cleanSentence := jlm.cleanBaseText(sentence)
	cleanWhisperText := jlm.cleanBaseText(whisperFullText)

	if cleanSentence == "" {
		return 0, 0, fmt.Errorf("empty sentence after cleaning")
	}

	// 步骤3: 在完整文本中查找句子的所有可能位置
	allMatches := jlm.findAllMatches(cleanSentence, cleanWhisperText)
	if len(allMatches) == 0 {
		// 如果直接匹配失败，尝试模糊匹配
		return jlm.fuzzyMatchSentence(cleanSentence, words, lastTs)
	}

	// 步骤4: 对每个可能的匹配位置，尝试计算时间戳
	var bestStartTime, bestEndTime float64
	var bestErr error
	found := false

	for _, startCharIndex := range allMatches {
		endCharIndex := startCharIndex + len([]rune(cleanSentence))

		startTime, endTime, err := jlm.calculateTimestampsByCharIndex(startCharIndex, endCharIndex, words, lastTs)
		if err == nil && startTime >= lastTs {
			// 找到一个有效的匹配，使用它
			bestStartTime = startTime
			bestEndTime = endTime
			found = true
			break
		} else if err == nil {
			// 记录这个匹配，但继续寻找更好的
			if !found || startTime > bestStartTime {
				bestStartTime = startTime
				bestEndTime = endTime
				bestErr = nil
				found = true
			}
		} else {
			// 记录错误，以防没有找到有效匹配
			if bestErr == nil {
				bestErr = err
			}
		}
	}

	if found {
		return bestStartTime, bestEndTime, bestErr
	}

	// 如果所有匹配都失败，回退到模糊匹配
	// return jlm.fuzzyMatchSentence(cleanSentence, words, lastTs)
	return 0, 0, fmt.Errorf("no valid timestamps found for sentence: %s, error: %v", cleanSentence, bestErr)
}

// buildWhisperFullText 合并所有 Whisper 词的文本
func (jlm *BaseLanguageMatcher) buildWhisperFullText(words []types.Word) string {
	var fullText strings.Builder
	for _, word := range words {
		if word.Text != "" {
			fullText.WriteString(word.Text)
		}
	}
	return fullText.String()
}

// cleanBaseText 清理文本，使用与 getSentenceTimestamps 相同的 util.GetRecognizableString 规则
func (jlm *BaseLanguageMatcher) cleanBaseText(text string) string {
	return util.GetRecognizableString(text)
}

// findAllMatches 找到所有匹配位置
func (jlm *BaseLanguageMatcher) findAllMatches(sentence, fullText string) []int {
	var matches []int
	sentenceRunes := []rune(sentence)
	fullTextRunes := []rune(fullText)

	if len(sentenceRunes) == 0 || len(fullTextRunes) == 0 {
		return matches
	}

	for i := 0; i <= len(fullTextRunes)-len(sentenceRunes); i++ {
		if jlm.matchesAt(fullTextRunes, sentenceRunes, i) {
			matches = append(matches, i)
		}
	}

	return matches
}

// matchesAt 检查在指定位置是否匹配
func (jlm *BaseLanguageMatcher) matchesAt(fullText, sentence []rune, pos int) bool {
	if pos+len(sentence) > len(fullText) {
		return false
	}

	for i, r := range sentence {
		if fullText[pos+i] != r {
			return false
		}
	}
	return true
}

// calculateTimestampsByCharIndex 根据字符索引计算时间戳
func (jlm *BaseLanguageMatcher) calculateTimestampsByCharIndex(startCharIndex, endCharIndex int, words []types.Word, lastTs float64) (startTime, endTime float64, err error) {
	var resultStartTime, resultEndTime float64
	var startWordFound, endWordFound bool
	currentCharIndex := 0

	for _, word := range words {
		if word.Text == "" {
			continue
		}

		// 计算当前词的清理后文本长度
		cleanWordText := jlm.cleanBaseText(word.Text)
		wordCharLength := len([]rune(cleanWordText))

		wordStartIndex := currentCharIndex
		wordEndIndex := currentCharIndex + wordCharLength

		// 检查是否找到开始时间戳
		if !startWordFound && wordEndIndex > startCharIndex {
			if word.Start >= lastTs {
				resultStartTime = word.Start
				startWordFound = true
			}
		}

		// 检查是否找到结束时间戳
		if wordStartIndex < endCharIndex {
			if word.End >= lastTs {
				resultEndTime = word.End
				endWordFound = true
			}
		}

		// 如果已经超过了结束索引，停止搜索
		if wordStartIndex >= endCharIndex {
			break
		}

		currentCharIndex = wordEndIndex
	}

	if !startWordFound || !endWordFound || resultStartTime < lastTs || resultStartTime >= resultEndTime {
		return 0, 0, fmt.Errorf("could not find valid timestamps for character range [%d, %d)", startCharIndex, endCharIndex)
	}

	return resultStartTime, resultEndTime, nil
}

// fuzzyMatchSentence 当直接匹配失败时的模糊匹配方法
func (jlm *BaseLanguageMatcher) fuzzyMatchSentence(sentence string, words []types.Word, lastTs float64) (startTime, endTime float64, err error) {
	// 将句子拆分成字符，寻找包含这些字符的词
	sentenceRunes := []rune(sentence)
	var matchedWords []types.Word

	for _, word := range words {
		if word.Start < lastTs {
			continue
		}

		// 检查词是否包含句子中的字符
		wordRunes := []rune(jlm.cleanBaseText(word.Text))
		if jlm.sentenceCharOverlap(wordRunes, sentenceRunes) >= 0.3 {
			matchedWords = append(matchedWords, word)
		}
	}

	if len(matchedWords) == 0 {
		// 如果在 lastTs 之后没找到，从头开始搜索
		for _, word := range words {
			wordRunes := []rune(jlm.cleanBaseText(word.Text))
			if jlm.sentenceCharOverlap(wordRunes, sentenceRunes) >= 0.3 {
				matchedWords = append(matchedWords, word)
			}
		}
	}

	if len(matchedWords) == 0 {
		return 0, 0, fmt.Errorf("no matching words found for fuzzy matching")
	}

	// 使用第一个和最后一个匹配的词来确定时间范围
	resultStartTime := matchedWords[0].Start

	// If the fuzzy match spans too long, it's likely matching common repeated words across the audio.
	// Only keep matched words that fall within a reasonable window (e.g. 5s) from the start of the first match.
	const maxFuzzyDuration = 5.0
	var filteredMatched []types.Word
	for _, w := range matchedWords {
		if w.Start >= resultStartTime && w.End <= resultStartTime+maxFuzzyDuration {
			filteredMatched = append(filteredMatched, w)
		}
	}

	var resultEndTime float64
	if len(filteredMatched) > 0 {
		resultEndTime = filteredMatched[len(filteredMatched)-1].End
	} else {
		resultEndTime = matchedWords[0].End
	}

	// 应用 lastTs 约束
	if resultStartTime < lastTs {
		resultStartTime = lastTs
	}

	return resultStartTime, resultEndTime, nil
}

// sentenceCharOverlap returns the fraction of word characters found in the sentence.
func (jlm *BaseLanguageMatcher) sentenceCharOverlap(wordRunes, sentenceRunes []rune) float64 {
	if len(wordRunes) == 0 {
		return 0
	}
	found := 0
	for _, wc := range wordRunes {
		for _, sc := range sentenceRunes {
			if sc == wc {
				found++
				break
			}
		}
	}
	return float64(found) / float64(len(wordRunes))
}
