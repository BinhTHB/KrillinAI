package types

import subtitlestyle "krillin-ai/internal/subtitle_style"

// var SplitTextPrompt = `你是一个英语处理专家，擅长翻译成%s和处理英文文本，根据句意和标点对句子进行拆分。

// - 不要漏掉原英文任何一个单词
// - 翻译一定要流畅，完整表达原文意思
// - 优先根据标点符号进行拆分，遇到逗号、句号、问号，一定要拆分，必须把句子拆短些。
// - 遇到定语从句、并列句等复杂句式，根据连词（如and, but, which, when）进行拆分。
// - 拆分后的单行句子英文不能超过15个单词。
// - 翻译的时候确保每个原始字幕块单独存在且编号和格式正确。
// - 不需要任何额外的话语，直接按下面格式输出结果。

// 1
// [中文翻译]
// [英文句子]

// 2
// [中文翻译]
// [英文句子]

// 内容如下:`

var SplitTextPrompt = `You are a language processing expert specializing in natural language processing and translation tasks. Follow these steps and requirements to achieve the most accurate and high-quality subtitle translation:

1. Translate the source sentence into %s, ensuring the translation is fluent, natural, and meets professional translation standards while preserving the original meaning. **If the target language is Chinese, you MUST use Simplified Chinese characters, NOT Traditional Chinese.**
2. Strictly split content into individual sentences based on punctuation marks (comma: ，,、 period: 。.、 question mark: ？? etc.), and ensure short split lengths according to these rules:
   - Each sentence should be as short as possible while maintaining complete meaning; moderate subtitle length provides a comfortable viewing experience.
   - Further split sentences based on conjunctions (e.g., "and", "but", "which", "when", "so", "but", "therefore", "considering" etc.) to get shorter results.
3. Translate each split sentence separately, ensuring no words are omitted or modified.
4. Represent each translated sentence pair with the original sentence using independent numbering, and wrap each in square brackets [].
5. The output translation must correspond to the original text, strictly presented in the original order without misalignment, maintaining the same meaning as the original, and the original text should be used as much as possible.
6. Translate all content regardless of whether it is formal or informal.

Translation output should follow this format:
**Normal translation example (each block has 3 parts, each part on its own line, separated by spaces)**:
1
[Translated sentence 1]
[Original sentence 1]

2
[Translated sentence 2]
[Original sentence 2]

**Example output when no text needs translation**:
[No text]

Complete the above translation task efficiently and accurately. Input content below:`

// 带有语气词过滤的拆分Prompt
var SplitTextPromptWithModalFilter = `You are a language processing expert specializing in natural language processing and translation tasks. Follow these steps and requirements to achieve the most accurate and high-quality subtitle translation:

1. Translate the source sentence into %s, ensuring the translation is fluent, natural, and meets professional translation standards while preserving the original meaning. **If the target language is Chinese, you MUST use Simplified Chinese characters, NOT Traditional Chinese.**
2. Strictly split content into individual sentences based on punctuation marks (comma: ，,、 period: 。.、 question mark: ？? etc.), and ensure short split lengths according to these rules:
   - Each sentence should be as short as possible while maintaining complete meaning; moderate subtitle length provides a comfortable viewing experience.
   - Further split sentences based on conjunctions (e.g., "and", "but", "which", "when", "so", "but", "therefore", "considering" etc.) to get shorter results.
3. Translate each split sentence separately, ensuring no words are omitted or modified.
4. Represent each translated sentence pair with the original sentence using independent numbering, and wrap each in square brackets [].
5. The output translation must correspond to the original text, strictly presented in the original order without misalignment, maintaining the same meaning as the original, and the original text should be used as much as possible.
6. Ignore modal/filler words in the text, such as "Oh", "Ah", "Wow", etc.
7. Translate all content regardless of whether it is formal or informal.

Translation output should follow this format:
**Normal translation example (each block has 3 parts, each part on its own line, separated by spaces)**:
1
[Translated sentence 1]
[Original sentence 1]

2
[Translated sentence 2]
[Original sentence 2]

**Example output when no text needs translation**:
[No text]

Complete the above translation task efficiently and accurately. Input content below:`

var SplitTextPromptJson = `You are a language processing expert specializing in natural language processing and translation tasks. Follow these steps and requirements to achieve the most accurate and high-quality subtitle translation:

1. Translate the source sentence into %s, ensuring the translation is fluent, natural, and meets professional translation standards while preserving the original meaning.
2. Strictly split content into individual sentences based on punctuation marks (comma: ，,、 period: 。.、 question mark: ？? etc.), and ensure short split lengths according to these rules:
   - Each sentence should be as short as possible while maintaining complete meaning; moderate subtitle length provides a comfortable viewing experience.
   - Further split sentences based on conjunctions (e.g., "and", "but", "which", "when", "so", "but", "therefore", "considering" etc.) to get shorter results.
3. Translate each split sentence separately, ensuring no words are omitted or modified.
4. Ensure the output translation corresponds to the original text, strictly presented in the original order.
5. The output format MUST be a JSON array, where each element contains 'original_sentence' and 'translated_sentence' fields.
6. The original sentence in the result must exactly match the original text, including case sensitivity of the first letter, and punctuation marks must also be retained without modification. For English source text, use English punctuation, and do not correct any grammar or spelling mistakes.
7. Each split sentence can only have one complete statement.

Ensure efficient and precise completion of the subtitle translation task. Input content below:`

var SplitTextPromptWithModalFilterJson = `You are a language processing expert specializing in natural language processing and translation tasks. Follow these steps and requirements to achieve the most accurate and high-quality subtitle translation:

1. Translate the source sentence into %s, ensuring the translation is fluent, natural, and meets professional translation standards while preserving the original meaning.
2. Strictly split content into individual sentences based on punctuation marks (comma: ，,、 period: 。.、 question mark: ？? etc.), and ensure short split lengths according to these rules:
   - Each sentence should be as short as possible while maintaining complete meaning; moderate subtitle length provides a comfortable viewing experience.
   - Further split sentences based on conjunctions (e.g., "and", "but", "which", "when", "so", "but", "therefore", "considering" etc.) to get shorter results.
3. Ignore modal/filler words in the text, such as "Oh", "Ah", "Wow", etc.
4. Translate each split sentence separately, ensuring no words are omitted or modified.
5. Ensure the output translation corresponds to the original text, strictly presented in the original order.
6. The output format MUST be a JSON array, where each element contains 'original_sentence' and 'translated_sentence' fields.
7. The original sentence in the result must exactly match the original text, including case sensitivity of the first letter, and punctuation marks must also be retained without modification. For English source text, use English punctuation, and do not correct any grammar or spelling mistakes.
8. Each split sentence can only have one complete statement.

Ensure efficient and precise completion of the subtitle translation task. Input content below:`

var TranslateVideoTitleAndDescriptionPrompt = `You are a professional translation expert, please translate the given title and description below (separated by ####), with requirements:
  - Translate content into %s
  - The translated content must still be separated by #### to divide the title and description
  The following is the source content, please translate completely as required:
 %s`
var SplitLongSentencePrompt = `Please split the following original and translated text into multiple parts, ensuring each part is as short as possible:
Original: %s
Translation: %s

Requirements:
1. The split original parts must not deviate from the source original text
2. Each split translated sentence must conform to grammatical standards, allowing addition of conjunctions, removal of particles, etc., to ensure natural flow when spoken.
3. If there are omissions in the translation, please fill them in during splitting.
4. You MUST return JSON format containing origin_part and translated_part arrays, for example:
{"align":[{"origin_part":"original part 1","translated_part":"translated part 1"},{"origin_part":"original part 2","translated_part":"translated part 2"}]}`

var SplitOriginLongSentencePrompt = `Please split the following text into multiple parts, ensuring it's divided into at most 3 short sentences, preferably 2 parts,

Original text: %s

CRITICAL Requirements:
1. The split sentences must exactly match the original text, absolutely no changes to the original text are allowed
2. Split based on sentence meaning, dividing into at most 3 parts, preferably 2 parts
3. **Each split part MUST contain at least 3-5 words. NEVER create single-word or two-word fragments**
4. Split at natural break points (conjunctions, clauses) - DO NOT split phrases like "we're marking out", "you're going to", etc.
5. Try to make the split as balanced as possible while maintaining sentence integrity
6. Return in JSON format only, no other descriptions or explanations
7. Example format:
{"short_sentences":[{"text": "split sentence 1 with at least 3 words"},{"text": "split sentence 2 with at least 3 words"}]}

`

var SplitLongTextByMeaningPrompt = `Please split the following long text into shorter sentences based on semantic meaning. Do not change, add, or remove any words from the original text.

Original text: %s

Requirements:
1. Split the text into as many shorter, meaningful sentences as possible while preserving ALL original words
2. Do NOT change, modify, add, or remove any words - only split at natural breakpoints
3. Split at natural linguistic boundaries such as:
   - Punctuation marks (commas, semicolons, periods)
   - Conjunctions (and, but, or, so, because, when, while, etc.)
   - Relative pronouns (which, that, who, where, etc.)
   - Natural pause points that maintain sentence meaning
4. Each split part should be a complete, meaningful unit that can stand alone
5. Prioritize shorter segments - split as much as possible while maintaining semantic integrity
6. No limit on the number of splits - make each part as short as possible while still being meaningful
7. Maintain the original word order and exact spelling
8. Preserve all original punctuation and capitalization
9. Return in JSON format only, no other descriptions or explanations
10. Example format:
{"short_sentences":[{"text": "first short part"},{"text": "second short part"},{"text": "third short part"}]}

`

// var SplitTextWithContextPrompt = `你是一个专业翻译专家，擅长结合上下文进行准确翻译。请根据以下提供的上下文句子和目标句子，将目标句子翻译成%s，并确保翻译结果与上下文保持连贯一致：

// 上下文句子：
// %s

// 需要翻译的目标句子：%s

// 翻译要求：
// 1. 严格按照目标语言的语法和表达习惯翻译
// 2. 保持专业术语的一致性
// 3. 输出仅包含翻译后的文本，不添加任何额外解释或格式
// 4. 确保翻译结果与上下文语义连贯

// 请直接输出翻译结果：`

// var SplitTextWithContextPrompt = `You are a professional translation expert skilled in providing accurate translations based on context. Please translate the target sentence into %s according to the provided context sentences below, ensuring the translation remains coherent and consistent.

// Here's the full context:
// %s

// Target sentence to translate:
// %s

// %s

// Translation requirements:
// 1.Analyze how the target sentence connects to both the preceding and following context
// 2.Provide the most natural translation that preserves the original tone and intent
// 3.Highlight any idioms, cultural references, or nuanced phrases that require special attention
// 4.If there are multiple possible interpretations, briefly explain each option
// 5.Maintain consistent terminology with the surrounding sentences"
// 6.Output only the translated text without any additional explanations or formatting

// Please provide only the translation result:`

var SplitTextWithContextPrompt = `You are a professional subtitle translation expert specialized in voiceover/dubbing production.

[TRANSLATION TASK]
**Objective**: 
Translate the "Target Sentence" below into %s with natural, fluent expression optimized for text-to-speech (TTS) voiceover.
Use "Previous Sentences" to understand context and maintain coherence.
The translation will be read aloud by a speech synthesizer within the available subtitle duration — it MUST be concise enough to fit.

**Critical Rules**:
1. OUTPUT MUST BE A SINGLE LINE: only the translated text
2. If translating to Chinese, MUST use Simplified Chinese characters (简体中文), NOT Traditional Chinese (繁体中文)
3. Translate naturally and idiomatically - avoid word-for-word literal translation
4. Remove stuttering/repeated words (e.g., "I I I'm" → translate as "I'm")
5. Filter out filler words (um, uh, er, ah, oh, mm, hmm, etc.) - do NOT translate them
6. Use proper punctuation marks in the target language (for Chinese: use ，。！？ not spaces)
7. Keep the original meaning but express it smoothly and naturally in the target language
8. If sentence is incomplete/fragmentary, keep it that way but translate fluently
9. IGNORE the "Next Sentences" - they are for reference only
10. **Wuxia/Martial Arts Style (Võ Hiệp)**: Use traditional wuxia style pronouns and addressing terms in Vietnamese (e.g., "huynh", "đệ", "muội", "tại hạ", "các vị", "các hạ", "tiền bối", "vãn bối", "tiểu tử", "lão phu"). If the relationship between characters is unknown or ambiguous, default to "ta" (I/me) and "ngươi" (you). STRICTLY AVOID modern, intimate, or colloquial pronouns like "bạn", "tớ", "cậu", "mày", "tao" unless historically appropriate for the character relationship.

**[VOICEOVER TIMING — CRITICAL]**
The translated text will be read by a TTS engine in a fixed time window equal to the original speech duration.
- AVAILABLE DURATION: %.1f seconds. The translation MUST be readable at a natural pace within this duration.
- LENGTH TARGET: Max %d syllables/characters. Keep it concise so it doesn't overrun.
- Avoid unnecessarily long or wordy translations — prefer shorter, natural alternatives
- Do NOT add explanatory words or repetitions — every word must carry meaning
- If the original sentence is short (~1-2s of speech), keep the translation equally brief
- For complex/compound sentences, prioritize the core message and trim non-essential modifiers
- Write for SPEECH, not for reading — use natural, flowing spoken language structure

**Context**:
[Previous Sentences]
%s

[Target Sentence]
%s

[Next Sentences]
%s

**Provide only the natural, fluent translation on a single line:**`

type SmallAudio struct {
	AudioFile         string
	TranscriptionData *TranscriptionData
	SrtNoTsFile       string
}

type SubtitleResultType int

const (
	SubtitleResultTypeOriginOnly                   SubtitleResultType = iota + 1 // 仅返回原语言字幕
	SubtitleResultTypeTargetOnly                                                 // 仅返回翻译后语言字幕
	SubtitleResultTypeBilingualTranslationOnTop                                  // 返回双语字幕，翻译后的字幕在上
	SubtitleResultTypeBilingualTranslationOnBottom                               // 返回双语字幕，翻译后的字幕在下
)

const (
	SubtitleTaskBilingualYes uint8 = iota + 1
	SubtitleTaskBilingualNo
)

const (
	SubtitleTaskTranslationSubtitlePosTop uint8 = iota + 1
	SubtitleTaskTranslationSubtitlePosBelow
)

const (
	SubtitleTaskModalFilterYes uint8 = iota + 1
	SubtitleTaskModalFilterNo
)

const (
	SubtitleTaskTtsYes uint8 = iota + 1
	SubtitleTaskTtsNo
)

const (
	SubtitleTaskTtsVoiceCodeLongyu uint8 = iota + 1
	SubtitleTaskTtsVoiceCodeLongchen
)

const (
	SubtitleTaskStatusProcessing uint8 = iota + 1
	SubtitleTaskStatusSuccess
	SubtitleTaskStatusFailed
)

const (
	SubtitleTaskAudioFileName                                    = "origin_audio.mp3"
	SubtitleTaskVideoFileName                                    = "origin_video.mp4"
	SubtitleTaskSplitAudioFileNamePrefix                         = "split_audio"
	SubtitleTaskSplitAudioFileNamePattern                        = SubtitleTaskSplitAudioFileNamePrefix + "_%03d.wav"
	SubtitleTaskSplitAudioTxtFileNamePattern                     = "split_audio_txt_%d.txt"
	SubtitleTaskSplitAudioWordsFileNamePattern                   = "split_audio_words_%d.txt"
	SubtitleTaskSplitSrtNoTimestampFileNamePattern               = "srt_no_ts_%d.srt"
	SubtitleTaskSrtNoTimestampFileName                           = "srt_no_ts.srt"
	SubtitleTaskSplitBilingualSrtFileNamePattern                 = "split_bilingual_srt_%d.srt"
	SubtitleTaskSplitShortOriginMixedSrtFileNamePattern          = "split_short_origin_mixed_srt_%d.srt" //长中文+短英文
	SubtitleTaskSplitShortOriginSrtFileNamePattern               = "split_short_origin_srt_%d.srt"       //短英文
	SubtitleTaskBilingualSrtFileName                             = "bilingual_srt.srt"
	SubtitleTaskShortOriginMixedSrtFileName                      = "short_origin_mixed_srt.srt" //长中文+短英文
	SubtitleTaskShortOriginSrtFileName                           = "short_origin_srt.srt"       //短英文
	SubtitleTaskOriginLanguageSrtFileName                        = "origin_language_srt.srt"
	SubtitleTaskOriginLanguageTextFileName                       = "origin_language.txt"
	SubtitleTaskTargetLanguageSrtFileName                        = "target_language_srt.srt"
	SubtitleTaskTargetLanguageTextFileName                       = "target_language.txt"
	SubtitleTaskStepParamGobPersistenceFileName                  = "step_param.gob"
	SubtitleTaskAudioTranscriptionDataPersistenceFileNamePattern = "audio_transcription_data_%d.json"
	SubtitleTaskTranslationRawDataPersistenceFileNamePattern     = "audio_translation_raw_data_%d.json"
	SubtitleTaskTranslationDataPersistenceFileNamePattern        = "translation_data_%d.json"
	SubtitleTaskTransferredVerticalVideoFileName                 = "transferred_vertical_video.mp4"
	SubtitleTaskHorizontalEmbedVideoFileName                     = "horizontal_embed.mp4"
	SubtitleTaskVerticalEmbedVideoFileName                       = "vertical_embed.mp4"
	SubtitleTaskVideoWithTtsFileName                             = "video_with_tts.mp4"
)

const (
	TtsAudioDurationDetailsFileName = "audio_duration_details.txt"
	TtsResultAudioFileName          = "tts_final_audio.wav"
)

const (
	AsrMono16kAudioFileName = "mono_16k_audio.wav"
)

type SubtitleFileInfo struct {
	Name               string
	Path               string
	LanguageIdentifier string // 在最终下载的文件里标识语言，如zh_cn，en，bilingual
}

type SubtitleTaskStepParam struct {
	TaskId                      string
	TaskPtr                     *SubtitleTask // 和storage里面对应
	TaskBasePath                string
	Link                        string
	AudioFilePath               string
	VttFile                     string // YouTube下载的原始字幕文件路径
	SubtitleResultType          SubtitleResultType
	EnableModalFilter           bool
	EnableTts                   bool
	TtsVoiceCode                string // 人声语音编码
	VoiceCloneAudioUrl          string // 音色克隆的源音频oss地址
	ReplaceWordsMap             map[string]string
	OriginLanguage              StandardLanguageCode // 视频源语言
	TargetLanguage              StandardLanguageCode // 用户希望的目标翻译语言
	UserUILanguage              StandardLanguageCode // 用户的使用语言
	BilingualSrtFilePath        string
	ShortOriginMixedSrtFilePath string
	SubtitleInfos               []SubtitleFileInfo
	TtsSourceFilePath           string
	TtsResultFilePath           string
	InputVideoPath              string // 源视频路径
	EmbedSubtitleVideoType      string // 合成字幕嵌入的视频类型 none不嵌入 horizontal横屏 vertical竖屏
	VerticalVideoMajorTitle     string // 合成竖屏视频的主标题
	VerticalVideoMinorTitle     string
	MaxWordOneLine              int                     // 字幕一行最多显示多少个字
	VideoWithTtsFilePath        string                  // 替换源视频的音频为tts结果后的视频路径
	VttSwitch                   bool                    // 是否使用VTT格式字幕文件
	SubtitleStyle               *subtitlestyle.StyleSet // CLI/Agent 传入的字幕样式；nil 时使用默认样式
	RenderWidth                 int                     // 当前待烧录字幕视频宽度，用于按字号估算自动换行
	RenderHeight                int                     // 当前待烧录字幕视频高度，用于按字号估算自动换行
}

type SrtSentence struct {
	Text  string
	Start float64
	End   float64
}

type SrtSentenceWithStrTime struct {
	Text  string
	Start string
	End   string
}

type SubtitleInfo struct {
	Id          uint64 `json:"id" gorm:"column:id"`                                  // 自增id
	TaskId      string `json:"task_id" gorm:"column:task_id"`                        // task_id
	Uid         uint32 `json:"uid" gorm:"column:uid"`                                // 用户id
	Name        string `json:"name" gorm:"column:name"`                              // 字幕名称
	DownloadUrl string `json:"download_url" gorm:"column:download_url"`              // 字幕地址
	CreateTime  int64  `json:"create_time" gorm:"column:create_time;autoCreateTime"` // 创建时间
}

type SubtitleTask struct {
	Id                    uint64         `json:"id" gorm:"column:id"`                                         // 自增id
	TaskId                string         `json:"task_id" gorm:"column:task_id"`                               // 任务id
	Title                 string         `json:"title" gorm:"column:title"`                                   // 标题
	Description           string         `json:"description" gorm:"column:description"`                       // 描述
	TranslatedTitle       string         `json:"translated_title" gorm:"column:translated_title"`             // 翻译后的标题
	TranslatedDescription string         `json:"translated_description" gorm:"column:translated_description"` // 翻译后的描述
	OriginLanguage        string         `json:"origin_language" gorm:"column:origin_language"`               // 视频原语言
	TargetLanguage        string         `json:"target_language" gorm:"column:target_language"`               // 翻译任务的目标语言
	VideoSrc              string         `json:"video_src" gorm:"column:video_src"`                           // 视频地址
	Status                uint8          `json:"status" gorm:"column:status"`                                 // 1-处理中,2-成功,3-失败
	LastSuccessStepNum    uint8          `json:"last_success_step_num" gorm:"column:last_success_step_num"`   // 最后成功的子任务序号，用于任务恢复
	FailReason            string         `json:"fail_reason" gorm:"column:fail_reason"`                       // 失败原因
	ProcessPct            uint8          `json:"process_percent" gorm:"column:process_percent"`               // 处理进度
	Duration              uint32         `json:"duration" gorm:"column:duration"`                             // 视频时长
	SrtNum                int            `json:"srt_num" gorm:"column:srt_num"`                               // 字幕数量
	SubtitleInfos         []SubtitleInfo `gorm:"foreignKey:TaskId;references:TaskId"`
	Cover                 string         `json:"cover" gorm:"column:cover"`                             // 封面
	SpeechDownloadUrl     string         `json:"speech_download_url" gorm:"column:speech_download_url"` // 语音文件下载地址
	CreateTime            int64          `json:"create_time" gorm:"column:create_time;autoCreateTime"`  // 创建时间
	UpdateTime            int64          `json:"update_time" gorm:"column:update_time;autoUpdateTime"`  // 更新时间
}

type Word struct {
	Num   int
	Text  string
	Start float64
	End   float64
}

type TranscriptionData struct {
	Language string
	Text     string
	Words    []Word
}

type SrtBlock struct {
	Index                  int
	Timestamp              string
	OriginLanguageSentence string
	TargetLanguageSentence string
}

// TranslationBatchItem represents a single sentence for batch translation
type TranslationBatchItem struct {
	Index        int     `json:"index"`
	Original     string  `json:"original"`
	Duration     float64 `json:"duration"`
	MaxSyllables int     `json:"max_syllables"`
}

// TranslationBatchResult represents the translated output for a single sentence
type TranslationBatchResult struct {
	Index      int    `json:"index"`
	Translated string `json:"translated"`
}

// TranslateBatchPrompt is used for translating all sentences in a single request
var TranslateBatchPrompt = `You are a professional subtitle translation expert specialized in voiceover/dubbing production.

[TRANSLATION TASK]
**Objective**: 
Translate ALL sentences in the input JSON array into %s with natural, fluent expression optimized for text-to-speech (TTS) voiceover.
You have FULL CONTEXT of the entire video - use it to maintain consistency in terminology, tone, and style.

**Critical Rules**:
1. OUTPUT MUST BE A VALID JSON ARRAY with the EXACT same number of items as input
2. Each output item MUST contain: {"index": <same as input>, "translated": "<translation>"}
3. If translating to Chinese, MUST use Simplified Chinese characters (简体中文), NOT Traditional Chinese (繁体中文)
4. Translate naturally and idiomatically - avoid word-for-word literal translation
5. Maintain consistent terminology and style throughout ALL sentences
6. Remove stuttering/repeated words (e.g., "I I I'm" → translate as "I'm")
7. Filter out filler words (um, uh, er, ah, oh, mm, hmm, etc.) - do NOT translate them
8. Use proper punctuation marks in the target language
9. **Wuxia/Martial Arts Style (Võ Hiệp)**: Use traditional wuxia style pronouns and addressing terms in Vietnamese (e.g., "huynh", "đệ", "muội", "tại hạ", "các vị", "các hạ", "tiền bối", "vãn bối", "tiểu tử", "lão phu"). If the relationship between characters is unknown or ambiguous, default to "ta" (I/me) and "ngươi" (you). STRICTLY AVOID modern, intimate, or colloquial pronouns like "bạn", "tớ", "cậu", "mày", "tao" unless historically appropriate for the character relationship.

**[VOICEOVER TIMING — CRITICAL]**
Each sentence has "duration" (seconds) and "max_syllables" constraints for TTS:
- The translation MUST be readable at a natural pace within the given duration
- Keep translations concise - prefer shorter, natural alternatives
- Do NOT add explanatory words or repetitions
- Write for SPEECH, not for reading - use natural, flowing spoken language

**Input Format**:
JSON array of objects: [{"index": 1, "original": "...", "duration": 2.5, "max_syllables": 12}, ...]

**Output Format** (STRICT):
JSON array ONLY, no markdown, no explanation:
[{"index": 1, "translated": "..."}, {"index": 2, "translated": "..."}, ...]

**IMPORTANT**: You MUST translate ALL %d sentences. Do NOT skip, merge, or split any sentence.

Input sentences:
%s`
