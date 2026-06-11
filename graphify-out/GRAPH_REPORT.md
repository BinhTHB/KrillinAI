# Graph Report - .  (2026-06-11)

## Corpus Check
- 222 files · ~248,090 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 767 nodes · 1065 edges · 61 communities (42 shown, 19 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.81)
- Token cost: 76,000 input · 4,000 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Cover Image Generation|Cover Image Generation]]
- [[_COMMUNITY_CLI & Alibaba Cloud Setup|CLI & Alibaba Cloud Setup]]
- [[_COMMUNITY_Image & Brand Assets|Image & Brand Assets]]
- [[_COMMUNITY_Project Documentation & Localization|Project Documentation & Localization]]
- [[_COMMUNITY_Audio-to-Subtitle Pipeline|Audio-to-Subtitle Pipeline]]
- [[_COMMUNITY_Alibaba Cloud SDK Clients|Alibaba Cloud SDK Clients]]
- [[_COMMUNITY_Video & Subtitle Utilities|Video & Subtitle Utilities]]
- [[_COMMUNITY_YouTube Subtitle Testing|YouTube Subtitle Testing]]
- [[_COMMUNITY_Service Adapter Layer|Service Adapter Layer]]
- [[_COMMUNITY_Documentation Concepts|Documentation Concepts]]
- [[_COMMUNITY_Image Assets Collection|Image Assets Collection]]
- [[_COMMUNITY_Dubbing Types & Config|Dubbing Types & Config]]
- [[_COMMUNITY_Duration Estimation|Duration Estimation]]
- [[_COMMUNITY_Service Adapter Interface|Service Adapter Interface]]
- [[_COMMUNITY_Video Rendering Pipeline|Video Rendering Pipeline]]
- [[_COMMUNITY_Audio Assembly & Chunking|Audio Assembly & Chunking]]
- [[_COMMUNITY_Working Directory Management|Working Directory Management]]
- [[_COMMUNITY_OpenAI-Compatible Image Gen|OpenAI-Compatible Image Gen]]
- [[_COMMUNITY_Dubbing Runner Pipeline|Dubbing Runner Pipeline]]
- [[_COMMUNITY_Miscellaneous Code|Miscellaneous Code]]
- [[_COMMUNITY_SRT Extraction Logic|SRT Extraction Logic]]
- [[_COMMUNITY_Miscellaneous Code|Miscellaneous Code]]
- [[_COMMUNITY_Dubbing Text Cleaning|Dubbing Text Cleaning]]
- [[_COMMUNITY_OpenAI Chat & TTS|OpenAI Chat & TTS]]
- [[_COMMUNITY_Miscellaneous Code|Miscellaneous Code]]
- [[_COMMUNITY_Miscellaneous Code|Miscellaneous Code]]
- [[_COMMUNITY_SRT Parsing & Cues|SRT Parsing & Cues]]
- [[_COMMUNITY_WhisperCPP Integration|WhisperCPP Integration]]
- [[_COMMUNITY_Miscellaneous Code|Miscellaneous Code]]
- [[_COMMUNITY_Edge TTS Client|Edge TTS Client]]
- [[_COMMUNITY_WhisperKit Integration|WhisperKit Integration]]
- [[_COMMUNITY_Pipeline Planning|Pipeline Planning]]
- [[_COMMUNITY_FasterWhisper Integration|FasterWhisper Integration]]
- [[_COMMUNITY_Whisper Integration|Whisper Integration]]
- [[_COMMUNITY_TTS Segment Generation|TTS Segment Generation]]
- [[_COMMUNITY_Miscellaneous Code|Miscellaneous Code]]
- [[_COMMUNITY_Timeline Fitting|Timeline Fitting]]
- [[_COMMUNITY_LLM Text Optimizer|LLM Text Optimizer]]
- [[_COMMUNITY_Subtitle Style Config|Subtitle Style Config]]
- [[_COMMUNITY_Config Handler|Config Handler]]
- [[_COMMUNITY_HTTP Handler Init|HTTP Handler Init]]
- [[_COMMUNITY_Miscellaneous|Miscellaneous]]
- [[_COMMUNITY_Config API|Config API]]
- [[_COMMUNITY_Static Assets|Static Assets]]
- [[_COMMUNITY_Service Struct|Service Struct]]
- [[_COMMUNITY_Service Constructor|Service Constructor]]
- [[_COMMUNITY_Cover Image Service|Cover Image Service]]
- [[_COMMUNITY_Chinese Text Splitting|Chinese Text Splitting]]
- [[_COMMUNITY_Horizontal Text Split|Horizontal Text Split]]
- [[_COMMUNITY_Space-based Split Check|Space-based Split Check]]
- [[_COMMUNITY_YouTube Subtitle Request|YouTube Subtitle Request]]
- [[_COMMUNITY_Fake TTS|Fake TTS]]
- [[_COMMUNITY_YouTube Subtitle Test|YouTube Subtitle Test]]
- [[_COMMUNITY_VTT Word Extraction Test|VTT Word Extraction Test]]
- [[_COMMUNITY_YouTube Subtitle Process Test|YouTube Subtitle Process Test]]
- [[_COMMUNITY_FAQ SRT-Only Dubbing|FAQ: SRT-Only Dubbing]]
- [[_COMMUNITY_FAQ Progress Bar Issues|FAQ: Progress Bar Issues]]
- [[_COMMUNITY_FAQ API Key Setup|FAQ: API Key Setup]]
- [[_COMMUNITY_Miscellaneous Node|Miscellaneous Node]]

## God Nodes (most connected - your core abstractions)
1. `KrillinAI` - 17 edges
2. `GenerateSubtitles()` - 16 edges
3. `Render()` - 14 edges
4. `KrillinAI CLI` - 14 edges
5. `GenerateCover()` - 9 edges
6. `NewManifest()` - 9 edges
7. `ServiceAdapter` - 9 edges
8. `fakeStageService` - 9 edges
9. `GenerateTTS()` - 9 edges
10. `YouTubeSubtitleService` - 8 edges

## Surprising Connections (you probably didn't know these)
- `KrillinAI` --references--> `KrillinAI Web UI`  [EXTRACTED]
  docs/zh/README.md → static/index.html
- `KrillinAI` --conceptually_related_to--> `krillinai-cover Skill`  [INFERRED]
  docs/zh/README.md → skills/krillinai-cover/SKILL.md
- `KrillinAI` --conceptually_related_to--> `krillinai-pipeline Skill`  [INFERRED]
  docs/zh/README.md → skills/krillinai-pipeline/SKILL.md
- `KrillinAI` --conceptually_related_to--> `KrillinAI CLI Contract`  [INFERRED]
  docs/zh/README.md → skills/krillinai-cli/references/cli-contract.md
- `KrillinAI CLI` --references--> `krillinai_manifest.json`  [EXTRACTED]
  docs/zh/cli.md → skills/krillinai-cli/references/cli-contract.md

## Hyperedges (group relationships)
- **Audio to Subtitle Pipeline** — service_audioToSubtitle, service_audioToSrt, service_getSplitPointsForAudio, service_processAudioSegments, service_startSplitWorkers, service_startTranscribeWorkers, service_startTranslateWorker, service_startResultHandler, service_mergeSubtitleFiles, service_splitSrt [EXTRACTED 1.00]
- **Subtitle Task Workflow** — service_StartSubtitleTask, service_linkToFile, service_audioToSubtitle, service_srtFileToSpeech, service_embedSubtitles, service_uploadSubtitles [EXTRACTED 1.00]
- **YouTube Subtitle Processing** — youtube_subtitle_YouTubeSubtitleService, translate_Translator, timestamps_TimestampGenerator, timestamps_BaseLanguageMatcher, youtube_subtitle_VttWord, youtube_subtitle_Sentence, youtube_subtitle_YoutubeSubtitleReq [EXTRACTED 1.00]
- **Dubbing main pipeline flow** — func:Runner.Run, func:Planner.Plan, func:FitTimeline, func:GenerateRawChunkSegments, func:AssembleChunkAudio, func:BuildDubCues [INFERRED]
- **Duration estimation hierarchy** — interface:DurationEstimator, type:StatisticalEstimator, type:HeuristicEstimator [INFERRED]
- **Text optimization with LLM** — interface:TextOptimizer, type:LLMOptimizer, func:LLMOptimizer.Optimize [INFERRED]
- **SRT file parsing and writing** — func:ParseSRTFile, func:WriteSRTFile, func:ParseTimestamp, func:FormatTimestamp, type:Cue [INFERRED]
- **Audio assembly with atempo filtering** — func:AssembleAudio, func:AssembleChunkAudio, func:buildAtempoFilter, func:WriteTinySilence [INFERRED]
- **Text cleaning for speech synthesis** — func:CleanTextForSpeech, func:IsSilenceOnlyText, var:parenNoisePattern, var:spacePattern [INFERRED]
- **Timeline fitting and speed configuration** — func:FitTimeline, func:normalizeSpeedConfig, func:chunkActualDuration, func:allocateChunkDurations, type:Config, type:Report [INFERRED]
- **KrillinAI CLI Command Set** — cli_subtitle_command, cli_tts_command, cli_render_horizontal_command, cli_render_vertical_command, cli_pipeline_command, cli_cover_command, cli_status_command [EXTRACTED 1.00]
- **Speech Recognition Providers** — openai_whisper_service, fasterwhisper_service, whisperkit_service, whispercpp_service, alibaba_cloud_asr_service [EXTRACTED 1.00]
- **TTS Service Providers** — alibaba_cloud_tts_service, openai_tts_service [EXTRACTED 1.00]
- **KrillinAI Skills Collection** — krillinai_skill_cli, krillinai_skill_cover, krillinai_skill_pipeline [EXTRACTED 1.00]
- **Alibaba Cloud Service Setup** — alibaba_cloud_access_key, alibaba_cloud_voice_service_activation, alibaba_cloud_oss_activation [EXTRACTED 1.00]
- **hyperedge:render-horizontal-bilingual-workflow** —  [INFERRED]
- **hyperedge:render-horizontal-dubbed-workflow** —  [INFERRED]
- **hyperedge:render-vertical-bilingual-workflow** —  [INFERRED]
- **hyperedge:render-vertical-dubbed-workflow** —  [INFERRED]
- **hyperedge:subtitle-workflow** —  [INFERRED]
- **hyperedge:tts-workflow** —  [INFERRED]

## Communities (61 total, 19 thin omitted)

### Community 0 - "Cover Image Generation"
Cohesion: 0.06
Nodes (44): coverFailureResponse(), coverImageBytes(), coverManifest(), coverResponse(), failCoverStage(), GenerateCover(), RenderCoverPrompt(), TestGenerateCoverRejectsEmptyPrompt() (+36 more)

### Community 1 - "CLI & Alibaba Cloud Setup"
Cohesion: 0.06
Nodes (52): Alibaba Cloud Access Key, Alibaba Cloud ASR, Alibaba Cloud OSS Activation, Alibaba Cloud Setup Guide, Alibaba Cloud TTS, Alibaba Cloud Voice Service Activation, Caption Source Strategy, cover Command (+44 more)

### Community 2 - "Image & Brand Assets"
Cohesion: 0.05
Nodes (50): command:render-horizontal, command:render-vertical, command:subtitle, command:tts, concept:chinese-word-segmentation, concept:display-width-splitting, config:config.toml, input:bilingual-top (+42 more)

### Community 3 - "Project Documentation & Localization"
Cohesion: 0.06
Nodes (49): Dockerfile, GoReleaser Build Config, README.md, aliyun.md (EN), aliyun.md (Arabic), docker.md (EN), docker.md (Arabic), edge_tts_voice_code.md (+41 more)

### Community 4 - "Audio-to-Subtitle Pipeline"
Cohesion: 0.05
Nodes (49): AudioSegment, DataWithId, TranslatedItem, findMaxIncreasingSubArray, jumpFindMaxIncreasingSubArray, dubbing.NewRunner, ClipAudio, DownloadYouTubeSubtitle (+41 more)

### Community 5 - "Alibaba Cloud SDK Clients"
Cohesion: 0.06
Nodes (45): AsrClient.Transcription, ChatClient.ChatCompletion, CreateToken, func:GenerateID, GenerateSignature, NewAsrClient, NewChatClient, NewOssClient (+37 more)

### Community 6 - "Video & Subtitle Utilities"
Cohesion: 0.05
Nodes (44): ConvertBlockVttToSrt, ConvertVttToSrt, func:FindClosestConsecutiveWords, func:IsAsianLanguage, IsTextMatch, MillisecondsToTime, ParseSrtFile, ParseVttTime (+36 more)

### Community 7 - "YouTube Subtitle Testing"
Cohesion: 0.07
Nodes (44): youtube_subtitle_test.go, func:AddSuffixToFileName, func:BeautifyAsianLanguageSentence, func:CheckDependency, func:CleanMarkdownCodeBlock, func:ConvertTimes, func:CopyFile, func:CountEffectiveChars (+36 more)

### Community 8 - "Service Adapter Layer"
Cohesion: 0.07
Nodes (26): CaptionSource, Error, ErrorKind, fakeStageService, LineMode, Outputs, Response, Stage (+18 more)

### Community 9 - "Documentation Concepts"
Cohesion: 0.08
Nodes (30): Alibaba Cloud, CLI Tool, Docker Deployment, KrillinAI Project, Localization, Agent Skills, Text-to-Speech, Whisper ASR (+22 more)

### Community 10 - "Image Assets Collection"
Cohesion: 0.08
Nodes (27): func:AnimatedContainer, func:DividedContainer, func:FadeAnimation, func:GhostButton, func:ModernCard, func:NewCustomTheme, func:NewFileManager, func:PrimaryButton (+19 more)

### Community 11 - "Dubbing Types & Config"
Cohesion: 0.16
Nodes (17): DubSubtitleFileName, DubbingDirName, DubbingInputFileName, DubbingPlanFileName, DubbingReportName, types.go, DefaultConfig(), TextOptimizer (+9 more)

### Community 12 - "Duration Estimation"
Cohesion: 0.26
Nodes (15): estimator.go, HeuristicEstimator.Estimate(), NewHeuristicEstimator(), StatisticalEstimator.Estimate(), StatisticalEstimator.calibrationFactor(), acronymPenalty(), nonSpaceRuneCount(), numberPenalty() (+7 more)

### Community 13 - "Service Adapter Interface"
Cohesion: 0.14
Nodes (4): NewServiceAdapter(), TestNewServiceAdapterKeepsService(), ServiceAdapter, StageService

### Community 14 - "Video Rendering Pipeline"
Cohesion: 0.16
Nodes (14): RenderVideoRequest, RenderVideo, buildEmbedSubtitleArgs, convertToVertical, embedSubtitles, getResolution, prepareRenderVideoInput, renderSubtitleFile (+6 more)

### Community 15 - "Audio Assembly & Chunking"
Cohesion: 0.31
Nodes (13): audio.go, AssembleAudio(), AssembleChunkAudio(), buildAtempoFilter(), chunkFittedEnd(), chunkSpeedFactor(), defaultFFmpegRunner(), fittedChunkPath() (+5 more)

### Community 16 - "Working Directory Management"
Cohesion: 0.27
Nodes (10): makeTaskID(), NormalizeInput(), ResolveWorkdir(), TestMakeTaskIDEmptyInputUsesTaskFallback(), TestMakeTaskIDUsesEightCharSuffix(), TestMakeTaskIDUsesEmptyQueryVAsFallback(), TestMakeTaskIDUsesQueryVWithoutPath(), TestNormalizeLocalInput() (+2 more)

### Community 17 - "OpenAI-Compatible Image Gen"
Cohesion: 0.29
Nodes (12): NewOpenAICompatibleClient, OpenAICompatibleClient.Generate, TestOpenAICompatibleGenerateAcceptsURLResponse, TestOpenAICompatibleGenerateOmitsResponseFormatForGPTImage, TestOpenAICompatibleGenerateReturnsHTTPError, TestOpenAICompatibleGenerateSendsJSONRequest, openai_compatible.go, openai_compatible_test.go (+4 more)

### Community 18 - "Dubbing Runner Pipeline"
Cohesion: 0.27
Nodes (12): runner.go, NewPlanner(), NewRunner(), NewStatisticalEstimator(), Runner.Run(), Runner.validate(), buildMuxArgs(), cleanCuesForSpeech() (+4 more)

### Community 19 - "Miscellaneous Code"
Cohesion: 0.22
Nodes (10): func:CreateConfigTab, func:CreateLlmTab, func:GetCurrentThemeIsDark, func:GlassmorphismCard, func:NewThemeManager, func:SetGlobalThemeManager, func:Show_Desktop, func:createStartButton (+2 more)

### Community 20 - "SRT Extraction Logic"
Cohesion: 0.33
Nodes (7): ExtractTargetSRT(), readSRTBlocks(), targetLine(), TestExtractBilingualTargetBottom(), TestExtractBilingualTargetTop(), TestExtractTargetOnlyKeepsSingleLineBlocks(), srtBlock

### Community 21 - "Miscellaneous Code"
Cohesion: 0.22
Nodes (9): pkg:dto, type:GetVideoSubtitleTaskReq, type:GetVideoSubtitleTaskRes, type:GetVideoSubtitleTaskResData, type:StartVideoSubtitleTaskReq, type:StartVideoSubtitleTaskRes, type:StartVideoSubtitleTaskResData, type:SubtitleInfoDTO (+1 more)

### Community 22 - "Dubbing Text Cleaning"
Cohesion: 0.31
Nodes (9): clean.go, planner.go, CleanTextForSpeech(), IsSilenceOnlyText(), Planner.Plan(), Planner.makeChunks(), dubbing, parenNoisePattern (+1 more)

### Community 23 - "OpenAI Chat & TTS"
Cohesion: 0.25
Nodes (8): Client.ChatCompletion (openai), Client.Text2Speech (openai), NewOpenAIClient, parseJSONResponse (openai), init.go, openai.go, krillin-ai/pkg/openai, OpenAIClient

### Community 24 - "Miscellaneous Code"
Cohesion: 0.32
Nodes (8): func:Execute_CLI, func:Help_CLI, func:Parse_CLI, func:findDefaultSubtitleStylePath, func:loadSubtitleStyleForCLI, pkg:cli, type:Command, type:subtitleStyleLoadError

### Community 25 - "Miscellaneous Code"
Cohesion: 0.29
Nodes (8): func:CreateSubtitleTask, func:GetSubtitleTaskStatus, pkg:api, type:SubtitleManager, type:SubtitleResult, type:SubtitleTaskAPI, type:TaskStatus, type:WordReplacement

### Community 26 - "SRT Parsing & Cues"
Cohesion: 0.25
Nodes (5): srt.go, BuildDubCues(), ParseSRTFile(), WriteSRTFile(), Cue

### Community 27 - "WhisperCPP Integration"
Cohesion: 0.33
Nodes (7): NewWhispercppProcessor, WhispercppProcessor.Transcription, parseTimestampToSeconds, init.go, transcription.go, krillin-ai/pkg/whispercpp, WhispercppProcessor

### Community 28 - "Miscellaneous Code"
Cohesion: 0.29
Nodes (7): func:CreateSubtitleTab, func:NewSubtitleManager, func:createEmbedSettingsCard, func:createProgressAndDownloadArea, func:createSubtitleSettingsCard, func:createVideoInputContainer, func:createVoiceSettingsCard

### Community 29 - "Edge TTS Client"
Cohesion: 0.40
Nodes (6): EdgeTtsClient.Text2Speech, EdgeTtsClient.attemptTTS, NewEdgeTtsClient, edgetts.go, krillin-ai/pkg/localtts, EdgeTtsClient

### Community 30 - "WhisperKit Integration"
Cohesion: 0.33
Nodes (6): NewWhisperKitProcessor, WhisperKitProcessor.Transcription, init.go, transcription.go, krillin-ai/pkg/whisperkit, WhisperKitProcessor

### Community 31 - "Pipeline Planning"
Cohesion: 0.40
Nodes (4): PlanOutputs(), TestPlanOutputsMapsToStages(), TestPlanOutputsRejectsUnsupportedOutput(), PipelineRequest

### Community 32 - "FasterWhisper Integration"
Cohesion: 0.33
Nodes (6): FastwhisperProcessor.Transcription, NewFastwhisperProcessor, init.go, transcription.go, krillin-ai/pkg/fasterwhisper, FastwhisperProcessor

### Community 33 - "Whisper Integration"
Cohesion: 0.33
Nodes (6): NewWhisperClient, WhisperClient.Transcription, init.go, whisper.go, krillin-ai/pkg/whisper, WhisperClient

### Community 34 - "TTS Segment Generation"
Cohesion: 0.60
Nodes (6): tts.go, GenerateRawChunkSegments(), GenerateRawSegments(), WriteTinySilence(), chunkSpeechText(), retryTTS()

### Community 35 - "Miscellaneous Code"
Cohesion: 0.40
Nodes (5): func:StyledEntry, func:StyledSelect, func:createAppConfigGroup, func:createLlmConfigGroup, func:createServerConfigGroup

### Community 36 - "Timeline Fitting"
Cohesion: 0.70
Nodes (5): fit.go, FitTimeline(), allocateChunkDurations(), chunkActualDuration(), normalizeSpeedConfig()

### Community 37 - "LLM Text Optimizer"
Cohesion: 0.50
Nodes (4): optimizer.go, NewLLMOptimizer(), LLMOptimizer, fakeChat

### Community 38 - "Subtitle Style Config"
Cohesion: 0.50
Nodes (4): Subtitle Style Format, Subtitle Style Cinematic Test, Subtitle Style Default, Subtitle Style Example

### Community 41 - "Miscellaneous"
Cohesion: 0.67
Nodes (3): func:createApiProvidersCard, func:createProviderCard, func:getProviderIcon

## Knowledge Gaps
- **71 isolated node(s):** `Service`, `NewService`, `PrepareMedia`, `GenerateSubtitlesFromAudio`, `GenerateSpeechFromSRT` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GenerateSubtitles()` connect `Service Adapter Layer` to `Cover Image Generation`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Why does `subtitleManifest()` connect `Cover Image Generation` to `Service Adapter Layer`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **What connects `Service`, `NewService`, `PrepareMedia` to the rest of the system?**
  _71 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Cover Image Generation` be split into smaller, more focused modules?**
  _Cohesion score 0.06493506493506493 - nodes in this community are weakly interconnected._
- **Should `CLI & Alibaba Cloud Setup` be split into smaller, more focused modules?**
  _Cohesion score 0.05580693815987934 - nodes in this community are weakly interconnected._
- **Should `Image & Brand Assets` be split into smaller, more focused modules?**
  _Cohesion score 0.05142857142857143 - nodes in this community are weakly interconnected._
- **Should `Project Documentation & Localization` be split into smaller, more focused modules?**
  _Cohesion score 0.05782312925170068 - nodes in this community are weakly interconnected._