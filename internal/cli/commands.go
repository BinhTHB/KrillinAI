package cli

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"krillin-ai/internal/pipeline"
	subtitlestyle "krillin-ai/internal/subtitle_style"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
)

const defaultSubtitleStylePath = "config/subtitle-style-default.json"

type subtitleStyleLoadError struct {
	err  error
	user bool
}

func (e subtitleStyleLoadError) Error() string {
	if e.err == nil {
		return ""
	}
	return e.err.Error()
}

func (e subtitleStyleLoadError) Unwrap() error {
	return e.err
}

func userStyleLoadError(err error) error {
	return subtitleStyleLoadError{err: err, user: true}
}

func defaultStyleLoadError(err error) error {
	return subtitleStyleLoadError{err: err}
}

type Command struct {
	Name              string
	Help              bool
	DryRun            bool
	SubtitleStyleFile string
	Subtitle          pipeline.SubtitleRequest
	TTS               pipeline.TTSRequest
	Render            pipeline.RenderRequest
	Cover             pipeline.CoverRequest
	Pipeline          pipeline.PipelineRequest
	GeminiDub         GeminiDubRequest
}

type GeminiDubRequest struct {
	Input              string
	Workdir            string
	TaskID             string
	OriginLang         string
	TargetLang         string
	UserLang           string
	CaptionSrc         string
	SRT                string
	Video              string
	OutputDir          string
	Provider           string
	Model              string
	Voice              string
	Speed              string
	Gap                string
	VoiceVolume        string
	BgVolume           string
	TimelineMode       string
	ASRTimestampOffset string
	Python             string
	Script             string
	MaxChunks          string
	KeepCache          bool
	PreserveCues       bool
	TimestampOnly      bool
}

func Parse(args []string) (Command, error) {
	if len(args) == 0 {
		return Command{}, errors.New("missing command")
	}
	name := args[0]
	if isHelpArg(name) {
		return Command{Help: true}, nil
	}
	switch name {
	case "subtitle":
		return parseSubtitle(name, args[1:])
	case "tts":
		return parseTTS(name, args[1:])
	case "render-horizontal":
		return parseRender(name, args[1:], true)
	case "render-vertical":
		return parseRender(name, args[1:], false)
	case "pipeline":
		return parsePipeline(name, args[1:])
	case "cover":
		return parseCover(name, args[1:])
	case "gemini-dub":
		return parseGeminiDub(name, args[1:])
	case "status":
		if hasHelpArg(args[1:]) {
			return Command{Name: name, Help: true}, nil
		}
		return Command{Name: name}, nil
	default:
		return Command{}, fmt.Errorf("unknown command: %s", name)
	}
}

func Help(cmd Command) string {
	switch cmd.Name {
	case "subtitle":
		return `Usage:
  krillinai-cli subtitle <input> --origin-lang <lang> --target-lang <lang> --workdir <dir> [flags]

Flags:
  --origin-lang <lang>       Source language, such as en, zh, ja
  --target-lang <lang>       Target language, such as zh_cn
  --user-lang <lang>         UI language for generated messages
  --workdir <dir>            Task working directory
  --task-id <id>             Optional task id
  --caption-source <source>  any, manual, auto, or whisper
  --bilingual-top            Put target subtitle on top (default true)
  --max-word-one-line <n>    Max words per subtitle line
  --subtitle-style-file <file>  JSON subtitle style override file
  --dry-run                  Validate command without external calls
  -h, --help                 Show this help
`
	case "tts":
		return `Usage:
  krillinai-cli tts --workdir <dir> --input-srt <file> [flags]

Flags:
  --workdir <dir>                 Task working directory
  --task-id <id>                  Optional task id
  --input-srt <file>              SRT file to synthesize
  --line-mode <mode>              target-only, bilingual-target-top, or bilingual-target-bottom
  --video <file>                  Optional source video for dubbed output
  --voice <voice>                 Provider-specific voice
  --voice-clone-source <source>   Optional voice clone source
  --dry-run                       Validate and write manifest without external calls
  -h, --help                      Show this help
`
	case "render-horizontal":
		return `Usage:
  krillinai-cli render-horizontal --workdir <dir> --video <file> --subtitle <file> [flags]

Flags:
  --workdir <dir>       Task working directory
  --task-id <id>        Optional task id
  --video <file>        Input video
  --audio <file>        Optional input audio
  --subtitle <file>     Subtitle file to burn in
  --subtitle-style-file <file>  JSON subtitle style override file
  --dubbed              Render dubbed variant
  --dry-run             Validate command without external calls
  -h, --help            Show this help
`
	case "render-vertical":
		return `Usage:
  krillinai-cli render-vertical --workdir <dir> --video <file> --subtitle <file> [flags]

Flags:
  --workdir <dir>       Task working directory
  --task-id <id>        Optional task id
  --video <file>        Input video
  --audio <file>        Optional input audio
  --subtitle <file>     Subtitle file to burn in
  --subtitle-style-file <file>  JSON subtitle style override file
  --dubbed              Render dubbed variant
  --major-title <text>  Vertical video major title
  --minor-title <text>  Vertical video minor title
  --dry-run             Validate command without external calls
  -h, --help            Show this help
`
	case "pipeline":
		return `Usage:
  krillinai-cli pipeline --outputs <list> [flags]

Flags:
  --outputs <list>  Comma-separated outputs, such as subtitle,tts,vertical-bilingual
  --async           Run asynchronously when supported
  --dry-run         Validate requested outputs
  -h, --help        Show this help
`
	case "cover":
		return `Usage:
  krillinai-cli cover --workdir <dir> --prompt <text> [flags]

Flags:
  --workdir <dir>   Task working directory
  --task-id <id>    Optional task id
  --prompt <text>   Prompt for GPT image cover generation
  --size <size>     Image size, such as 1024x1024 or 1536x1024
  --dry-run         Validate and write manifest without external calls
  -h, --help        Show this help
`
	case "gemini-dub":
		return `Usage:
  krillinai-cli gemini-dub [input-url-or-path] [flags]

Runs subtitle generation when input-url-or-path is provided, then runs the controlled Gemini Live dubbing pipeline and renders the final video.
When input-url-or-path is provided and --workdir is omitted, a timestamped workdir is created under tasks/.

Flags:
  --workdir <dir>        Task working directory (optional with input URL/path)
  --task-id <id>         Optional task id
  --origin-lang <lang>   Source language (default zh)
  --target-lang <lang>   Target language (default vi)
  --user-lang <lang>     UI language (default vi)
  --caption-source <src> any, manual, auto, or whisper (default whisper)
  --srt <file>           Input translated SRT after subtitle stage (default target_language_srt_clean.srt)
  --video <file>         Input source video (default origin_video.mp4)
  --output-dir <dir>     Output directory under workdir (default controlled_gemini_live)
  --provider <provider>  gemini, hybrid, or edge (default gemini)
  --model <model>        Gemini Live model (default gemini-3.1-flash-live-preview)
  --voice <voice>        Gemini voice: Puck, Charon, Kore, Fenrir, Aoede (default Aoede)
  --speed <n>            Local TTS speed-up factor (default 2.1)
  --gap <n>              Gap after each chunk in seconds (default 0.02)
  --voice-volume <n>     Voice volume multiplier (default 1.6)
  --max-chunks <n>       Optional preview limit
  --match-timestamps-only  Stop after writing a timestamp-matched clean SRT; do not run TTS/render
  --preserve-cues        One TTS chunk per SRT cue; preserve source subtitle timing and freeze if needed (default true)
  --python <path>        Python executable (default python)
  --script <path>        Dubbing script path (default scripts/controlled_tts_segment_freezing_dub.py)
  --keep-cache           Keep existing output/cache directory
  --dry-run              Validate command without running the script
  -h, --help             Show this help
`
	case "status":
		return `Usage:
  krillinai-cli status

Status query is a reserved/planned CLI surface in the current implementation.
`
	default:
		return `Usage:
  krillinai-cli <command> [flags]

Commands:
  subtitle             Generate source, target, bilingual, and short vertical subtitles
  tts                  Generate target-language dubbing from SRT subtitles
  render-horizontal    Render landscape subtitle or dubbed videos
  render-vertical      Render portrait subtitle or dubbed videos
  pipeline             Plan or run multi-stage workflows when supported
  cover                Generate a cover image from a prompt
  gemini-dub           Run controlled Gemini Live dubbing and render final video
  status               Reserved status query surface

Run "krillinai-cli <command> --help" for command-specific flags.
`
	}
}

func Execute(ctx context.Context, svc pipeline.StageService, cmd Command) pipeline.Response {
	if cmd.DryRun {
		return dryRun(cmd)
	}
	switch cmd.Name {
	case "subtitle":
		style, err := loadSubtitleStyleForCLI(cmd.SubtitleStyleFile)
		if err != nil {
			return styleLoadFailure(pipeline.StageSubtitle, cmd.Subtitle.Workdir, cmd.Subtitle.TaskID, err)
		}
		cmd.Subtitle.SubtitleStyle = style
		resp, err := pipeline.GenerateSubtitles(ctx, svc, cmd.Subtitle)
		return responseWithError(resp, err)
	case "tts":
		resp, err := pipeline.GenerateTTS(ctx, svc, cmd.TTS)
		return responseWithError(resp, err)
	case "render-horizontal", "render-vertical":
		style, err := loadSubtitleStyleForCLI(cmd.SubtitleStyleFile)
		if err != nil {
			return styleLoadFailure(renderStageFromCommand(cmd.Name), cmd.Render.Workdir, cmd.Render.TaskID, err)
		}
		cmd.Render.SubtitleStyle = style
		resp, err := pipeline.Render(ctx, svc, cmd.Render)
		return responseWithError(resp, err)
	case "cover":
		resp, err := pipeline.GenerateCover(ctx, svc, cmd.Cover)
		return responseWithError(resp, err)
	case "gemini-dub":
		return executeGeminiDub(ctx, svc, cmd.GeminiDub)
	default:
		return pipeline.Response{
			OK: false,
			Error: &pipeline.Error{
				Kind:    pipeline.ErrorKindUsage,
				Code:    "unsupported_command",
				Message: fmt.Sprintf("unsupported command: %s", cmd.Name),
			},
		}
	}
}

func parseCover(name string, args []string) (Command, error) {
	if hasHelpArg(args) {
		return Command{Name: name, Help: true}, nil
	}
	fs := newFlagSet(name)
	workdir := fs.String("workdir", "", "workdir")
	taskID := fs.String("task-id", "", "task id")
	prompt := fs.String("prompt", "", "image prompt")
	size := fs.String("size", "", "image size")
	dryRun := fs.Bool("dry-run", false, "validate command without running external services")
	if err := fs.Parse(args); err != nil {
		return Command{}, err
	}
	if strings.TrimSpace(*prompt) == "" {
		return Command{}, errors.New("cover requires --prompt")
	}
	return Command{
		Name:   name,
		DryRun: *dryRun,
		Cover: pipeline.CoverRequest{
			Workdir: *workdir,
			TaskID:  *taskID,
			Prompt:  *prompt,
			Size:    *size,
		},
	}, nil
}

func parseGeminiDub(name string, args []string) (Command, error) {
	if hasHelpArg(args) {
		return Command{Name: name, Help: true}, nil
	}
	fs := newFlagSet(name)
	workdir := fs.String("workdir", "", "workdir")
	taskID := fs.String("task-id", "", "task id")
	originLang := fs.String("origin-lang", "zh", "origin language")
	targetLang := fs.String("target-lang", "vi", "target language")
	userLang := fs.String("user-lang", "vi", "user interface language")
	captionSource := fs.String("caption-source", string(pipeline.CaptionSourceWhisper), "caption source")
	srt := fs.String("srt", "target_language_srt.srt", "input translated srt")
	video := fs.String("video", "origin_video.mp4", "input video")
	outputDir := fs.String("output-dir", "controlled_gemini_live", "output directory under workdir")
	provider := fs.String("provider", "gemini", "tts provider")
	model := fs.String("model", "gemini-3.1-flash-live-preview", "gemini live model")
	voice := fs.String("voice", "Aoede", "gemini voice")
	speed := fs.String("speed", "2.1", "local speed-up factor")
	gap := fs.String("gap", "0.02", "gap after each chunk")
	voiceVolume := fs.String("voice-volume", "1.6", "voice volume multiplier")
	bgVolume := fs.String("bg-volume", "0.15", "background original audio volume multiplier")
	timelineMode := fs.String("timeline-mode", "freeze", "timeline mode: overlay or freeze")
	asrTimestampOffset := fs.String("asr-timestamp-offset", "0", "seconds added to ASR/origin subtitle timestamps before TTS/render")
	python := fs.String("python", "python", "python executable")
	script := fs.String("script", filepath.Join("scripts", "controlled_tts_segment_freezing_dub.py"), "dubbing script")
	maxChunks := fs.String("max-chunks", "", "optional preview limit")
	preserveCues := fs.Bool("preserve-cues", true, "render one TTS chunk per SRT cue to preserve source subtitle timing (freezes frame if TTS is longer)")
	timestampOnly := fs.Bool("match-timestamps-only", false, "stop after writing a timestamp-matched clean SRT; do not run TTS/render")
	keepCache := fs.Bool("keep-cache", false, "keep existing output/cache directory")
	dryRun := fs.Bool("dry-run", false, "validate command without running the script")
	input := ""
	parseArgs := args
	if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
		input = args[0]
		parseArgs = args[1:]
	}
	if err := fs.Parse(parseArgs); err != nil {
		return Command{}, err
	}
	if input == "" && fs.NArg() == 1 {
		input = fs.Arg(0)
	}
	if fs.NArg() > 1 {
		return Command{}, errors.New("gemini-dub accepts at most one input URL/path")
	}
	resolvedWorkdir := strings.TrimSpace(*workdir)
	if resolvedWorkdir == "" {
		if strings.TrimSpace(input) == "" {
			return Command{}, errors.New("gemini-dub requires --workdir when no input URL/path is provided")
		}
		resolvedWorkdir = defaultGeminiDubWorkdir()
	}
	return Command{
		Name:   name,
		DryRun: *dryRun,
		GeminiDub: GeminiDubRequest{
			Input:              input,
			Workdir:            resolvedWorkdir,
			TaskID:             *taskID,
			OriginLang:         *originLang,
			TargetLang:         *targetLang,
			UserLang:           *userLang,
			CaptionSrc:         *captionSource,
			SRT:                *srt,
			Video:              *video,
			OutputDir:          *outputDir,
			Provider:           *provider,
			Model:              *model,
			Voice:              *voice,
			Speed:              *speed,
			Gap:                *gap,
			VoiceVolume:        *voiceVolume,
			BgVolume:           *bgVolume,
			TimelineMode:       *timelineMode,
			ASRTimestampOffset: *asrTimestampOffset,
			Python:             *python,
			Script:             *script,
			MaxChunks:          *maxChunks,
			KeepCache:          *keepCache,
			PreserveCues:       *preserveCues,
			TimestampOnly:      *timestampOnly,
		},
	}, nil
}

func parseSubtitle(name string, args []string) (Command, error) {
	if hasHelpArg(args) {
		return Command{Name: name, Help: true}, nil
	}
	fs := newFlagSet(name)
	originLang := fs.String("origin-lang", "", "origin language")
	targetLang := fs.String("target-lang", "", "target language")
	userLang := fs.String("user-lang", "", "user interface language")
	workdir := fs.String("workdir", "", "workdir")
	taskID := fs.String("task-id", "", "task id")
	captionSource := fs.String("caption-source", string(pipeline.CaptionSourceAny), "caption source")
	bilingualTop := fs.Bool("bilingual-top", true, "put target subtitle on top")
	maxWordOneLine := fs.Int("max-word-one-line", 0, "max words per line")
	subtitleStyleFile := fs.String("subtitle-style-file", "", "subtitle style JSON file")
	dryRun := fs.Bool("dry-run", false, "validate command without running external services")
	input := ""
	parseArgs := args
	if len(args) > 0 && !strings.HasPrefix(args[0], "-") {
		input = args[0]
		parseArgs = args[1:]
	}
	if err := fs.Parse(parseArgs); err != nil {
		return Command{}, err
	}
	if input == "" && fs.NArg() == 1 {
		input = fs.Arg(0)
	}
	if input == "" || fs.NArg() > 1 {
		return Command{}, errors.New("subtitle requires input")
	}
	return Command{
		Name:              name,
		DryRun:            *dryRun,
		SubtitleStyleFile: *subtitleStyleFile,
		Subtitle: pipeline.SubtitleRequest{
			Input:          input,
			Workdir:        *workdir,
			TaskID:         *taskID,
			OriginLang:     *originLang,
			TargetLang:     *targetLang,
			UserLang:       *userLang,
			CaptionSource:  pipeline.CaptionSource(*captionSource),
			BilingualTop:   *bilingualTop,
			MaxWordOneLine: *maxWordOneLine,
		},
	}, nil
}

func parseTTS(name string, args []string) (Command, error) {
	if hasHelpArg(args) {
		return Command{Name: name, Help: true}, nil
	}
	fs := newFlagSet(name)
	workdir := fs.String("workdir", "", "workdir")
	taskID := fs.String("task-id", "", "task id")
	inputSRT := fs.String("input-srt", "", "input srt")
	lineMode := fs.String("line-mode", string(pipeline.LineModeTargetOnly), "line mode")
	video := fs.String("video", "", "input video")
	voice := fs.String("voice", "", "voice")
	voiceCloneSource := fs.String("voice-clone-source", "", "voice clone source")
	dryRun := fs.Bool("dry-run", false, "validate command without running external services")
	if err := fs.Parse(args); err != nil {
		return Command{}, err
	}
	if *inputSRT == "" {
		return Command{}, errors.New("tts requires --input-srt")
	}
	return Command{
		Name:   name,
		DryRun: *dryRun,
		TTS: pipeline.TTSRequest{
			Workdir:          *workdir,
			TaskID:           *taskID,
			InputSRT:         *inputSRT,
			LineMode:         pipeline.LineMode(*lineMode),
			Video:            *video,
			Voice:            *voice,
			VoiceCloneSource: *voiceCloneSource,
		},
	}, nil
}

func parseRender(name string, args []string, horizontal bool) (Command, error) {
	if hasHelpArg(args) {
		return Command{Name: name, Help: true}, nil
	}
	fs := newFlagSet(name)
	workdir := fs.String("workdir", "", "workdir")
	taskID := fs.String("task-id", "", "task id")
	video := fs.String("video", "", "input video")
	audio := fs.String("audio", "", "input audio")
	subtitle := fs.String("subtitle", "", "subtitle")
	dubbed := fs.Bool("dubbed", false, "render dubbed video")
	majorTitle := fs.String("major-title", "", "vertical major title")
	minorTitle := fs.String("minor-title", "", "vertical minor title")
	subtitleStyleFile := fs.String("subtitle-style-file", "", "subtitle style JSON file")
	dryRun := fs.Bool("dry-run", false, "validate command without running external services")
	if err := fs.Parse(args); err != nil {
		return Command{}, err
	}
	return Command{
		Name:              name,
		DryRun:            *dryRun,
		SubtitleStyleFile: *subtitleStyleFile,
		Render: pipeline.RenderRequest{
			Workdir:    *workdir,
			TaskID:     *taskID,
			Video:      *video,
			Audio:      *audio,
			Subtitle:   *subtitle,
			Horizontal: horizontal,
			Dubbed:     *dubbed,
			MajorTitle: *majorTitle,
			MinorTitle: *minorTitle,
		},
	}, nil
}

func parsePipeline(name string, args []string) (Command, error) {
	if hasHelpArg(args) {
		return Command{Name: name, Help: true}, nil
	}
	fs := newFlagSet(name)
	outputs := fs.String("outputs", "subtitle", "outputs")
	async := fs.Bool("async", false, "run async")
	dryRun := fs.Bool("dry-run", false, "validate command without running external services")
	if err := fs.Parse(args); err != nil {
		return Command{}, err
	}
	if _, err := pipeline.PlanOutputs(*outputs); err != nil {
		return Command{}, err
	}
	return Command{
		Name:   name,
		DryRun: *dryRun,
		Pipeline: pipeline.PipelineRequest{
			Outputs: *outputs,
			Async:   *async,
		},
	}, nil
}

func dryRun(cmd Command) pipeline.Response {
	switch cmd.Name {
	case "subtitle":
		if _, err := loadSubtitleStyleForCLI(cmd.SubtitleStyleFile); err != nil {
			return styleLoadFailure(pipeline.StageSubtitle, cmd.Subtitle.Workdir, cmd.Subtitle.TaskID, err)
		}
		return dryRunResponse(pipeline.StageSubtitle, cmd.Subtitle.Workdir, cmd.Subtitle.TaskID)
	case "tts":
		return dryRunManifest(cmd.TTS.Workdir, cmd.TTS.TaskID, pipeline.StageTTS, nil)
	case "render-horizontal":
		if _, err := loadSubtitleStyleForCLI(cmd.SubtitleStyleFile); err != nil {
			return styleLoadFailure(pipeline.StageRenderHorizontal, cmd.Render.Workdir, cmd.Render.TaskID, err)
		}
		return dryRunResponse(pipeline.StageRenderHorizontal, cmd.Render.Workdir, cmd.Render.TaskID)
	case "render-vertical":
		if _, err := loadSubtitleStyleForCLI(cmd.SubtitleStyleFile); err != nil {
			return styleLoadFailure(pipeline.StageRenderVertical, cmd.Render.Workdir, cmd.Render.TaskID, err)
		}
		return dryRunResponse(pipeline.StageRenderVertical, cmd.Render.Workdir, cmd.Render.TaskID)
	case "cover":
		return dryRunManifest(cmd.Cover.Workdir, cmd.Cover.TaskID, pipeline.StageCover, func(m *pipeline.Manifest) {
			m.Outputs.FinalCoverPrompt = m.Outputs.FinalCoverPrompt
		})
	case "pipeline":
		return pipeline.Response{OK: true, Stage: pipeline.StagePipeline}
	case "gemini-dub":
		return pipeline.Response{
			OK:      true,
			Stage:   pipeline.StageGeminiDub,
			Workdir: cmd.GeminiDub.Workdir,
			TaskID:  cmd.GeminiDub.TaskID,
			Inputs: map[string]string{
				"video": filepath.Join(cmd.GeminiDub.Workdir, cmd.GeminiDub.Video),
				"srt":   filepath.Join(cmd.GeminiDub.Workdir, cmd.GeminiDub.SRT),
			},
			Outputs: pipeline.Outputs{
				VideoWithTTS: filepath.Join(cmd.GeminiDub.Workdir, cmd.GeminiDub.OutputDir, "controlled_tts_final.mp4"),
				TargetSRT:    filepath.Join(cmd.GeminiDub.Workdir, cmd.GeminiDub.OutputDir, "controlled_aligned.srt"),
			},
		}
	default:
		return pipeline.Response{
			OK: false,
			Error: &pipeline.Error{
				Kind:    pipeline.ErrorKindUsage,
				Code:    "unsupported_dry_run",
				Message: fmt.Sprintf("unsupported dry-run command: %s", cmd.Name),
			},
		}
	}
}

func dryRunResponse(stage pipeline.Stage, workdir, taskID string) pipeline.Response {
	return pipeline.Response{
		OK:      true,
		Stage:   stage,
		Workdir: workdir,
		TaskID:  taskID,
	}
}

func dryRunManifest(workdir, taskID string, stage pipeline.Stage, update func(*pipeline.Manifest)) pipeline.Response {
	if workdir == "" {
		workdir = "."
	}
	manifest := pipeline.NewManifest(taskID, workdir)
	if update != nil {
		update(manifest)
	}
	if err := manifest.ApplyDefaultOutputs(); err != nil {
		return dryRunError(stage, workdir, taskID, "apply_outputs_failed", err)
	}
	manifest.MarkStage(stage, true, "dry-run")
	if err := manifest.Save(); err != nil && !errors.Is(err, os.ErrExist) {
		return dryRunError(stage, workdir, taskID, "save_manifest_failed", err)
	}
	return pipeline.Response{
		OK:      true,
		Stage:   stage,
		Workdir: manifest.Workdir,
		TaskID:  manifest.TaskID,
		Outputs: manifest.Outputs,
	}
}

func dryRunError(stage pipeline.Stage, workdir, taskID, code string, err error) pipeline.Response {
	return pipeline.Response{
		OK:      false,
		Stage:   stage,
		Workdir: workdir,
		TaskID:  taskID,
		Error: &pipeline.Error{
			Kind:    pipeline.ErrorKindInternal,
			Code:    code,
			Message: err.Error(),
		},
	}
}

func loadSubtitleStyleForCLI(styleFile string) (*subtitlestyle.StyleSet, error) {
	base := subtitlestyle.DefaultStyleSet()
	if defaultPath, ok, err := findDefaultSubtitleStylePath(); err != nil {
		return nil, defaultStyleLoadError(err)
	} else if ok {
		fileStyle, err := subtitlestyle.LoadOverrideFile(defaultPath)
		if err != nil {
			return nil, defaultStyleLoadError(err)
		}
		base, err = subtitlestyle.Merge(base, fileStyle)
		if err != nil {
			return nil, defaultStyleLoadError(err)
		}
	}
	if strings.TrimSpace(styleFile) == "" {
		return base, nil
	}
	override, err := subtitlestyle.LoadOverrideFile(styleFile)
	if err != nil {
		return nil, userStyleLoadError(err)
	}
	merged, err := subtitlestyle.Merge(base, override)
	if err != nil {
		return nil, userStyleLoadError(err)
	}
	return merged, nil
}

func findDefaultSubtitleStylePath() (string, bool, error) {
	paths := []string{defaultSubtitleStylePath}
	if exe, err := os.Executable(); err == nil {
		exeDir := filepath.Dir(exe)
		paths = appendDefaultStyleParentPaths(paths, exeDir)
	} else if !errors.Is(err, os.ErrNotExist) {
		return "", false, err
	}
	if _, sourceFile, _, ok := runtime.Caller(0); ok {
		paths = appendDefaultStyleParentPaths(paths, filepath.Dir(sourceFile))
	}
	if cwd, err := os.Getwd(); err == nil {
		paths = appendDefaultStyleParentPaths(paths, cwd)
	} else {
		return "", false, err
	}
	seen := make(map[string]bool, len(paths))
	for _, path := range paths {
		clean := filepath.Clean(path)
		if seen[clean] {
			continue
		}
		seen[clean] = true
		if _, err := os.Stat(clean); err == nil {
			return clean, true, nil
		} else if !errors.Is(err, os.ErrNotExist) {
			return "", false, err
		}
	}
	return "", false, nil
}

func appendDefaultStyleParentPaths(paths []string, dir string) []string {
	for {
		paths = append(paths, filepath.Join(dir, defaultSubtitleStylePath))
		parent := filepath.Dir(dir)
		if parent == dir {
			return paths
		}
		dir = parent
	}
}

func styleLoadFailure(stage pipeline.Stage, workdir, taskID string, err error) pipeline.Response {
	kind := pipeline.ErrorKindUsage
	code := "subtitle_style_load_failed"
	var styleErr subtitleStyleLoadError
	if errors.As(err, &styleErr) && !styleErr.user {
		kind = pipeline.ErrorKindInternal
		code = "default_subtitle_style_load_failed"
	}
	return pipeline.Response{
		OK:      false,
		Stage:   stage,
		Workdir: workdir,
		TaskID:  taskID,
		Error: &pipeline.Error{
			Kind:    kind,
			Code:    code,
			Message: err.Error(),
		},
	}
}

func executeGeminiDub(ctx context.Context, svc pipeline.StageService, req GeminiDubRequest) pipeline.Response {
	start := time.Now()

	if err := os.MkdirAll(req.Workdir, 0755); err != nil {
		return pipeline.Response{
			OK:      false,
			Stage:   pipeline.StageGeminiDub,
			Workdir: req.Workdir,
			TaskID:  req.TaskID,
			Error: &pipeline.Error{
				Kind:    pipeline.ErrorKindInternal,
				Code:    "mkdir_workdir_failed",
				Message: err.Error(),
			},
		}
	}

	if req.Input != "" {
		subReq := pipeline.SubtitleRequest{
			Input:         req.Input,
			Workdir:       req.Workdir,
			TaskID:        req.TaskID,
			OriginLang:    req.OriginLang,
			TargetLang:    req.TargetLang,
			UserLang:      req.UserLang,
			CaptionSource: pipeline.CaptionSource(req.CaptionSrc),
			BilingualTop:  true,
		}
		subResp, err := pipeline.GenerateSubtitles(ctx, svc, subReq)
		if err != nil {
			return responseWithError(subResp, err)
		}
		if !subResp.OK {
			return subResp
		}
		if err := ensureGeminiDubVideo(req); err != nil {
			return geminiDubFailure(req, "download_video_failed", err, start)
		}
	}

	resolvedSRT, err := resolveGeminiDubSRT(req)
	if err != nil {
		return geminiDubFailure(req, "resolve_srt_failed", err, start)
	}
	cleanSRT, err := prepareGeminiDubCleanSRT(req, resolvedSRT)
	if err != nil {
		return geminiDubFailure(req, "prepare_clean_srt_failed", err, start)
	}
	if req.TimestampOnly {
		cleanPath := filepath.Join(req.Workdir, cleanSRT)
		defaultCleanPath := filepath.Join(req.Workdir, "target_language_srt_clean.srt")
		if cleanSRT != "target_language_srt_clean.srt" {
			data, readErr := os.ReadFile(cleanPath)
			if readErr != nil {
				return geminiDubFailure(req, "read_clean_srt_failed", readErr, start)
			}
			if writeErr := os.WriteFile(defaultCleanPath, data, 0644); writeErr != nil {
				return geminiDubFailure(req, "write_default_clean_srt_failed", writeErr, start)
			}
			cleanPath = defaultCleanPath
			cleanSRT = "target_language_srt_clean.srt"
		}
		return pipeline.Response{
			OK:      true,
			Stage:   pipeline.StageGeminiDub,
			Workdir: req.Workdir,
			TaskID:  req.TaskID,
			Inputs: map[string]string{
				"video": filepath.Join(req.Workdir, req.Video),
				"srt":   filepath.Join(req.Workdir, resolvedSRT),
			},
			Outputs: pipeline.Outputs{
				TargetSRT: cleanPath,
			},
			DurationMS: time.Since(start).Milliseconds(),
		}
	}

	args := []string{
		req.Script,
		"--workdir", req.Workdir,
		"--srt", cleanSRT,
		"--video", req.Video,
		"--output-dir", req.OutputDir,
		"--tts-provider", req.Provider,
		"--gemini-model", req.Model,
		"--gemini-voice", req.Voice,
		"--force-speed",
		"--speed", req.Speed,
		"--gap", req.Gap,
		"--voice-volume", req.VoiceVolume,
		"--bg-volume", req.BgVolume,
		"--timeline-mode", req.TimelineMode,
		"--asr-timestamp-offset", req.ASRTimestampOffset,
	}
	if strings.TrimSpace(req.MaxChunks) != "" {
		args = append(args, "--max-chunks", req.MaxChunks)
	}
	if req.KeepCache {
		args = append(args, "--keep-cache")
	}
	if req.PreserveCues {
		args = append(args, "--preserve-cues")
	}

	cmd := exec.Command(req.Python, args...)
	cmd.Stdout = os.Stderr
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return pipeline.Response{
			OK:      false,
			Stage:   pipeline.StageGeminiDub,
			Workdir: req.Workdir,
			TaskID:  req.TaskID,
			Error: &pipeline.Error{
				Kind:      pipeline.ErrorKindRetryable,
				Code:      "gemini_dub_failed",
				Message:   err.Error(),
				Retryable: true,
			},
			DurationMS: time.Since(start).Milliseconds(),
		}
	}

	outputBase := filepath.Join(req.Workdir, req.OutputDir)
	return pipeline.Response{
		OK:      true,
		Stage:   pipeline.StageGeminiDub,
		Workdir: req.Workdir,
		TaskID:  req.TaskID,
		Inputs: map[string]string{
			"video": filepath.Join(req.Workdir, req.Video),
			"srt":   filepath.Join(req.Workdir, req.SRT),
		},
		Outputs: pipeline.Outputs{
			VideoWithTTS: filepath.Join(outputBase, "controlled_tts_final.mp4"),
			TargetSRT:    filepath.Join(outputBase, "controlled_aligned.srt"),
		},
		DurationMS: time.Since(start).Milliseconds(),
	}
}

func defaultGeminiDubWorkdir() string {
	return filepath.Join("tasks", "gemini-dub-"+time.Now().Format("20060102-150405"))
}

func resolveGeminiDubSRT(req GeminiDubRequest) (string, error) {
	if fileExists(filepath.Join(req.Workdir, req.SRT)) {
		return req.SRT, nil
	}
	if req.SRT == "target_language_srt_clean.srt" && fileExists(filepath.Join(req.Workdir, "target_language_srt.srt")) {
		return "target_language_srt.srt", nil
	}
	return "", fmt.Errorf("input SRT not found: %s", filepath.Join(req.Workdir, req.SRT))
}

var srtTimeLineRE = regexp.MustCompile(`(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})`)

func prepareGeminiDubCleanSRT(req GeminiDubRequest, inputSRT string) (string, error) {
	inputPath := filepath.Join(req.Workdir, inputSRT)
	content, err := os.ReadFile(inputPath)
	if err != nil {
		return "", err
	}
	entries, err := parseGeminiDubSRT(string(content))
	if err != nil {
		return "", err
	}
	if len(entries) == 0 {
		return "", fmt.Errorf("input SRT has no entries: %s", inputPath)
	}

	videoPath := filepath.Join(req.Workdir, req.Video)
	videoDur := getGeminiDubVideoDuration(videoPath)

	// Preserve cue coverage when the input timeline is suspicious. Scaling may fix
	// timestamps, but merging would hide/drop auditability of translated cues.
	preserveCoverage := needsGeminiDubTimingFix(entries, videoDur)

	// Fix timing using origin_language_srt.srt when input SRT has suspicious timestamps
	fixedEntries, fixErr := fixGeminiDubSRTTiming(req.Workdir, inputPath, entries, inputSRT, videoDur)
	if fixErr != nil {
		return "", fmt.Errorf("timing fix failed: %w", fixErr)
	}
	timingFixed := false
	if fixedEntries != nil {
		fmt.Printf("Fixed %d entries using origin SRT timing\n", len(fixedEntries))
		entries = fixedEntries
		timingFixed = true
	}

	// Check for untranslated CJK — fallback to Python batch translator
	cjkCount := 0
	viCount := 0
	for _, e := range entries {
		if containsCJK(e.Text) {
			cjkCount++
		} else {
			viCount++
		}
	}
	if cjkCount > viCount && !req.TimestampOnly {
		// Too many CJK — not enough Vietnamese; retranslate using fallback script
		return "", fmt.Errorf("too many untranslated CJK entries (%d vs %d Vietnamese), need to retranslate", cjkCount, viCount)
	}
	if cjkCount > 0 && viCount > 0 && !req.TimestampOnly {
		// Partial CJK — run fallback script on origin SRT
		originSRT := filepath.Join(req.Workdir, "origin_language_srt.srt")
		if !containsCJK(string(content)) || fileExists(originSRT) {
			if fileExists(originSRT) {
				fmt.Printf("Translating %d CJK entries via Gemini batch fallback...\n", cjkCount)
				cmd := exec.Command("python", "-u", "scripts/translate_gemini.py",
					"--workdir", req.Workdir,
				)
				cmd.Stdout = os.Stderr
				cmd.Stderr = os.Stderr
				if err := cmd.Run(); err != nil {
					return "", fmt.Errorf("CJK fallback translation failed: %w (will continue with %d CJK remaining)", err, cjkCount)
				}
				// Re-read the updated SRT
				content, err = os.ReadFile(inputPath)
				if err != nil {
					return "", fmt.Errorf("re-read after fallback: %w", err)
				}
				entries, err = parseGeminiDubSRT(string(content))
				if err != nil {
					return "", fmt.Errorf("parse after fallback: %w", err)
				}
			}
		}
	}

	// Determine video duration to cap the final timeline
	if videoDur > 0 && len(entries) > 0 {
		maxEnd := entries[len(entries)-1].End
		if maxEnd > videoDur+1.0 {
			scale := (videoDur - 0.25) / maxEnd
			last := 0.0
			for i, e := range entries {
				ns := e.Start * scale
				ne := e.End * scale
				if ns < last+0.03 {
					ns = last + 0.03
				}
				dur := ne - ns
				if dur < 0.35 {
					dur = 0.35
				}
				ne = ns + dur
				if ne > videoDur-0.02 {
					ne = videoDur - 0.02
				}
				if ne <= ns {
					ne = ns + 0.05
				}
				entries[i].Start = ns
				entries[i].End = ne
				last = ne
			}
		}

		// Merge adjacent blocks only when timing was not rewritten. Rewritten timing preserves
		// every translated cue so TTS receives complete, auditable subtitle coverage.
		if !timingFixed && !preserveCoverage && len(entries) > 35 {
			merged := make([]geminiDubSRTEntry, 0, len(entries))
			var curr *geminiDubSRTEntry
			for _, e := range entries {
				if curr == nil {
					curr = &geminiDubSRTEntry{Start: e.Start, End: e.End, Text: e.Text}
				} else {
					gap := e.Start - curr.End
					duration := e.End - curr.Start
					if gap < 0.8 && duration < 5.5 {
						t1 := strings.TrimSpace(curr.Text)
						t2 := strings.TrimSpace(e.Text)
						if t1 != "" {
							lastChar := t1[len(t1)-1]
							if lastChar != '.' && lastChar != '!' && lastChar != '?' && lastChar != ',' && lastChar != ':' && lastChar != ';' {
								t1 += "."
							}
						}
						curr.Text = t1 + " " + t2
						curr.End = e.End
					} else {
						merged = append(merged, *curr)
						curr = &geminiDubSRTEntry{Start: e.Start, End: e.End, Text: e.Text}
					}
				}
			}
			if curr != nil {
				merged = append(merged, *curr)
			}
			entries = merged
		}
	}

	entries = splitGeminiDubLongEntries(entries)

	// When timing has been fixed by text-matching, use overlay mode so the
	// text-matched anchor timing is preserved rather than re-estimated.
	cleanMode := req.TimelineMode
	maxEntryDur := 12.0
	if timingFixed {
		cleanMode = "overlay"
	}
	cleaned := sanitizeGeminiDubEntries(entries, cleanMode)
	// Cap individual entry duration to prevent validator from rejecting
	// long anchor windows (e.g. the first anchor spans 4→22s of silence).
	for i, e := range cleaned {
		if d := e.End - e.Start; d > maxEntryDur {
			e.End = e.Start + maxEntryDur
			cleaned[i] = e
		}
	}
	cleaned = capGeminiDubEntriesToDuration(cleaned, videoDur)

	if err := validateGeminiDubCleanEntries(cleaned); err != nil {
		return "", err
	}
	cleanName := strings.TrimSuffix(filepath.Base(inputSRT), filepath.Ext(inputSRT)) + "_gemini_clean.srt"
	cleanPath := filepath.Join(req.Workdir, cleanName)
	if err := os.WriteFile(cleanPath, []byte(formatGeminiDubSRT(cleaned)), 0644); err != nil {
		return "", err
	}
	return cleanName, nil
}

func fixGeminiDubSRTTiming(workdir, inputPath string, targetEntries []geminiDubSRTEntry, inputSRT string, videoDur float64) ([]geminiDubSRTEntry, error) {
	// Try text-matching first when both origin files are available,
	// regardless of needsGeminiDubTimingFix, as already-fixed SRTs
	// should still use text-matching to preserve separate target cues.
	fullOriginPath := filepath.Join(workdir, "origin_language_srt.srt")
	shortOriginPath := filepath.Join(workdir, "short_origin_srt.srt")
	if fileExists(fullOriginPath) && fileExists(shortOriginPath) {
		if fixed, err := fixByTextMatch(fullOriginPath, shortOriginPath, targetEntries, videoDur); err == nil && fixed != nil {
			fmt.Printf("Fixed %d entries using text-matched anchor timing\n", len(fixed))
			if err := validateGeminiDubFixedEntries(fixed); err != nil {
				return nil, err
			}
			return fixed, nil
		}
	}

	if !needsGeminiDubTimingFix(targetEntries, videoDur) {
		return nil, nil
	}
	// Fall back to proportional index mapping when text matching can't be used
	originCandidates := []string{"origin_language_srt.srt", "short_origin_srt.srt"}
	var originEntries []geminiDubSRTEntry
	for _, name := range originCandidates {
		originPath := filepath.Join(workdir, name)
		if !fileExists(originPath) {
			continue
		}
		content, err := os.ReadFile(originPath)
		if err != nil {
			continue
		}
		entries, err := parseGeminiDubSRT(string(content))
		if err != nil || len(entries) == 0 {
			continue
		}
		if !isGeminiDubTimingBetter(entries, targetEntries, videoDur) {
			continue
		}
		// Equal-length anchors are accepted for 1:1 index mapping.
		// short_origin_srt is the reliable Whisper segment timeline when the full
		// origin/target SRT contains hallucinated one-second cues or extends beyond
		// the video; distribute all translated target entries over its anchor windows.
		if len(entries) == len(targetEntries) || name == "short_origin_srt.srt" || hasGeminiDubNonMonotonic(targetEntries) {
			originEntries = entries
			break
		}
	}
	if len(originEntries) == 0 {
		return nil, nil
	}

	fixed := distributeGeminiDubTimingByAnchors(originEntries, targetEntries, videoDur)
	if len(fixed) == 0 {
		return nil, nil
	}
	if err := validateGeminiDubFixedEntries(fixed); err != nil {
		return nil, err
	}

	badPath := strings.TrimSuffix(inputPath, filepath.Ext(inputPath)) + ".bad" + filepath.Ext(inputPath)
	if !fileExists(badPath) {
		if err := os.WriteFile(badPath, []byte(formatGeminiDubSRT(targetEntries)), 0644); err != nil {
			return nil, err
		}
	}
	fixedName := strings.TrimSuffix(filepath.Base(inputSRT), filepath.Ext(inputSRT)) + "_fixed.srt"
	fixedPath := filepath.Join(workdir, fixedName)
	if err := os.WriteFile(fixedPath, []byte(formatGeminiDubSRT(fixed)), 0644); err != nil {
		return nil, err
	}
	return fixed, nil
}

func needsGeminiDubTimingFix(entries []geminiDubSRTEntry, videoDur float64) bool {
	if len(entries) == 0 {
		return false
	}
	oneSecond := 0
	nonMonotonic := false
	lastEnd := 0.0
	for _, entry := range entries {
		dur := entry.End - entry.Start
		if dur >= 0.99 && dur <= 1.01 {
			oneSecond++
		}
		if entry.Start < lastEnd-0.001 {
			nonMonotonic = true
		}
		if entry.End > lastEnd {
			lastEnd = entry.End
		}
	}
	if nonMonotonic {
		return true
	}
	if oneSecond*3 > len(entries) {
		return true
	}
	return videoDur > 0 && lastEnd > videoDur+5.0 && oneSecond*5 > len(entries)
}

func hasGeminiDubNonMonotonic(entries []geminiDubSRTEntry) bool {
	lastEnd := 0.0
	for _, entry := range entries {
		if entry.Start < lastEnd-0.001 {
			return true
		}
		if entry.End > lastEnd {
			lastEnd = entry.End
		}
	}
	return false
}

func isGeminiDubTimingBetter(originEntries, targetEntries []geminiDubSRTEntry, videoDur float64) bool {
	originScore := geminiDubTimingBadness(originEntries, videoDur)
	targetScore := geminiDubTimingBadness(targetEntries, videoDur)
	return originScore+5 < targetScore
}

func geminiDubTimingBadness(entries []geminiDubSRTEntry, videoDur float64) int {
	badness := 0
	lastEnd := 0.0
	maxEnd := 0.0
	for _, entry := range entries {
		dur := entry.End - entry.Start
		if dur >= 0.99 && dur <= 1.01 {
			badness += 2
		}
		if dur <= 0 {
			badness += 5
		}
		if entry.Start < lastEnd-0.001 {
			badness += 5
		}
		if entry.End > lastEnd {
			lastEnd = entry.End
		}
		if entry.End > maxEnd {
			maxEnd = entry.End
		}
	}
	if videoDur > 0 && maxEnd > videoDur+5.0 {
		badness += int(maxEnd - videoDur)
	}
	return badness
}

// fixByTextMatch reads the full origin SRT (87 entries with Chinese text,
// one-per-target-entry) and short_origin SRT (43 entries, reliable timing)
// and maps each target entry to the short_origin anchor whose Chinese text
// has the strongest character overlap (≥8 chars).
// Entries without a strong match are linearly interpolated between their
// nearest matched neighbours, giving smooth timing even for dialogue lines
// that the short Whisper SRT didn't independently transcribe.
func fixByTextMatch(fullOriginPath, shortOriginPath string, targets []geminiDubSRTEntry, videoDur float64) ([]geminiDubSRTEntry, error) {
	fullContent, err := os.ReadFile(fullOriginPath)
	if err != nil {
		return nil, err
	}
	shortContent, err := os.ReadFile(shortOriginPath)
	if err != nil {
		return nil, err
	}
	fullEntries, err := parseGeminiDubSRT(string(fullContent))
	if err != nil {
		return nil, err
	}
	shortEntries, err := parseGeminiDubSRT(string(shortContent))
	if err != nil {
		return nil, err
	}
	if len(fullEntries) != len(targets) {
		return nil, fmt.Errorf("full origin length %d does not match targets %d", len(fullEntries), len(targets))
	}
	if len(shortEntries) == 0 {
		return nil, fmt.Errorf("short origin is empty")
	}

	nTarget := len(targets)
	nAnchor := len(shortEntries)

	// Sort short_origin by start time for stable window assignment
	sortedAnchors := append([]geminiDubSRTEntry(nil), shortEntries...)
	sort.SliceStable(sortedAnchors, func(i, j int) bool {
		return sortedAnchors[i].Start < sortedAnchors[j].Start
	})

	// Clean Chinese text (keep only CJK+alnum)
	cleanFull := make([]string, nTarget)
	for i, e := range fullEntries {
		cleanFull[i] = cleanChineseText(e.Text)
	}
	cleanAnchor := make([]string, nAnchor)
	for j, e := range sortedAnchors {
		cleanAnchor[j] = cleanChineseText(e.Text)
	}

	fixed := make([]geminiDubSRTEntry, nTarget)
	for i := 0; i < nTarget; i++ {
		fixed[i] = geminiDubSRTEntry{Index: i + 1, Text: targets[i].Text}
	}

	// Phase 1 — find strong text matches
	type match struct{ targetIdx, anchorIdx int }
	const minOverlap = 8
	matched := []match{}
	// per‑target best anchor (pre‑threshold)
	bestAnchor := make([]int, nTarget)
	bestOverlap := make([]int, nTarget)
	for i := 0; i < nTarget; i++ {
		bj, bo := -1, -1
		for j := 0; j < nAnchor; j++ {
			o := chineseOverlapScore(cleanFull[i], cleanAnchor[j])
			if o > bo {
				bo = o
				bj = j
			}
		}
		bestAnchor[i] = bj
		bestOverlap[i] = bo
	}

	// Accept strong matches while enforcing sequential anchor order
	lastAJ := -1
	for i := 0; i < nTarget; i++ {
		if bestOverlap[i] >= minOverlap && bestAnchor[i] > lastAJ {
			if len(matched) > 0 && bestAnchor[i] == lastAJ {
				// consecutive targets can share the same anchor
				matched = append(matched, match{targetIdx: i, anchorIdx: bestAnchor[i]})
				continue
			}
			if bestAnchor[i] > lastAJ {
				matched = append(matched, match{targetIdx: i, anchorIdx: bestAnchor[i]})
				lastAJ = bestAnchor[i]
			}
		}
	}

	// If too few matches, fall back to proportional mapping
	if len(matched) < 2 && nTarget > 1 {
		return nil, fmt.Errorf("only %d text matches, insufficient for interpolation", len(matched))
	}

	const innerGap = 0.05

	// Phase 2 — assign timing for strong matches
	for mi, m := range matched {
		aj := m.anchorIdx
		if aj >= nAnchor {
			aj = nAnchor - 1
		}
		winStart := sortedAnchors[aj].Start
		var winEnd float64
		if aj+1 < nAnchor {
			winEnd = sortedAnchors[aj+1].Start
		} else {
			winEnd = sortedAnchors[aj].End
			if videoDur > 0 && videoDur > winStart {
				winEnd = videoDur
			}
		}
		// A full-origin sentence can span several short-origin anchors. Extend the
		// matched window across consecutive anchors that still share text with it.
		for ka := aj + 1; ka < nAnchor; ka++ {
			if chineseOverlapScore(cleanFull[m.targetIdx], cleanAnchor[ka]) < minOverlap/2 {
				break
			}
			if ka+1 < nAnchor {
				winEnd = sortedAnchors[ka+1].Start
			} else {
				winEnd = sortedAnchors[ka].End
				if videoDur > 0 && videoDur > winStart {
					winEnd = videoDur
				}
			}
		}
		if winEnd <= winStart {
			winEnd = winStart + 1.0
		}
		if videoDur > 0 && winEnd > videoDur {
			winEnd = videoDur
		}
		if winEnd-winStart < 0.5 {
			winEnd = winStart + 0.5
		}

		// Count how many targets share this anchor
		groupStart := m.targetIdx
		groupEnd := m.targetIdx
		for k := mi + 1; k < len(matched); k++ {
			if matched[k].anchorIdx == aj {
				groupEnd = matched[k].targetIdx
			} else {
				break
			}
		}
		groupLen := groupEnd - groupStart + 1

		// Distribute proportionally by character length
		totalChars := 0
		charLens := make([]int, groupLen)
		for k := 0; k < groupLen; k++ {
			cl := len([]rune(fixed[groupStart+k].Text))
			charLens[k] = cl
			totalChars += cl
		}
		available := winEnd - winStart - float64(groupLen-1)*innerGap
		if available < float64(groupLen)*0.25 {
			available = float64(groupLen) * 0.25
		}
		cursor := winStart
		for k := 0; k < groupLen; k++ {
			idx := groupStart + k
			ratio := 1.0 / float64(groupLen)
			if totalChars > 0 {
				ratio = float64(charLens[k]) / float64(totalChars)
			}
			dur := ratio * available
			if dur < 0.25 {
				dur = 0.25
			}
			end := cursor + dur
			if end > winEnd-0.05 {
				end = winEnd - 0.05
			}
			if end <= cursor {
				end = cursor + 0.05
			}
			fixed[idx].Start = cursor
			fixed[idx].End = end
			cursor = end + innerGap
		}
	}

	// Phase 3 — interpolate unmatched entries between matched anchors
	for gi, m := range matched {
		if gi == 0 {
			// entries before the first match: extend backwards
			prevStart := fixed[m.targetIdx].Start
			if m.targetIdx > 0 {
				// extend backwards from the first match using its start with fallback
				for k := 0; k < m.targetIdx; k++ {
					t := prevStart - float64(m.targetIdx-k)*0.5
					if t < 0 {
						t = 0
					}
					fixed[k].Start = t
					fixed[k].End = t + 0.5
				}
			}
			continue
		}
		prevM := matched[gi-1]
		prevEnd := fixed[prevM.targetIdx].End
		currStart := fixed[m.targetIdx].Start

		// Interpolate entries between prevM and m
		between := m.targetIdx - prevM.targetIdx - 1
		if between > 0 && currStart > prevEnd+0.01 {
			dur := currStart - prevEnd
			perEntry := dur / float64(between)
			for k := 0; k < between; k++ {
				idx := prevM.targetIdx + 1 + k
				s := prevEnd + float64(k)*perEntry
				e := s + perEntry*0.9
				fixed[idx].Start = s
				fixed[idx].End = e
			}
		}
	}

	// Phase 4 — entries after the last match
	lastM := matched[len(matched)-1]
	lastEnd := fixed[lastM.targetIdx].End
	for i := lastM.targetIdx + 1; i < nTarget; i++ {
		s := lastEnd + float64(i-lastM.targetIdx)*0.25
		e := s + 0.5
		if videoDur > 0 && e > videoDur {
			e = videoDur
		}
		fixed[i].Start = s
		fixed[i].End = e
		lastEnd = e
	}

	expanded := expandGeminiDubTextMatchedEntries(fixed, fullEntries, sortedAnchors, cleanFull, cleanAnchor, minOverlap, videoDur)
	if len(expanded) > 0 {
		fixed = expanded
	}

	// Final monotonicity pass
	last := 0.0
	for i := 0; i < len(fixed); i++ {
		if fixed[i].Start < last {
			fixed[i].Start = last + 0.02
		}
		if fixed[i].End <= fixed[i].Start {
			fixed[i].End = fixed[i].Start + 0.5
		}
		last = fixed[i].End
	}

	return fixed, nil
}

func expandGeminiDubTextMatchedEntries(entries, fullEntries, sortedAnchors []geminiDubSRTEntry, cleanFull, cleanAnchor []string, minOverlap int, videoDur float64) []geminiDubSRTEntry {
	if len(entries) == 0 || len(entries) != len(fullEntries) || len(sortedAnchors) == 0 {
		return entries
	}
	expanded := make([]geminiDubSRTEntry, 0, len(entries))
	for i, entry := range entries {
		spanStart, spanEnd := geminiDubAnchorSpan(cleanFull[i], cleanAnchor, minOverlap)
		parts := splitGeminiDubSentences(entry.Text)
		spanCount := spanEnd - spanStart + 1
		if spanCount <= 1 || len(parts) <= 1 || len(parts) > spanCount {
			expanded = append(expanded, entry)
			continue
		}
		for partIdx, part := range parts {
			aj := spanStart + partIdx
			start := sortedAnchors[aj].Start
			var end float64
			if aj+1 < len(sortedAnchors) {
				end = sortedAnchors[aj+1].Start
			} else {
				end = sortedAnchors[aj].End
				if videoDur > 0 && videoDur > start {
					end = videoDur
				}
			}
			if end <= start {
				end = start + 0.3
			}
			expanded = append(expanded, geminiDubSRTEntry{
				Index: len(expanded) + 1,
				Text:  part,
				Start: start,
				End:   end,
			})
		}
	}
	for i := range expanded {
		expanded[i].Index = i + 1
	}
	return expanded
}

func geminiDubAnchorSpan(fullClean string, cleanAnchors []string, minOverlap int) (int, int) {
	start := -1
	end := -1
	for j, anchorClean := range cleanAnchors {
		if chineseOverlapScore(fullClean, anchorClean) >= minOverlap/2 {
			if start == -1 {
				start = j
			}
			end = j
			continue
		}
		if start != -1 {
			break
		}
	}
	return start, end
}

// cleanChineseText returns only CJK unified ideograph characters
// and alphanumerics from s, lowercased.
func cleanChineseText(s string) string {
	var sb strings.Builder
	for _, r := range s {
		if (r >= 0x4e00 && r <= 0x9fff) || unicode.IsLetter(r) || unicode.IsDigit(r) {
			sb.WriteRune(unicode.ToLower(r))
		}
	}
	return sb.String()
}

// chineseOverlapScore counts the number of unique runes shared between
// two cleaned Chinese-text strings.
func chineseOverlapScore(s1, s2 string) int {
	r1 := []rune(s1)
	r2 := []rune(s2)
	if len(r1) == 0 || len(r2) == 0 {
		return 0
	}
	set2 := make(map[rune]bool)
	for _, r := range r2 {
		set2[r] = true
	}
	score := 0
	for _, r := range r1 {
		if set2[r] {
			score++
		}
	}
	return score
}
func distributeGeminiDubTimingByAnchors(anchors, targets []geminiDubSRTEntry, videoDur float64) []geminiDubSRTEntry {
	if len(anchors) == 0 || len(targets) == 0 {
		return nil
	}

	// Sort anchors by start time (and index as tiebreaker for stability)
	sortedAnchors := append([]geminiDubSRTEntry(nil), anchors...)
	sort.SliceStable(sortedAnchors, func(i, j int) bool {
		if sortedAnchors[i].Start == sortedAnchors[j].Start {
			return sortedAnchors[i].Index < sortedAnchors[j].Index
		}
		return sortedAnchors[i].Start < sortedAnchors[j].Start
	})

	nTarget := len(targets)
	fixed := make([]geminiDubSRTEntry, nTarget)
	const innerGap = 0.05

	// Map each target entry to an anchor window by proportional index.
	// When anchors == targets length, this gives a perfect 1:1 mapping.
	for i := 0; i < nTarget; i++ {
		j := (i * len(sortedAnchors)) / nTarget
		if j >= len(sortedAnchors) {
			j = len(sortedAnchors) - 1
		}
		fixed[i] = geminiDubSRTEntry{
			Index: i + 1,
			Text:  targets[i].Text,
		}
	}

	// Assign timing per anchor window, then distribute among its targets
	type groupInfo struct{ start, length int }
	groups := make([]groupInfo, 0, len(sortedAnchors))
	start := 0
	for j := 0; j < len(sortedAnchors); j++ {
		// Count how many fixed entries map to this anchor
		count := 0
		for i := start; i < nTarget; i++ {
			want := (i * len(sortedAnchors)) / nTarget
			if want != j {
				break
			}
			count++
		}
		if count > 0 {
			groups = append(groups, groupInfo{start: start, length: count})
			start += count
		}
	}
	// In case some targets were left unassigned (rounding)
	if start < nTarget && len(groups) > 0 {
		groups[len(groups)-1].length += nTarget - start
	}

	for gi, g := range groups {
		aj := gi
		if aj >= len(sortedAnchors) {
			aj = len(sortedAnchors) - 1
		}
		winStart := sortedAnchors[aj].Start

		var winEnd float64
		if aj+1 < len(sortedAnchors) {
			winEnd = sortedAnchors[aj+1].Start
		} else {
			winEnd = sortedAnchors[aj].End
			if videoDur > 0 && videoDur > winStart {
				winEnd = videoDur
			}
		}
		if winEnd <= winStart {
			winEnd = winStart + 1.0
		}
		if videoDur > 0 && winEnd > videoDur {
			winEnd = videoDur
		}
		if winEnd-winStart < 0.5 {
			winEnd = winStart + 0.5
		}

		if g.length == 1 {
			idx := g.start
			fixed[idx].Start = winStart
			fixed[idx].End = winEnd
			continue
		}

		// Distribute proportionally by character length
		totalChars := 0
		charLens := make([]int, g.length)
		for k := 0; k < g.length; k++ {
			cl := len([]rune(fixed[g.start+k].Text))
			charLens[k] = cl
			totalChars += cl
		}

		available := winEnd - winStart - float64(g.length-1)*innerGap
		if available < float64(g.length)*0.25 {
			available = float64(g.length) * 0.25
		}

		cursor := winStart
		for k := 0; k < g.length; k++ {
			idx := g.start + k
			ratio := 1.0 / float64(g.length)
			if totalChars > 0 {
				ratio = float64(charLens[k]) / float64(totalChars)
			}
			dur := ratio * available
			if dur < 0.25 {
				dur = 0.25
			}
			end := cursor + dur
			if end > winEnd-0.05 {
				end = winEnd - 0.05
			}
			if end <= cursor {
				end = cursor + 0.05
			}
			fixed[idx].Start = cursor
			fixed[idx].End = end
			cursor = end + innerGap
		}
	}

	// Final monotonicity pass: fix any negative gaps from rounding
	lastEnd := 0.0
	for i := 0; i < nTarget; i++ {
		if fixed[i].Text == "" {
			fixed[i].Text = targets[i].Text
		}
		if fixed[i].Start < lastEnd {
			fixed[i].Start = lastEnd + 0.02
		}
		if fixed[i].End <= fixed[i].Start {
			fixed[i].End = fixed[i].Start + 0.5
		}
		lastEnd = fixed[i].End
	}

	return fixed
}

func validateGeminiDubFixedEntries(entries []geminiDubSRTEntry) error {
	lastEnd := 0.0
	for i, entry := range entries {
		if strings.TrimSpace(entry.Text) == "" {
			return fmt.Errorf("fixed SRT has empty text at entry %d", i+1)
		}
		if entry.Start < lastEnd-0.001 {
			return fmt.Errorf("fixed SRT is non-monotonic at entry %d", i+1)
		}
		if entry.End <= entry.Start {
			return fmt.Errorf("fixed SRT has non-positive duration at entry %d", i+1)
		}
		lastEnd = entry.End
	}
	return nil
}

func getGeminiDubVideoDuration(videoPath string) float64 {
	cmd := exec.Command("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", videoPath)
	out, err := cmd.Output()
	if err != nil {
		return 0
	}
	dur, err := strconv.ParseFloat(strings.TrimSpace(string(out)), 64)
	if err != nil || dur <= 0 {
		return 0
	}
	return dur
}

func capGeminiDubTimeline(entries []geminiDubSRTEntry, videoDur float64) []geminiDubSRTEntry {
	if videoDur <= 0 {
		return entries
	}
	maxDur := videoDur + 60 // allow up to 60s of freeze at end
	cutoff := -1
	for i, entry := range entries {
		if entry.Start >= maxDur {
			cutoff = i
			break
		}
		if entry.End > maxDur {
			entry.End = maxDur
			entries[i] = entry
		}
	}
	if cutoff >= 0 {
		entries = entries[:cutoff]
	}
	if len(entries) == 0 {
		return entries
	}
	if entries[len(entries)-1].End > maxDur {
		e := entries[len(entries)-1]
		e.End = maxDur
		entries[len(entries)-1] = e
	}
	return entries
}

func capGeminiDubEntriesToDuration(entries []geminiDubSRTEntry, videoDur float64) []geminiDubSRTEntry {
	if videoDur <= 0 || len(entries) == 0 {
		return entries
	}
	maxEnd := entries[len(entries)-1].End
	if maxEnd <= videoDur+1.0 {
		return entries
	}
	scale := (videoDur - 0.25) / maxEnd
	last := 0.0
	for i, e := range entries {
		ns := e.Start * scale
		ne := e.End * scale
		if ns < last+0.03 {
			ns = last + 0.03
		}
		dur := ne - ns
		if dur < 0.5 {
			dur = 0.5
		}
		ne = ns + dur
		if ne > videoDur-0.02 {
			ne = videoDur - 0.02
		}
		if ne <= ns {
			ne = ns + 0.05
		}
		entries[i].Start = ns
		entries[i].End = ne
		last = ne
	}
	return entries
}

func splitGeminiDubLongEntries(entries []geminiDubSRTEntry) []geminiDubSRTEntry {
	split := make([]geminiDubSRTEntry, 0, len(entries))
	for _, entry := range entries {
		parts := splitGeminiDubSentences(entry.Text)
		if len(parts) <= 1 || entry.End-entry.Start < 1.0 {
			split = append(split, entry)
			continue
		}

		gap := 0.05
		available := entry.End - entry.Start - gap*float64(len(parts)-1)
		if available < 0.35*float64(len(parts)) {
			split = append(split, entry)
			continue
		}

		totalChars := 0
		charLens := make([]int, len(parts))
		for i, part := range parts {
			charLens[i] = len([]rune(part))
			totalChars += charLens[i]
		}

		cursor := entry.Start
		for i, part := range parts {
			ratio := 1.0 / float64(len(parts))
			if totalChars > 0 {
				ratio = float64(charLens[i]) / float64(totalChars)
			}
			dur := ratio * available
			if dur < 0.35 {
				dur = 0.35
			}
			end := cursor + dur
			if i == len(parts)-1 || end > entry.End {
				end = entry.End
			}
			if end <= cursor {
				end = cursor + 0.05
			}
			split = append(split, geminiDubSRTEntry{Index: len(split) + 1, Text: part, Start: cursor, End: end})
			cursor = end + gap
		}
	}
	return split
}

func splitGeminiDubSentences(text string) []string {
	text = strings.TrimSpace(text)
	if text == "" {
		return nil
	}

	parts := make([]string, 0, 2)
	var b strings.Builder
	runes := []rune(text)
	for i, r := range runes {
		b.WriteRune(r)
		if !isGeminiDubSentenceEnd(r) {
			continue
		}
		nextIsBoundary := i == len(runes)-1 || unicode.IsSpace(runes[i+1]) || runes[i+1] == '"' || runes[i+1] == '“' || runes[i+1] == '”'
		if !nextIsBoundary {
			continue
		}
		part := strings.TrimSpace(b.String())
		part = strings.Trim(part, "\"“” ")
		if part != "" {
			parts = append(parts, part)
		}
		b.Reset()
	}
	if rest := strings.TrimSpace(b.String()); rest != "" {
		rest = strings.Trim(rest, "\"“” ")
		if rest != "" {
			parts = append(parts, rest)
		}
	}
	return parts
}

func isGeminiDubSentenceEnd(r rune) bool {
	switch r {
	case '.', '!', '?', '。', '！', '？':
		return true
	default:
		return false
	}
}

type geminiDubSRTEntry struct {
	Index int
	Text  string
	Start float64
	End   float64
}

func parseGeminiDubSRT(content string) ([]geminiDubSRTEntry, error) {
	content = strings.ReplaceAll(content, "\r\n", "\n")
	blocks := strings.Split(strings.TrimSpace(content), "\n\n")
	entries := make([]geminiDubSRTEntry, 0, len(blocks))
	for _, block := range blocks {
		lines := strings.Split(strings.TrimSpace(block), "\n")
		if len(lines) < 3 {
			continue
		}
		idx, err := strconv.Atoi(strings.TrimSpace(lines[0]))
		if err != nil {
			continue
		}
		m := srtTimeLineRE.FindStringSubmatch(lines[1])
		if m == nil {
			continue
		}
		start, err := parseSRTTimeParts(m[1:5])
		if err != nil {
			return nil, err
		}
		end, err := parseSRTTimeParts(m[5:9])
		if err != nil {
			return nil, err
		}
		text := strings.TrimSpace(strings.Join(lines[2:], " "))
		if text == "" {
			continue
		}
		entries = append(entries, geminiDubSRTEntry{Index: idx, Text: text, Start: start, End: end})
	}
	return entries, nil
}

func parseSRTTimeParts(parts []string) (float64, error) {
	if len(parts) != 4 {
		return 0, fmt.Errorf("invalid srt time parts")
	}
	vals := make([]int, 4)
	for i, part := range parts {
		v, err := strconv.Atoi(part)
		if err != nil {
			return 0, err
		}
		vals[i] = v
	}
	return float64(vals[0]*3600+vals[1]*60+vals[2]) + float64(vals[3])/1000, nil
}

func sanitizeGeminiDubEntries(entries []geminiDubSRTEntry, timelineMode string) []geminiDubSRTEntry {
	cleaned := make([]geminiDubSRTEntry, 0, len(entries))
	lastEnd := 0.0
	for i, entry := range entries {
		text := strings.TrimSpace(entry.Text)
		if text == "" {
			continue
		}

		start := entry.Start
		if start < lastEnd {
			start = lastEnd + 0.05
		}

		end := entry.End
		if timelineMode != "overlay" {
			dur := estimateGeminiDubDuration(text)
			if originalDur := entry.End - entry.Start; originalDur >= 1.5 && originalDur < dur {
				dur = originalDur
			}
			if i+1 < len(entries) {
				nextStart := entries[i+1].Start
				if nextStart > start+0.35 && start+dur >= nextStart {
					dur = nextStart - start - 0.05
				}
			}
			if dur < 0.8 {
				dur = 0.8
			}
			if dur > 12.0 {
				dur = 12.0
			}
			end = start + dur
		} else if end <= start {
			end = start + 0.5
		}

		cleaned = append(cleaned, geminiDubSRTEntry{Text: text, Start: start, End: end})
		lastEnd = end
	}
	return cleaned
}

func validateGeminiDubCleanEntries(entries []geminiDubSRTEntry) error {
	if len(entries) == 0 {
		return fmt.Errorf("clean SRT has no usable entries")
	}
	lastEnd := 0.0
	for i, entry := range entries {
		if entry.Start < lastEnd {
			return fmt.Errorf("clean SRT is non-monotonic at entry %d", i+1)
		}
		if entry.End <= entry.Start {
			return fmt.Errorf("clean SRT has non-positive duration at entry %d", i+1)
		}
		if entry.End-entry.Start > 12.0 {
			return fmt.Errorf("clean SRT entry %d is too long: %.2fs", i+1, entry.End-entry.Start)
		}
		lastEnd = entry.End
	}
	return nil
}

func estimateGeminiDubDuration(text string) float64 {
	runes := []rune(text)
	dur := float64(len(runes)) * 0.09
	if dur < 1.5 {
		return 1.5
	}
	if dur > 12.0 {
		return 12.0
	}
	return dur
}

func formatGeminiDubSRT(entries []geminiDubSRTEntry) string {
	var b strings.Builder
	for i, entry := range entries {
		fmt.Fprintf(&b, "%d\n%s --> %s\n%s\n\n", i+1, formatSRTTime(entry.Start), formatSRTTime(entry.End), entry.Text)
	}
	return b.String()
}

func formatSRTTime(seconds float64) string {
	if seconds < 0 {
		seconds = 0
	}
	millis := int(seconds*1000 + 0.5)
	h := millis / 3600000
	millis %= 3600000
	m := millis / 60000
	millis %= 60000
	s := millis / 1000
	ms := millis % 1000
	return fmt.Sprintf("%02d:%02d:%02d,%03d", h, m, s, ms)
}

func containsCJK(text string) bool {
	for _, r := range text {
		if unicode.In(r, unicode.Han) {
			return true
		}
	}
	return false
}

func ensureGeminiDubVideo(req GeminiDubRequest) error {
	videoPath := filepath.Join(req.Workdir, req.Video)
	if fileExists(videoPath) {
		return nil
	}
	if strings.TrimSpace(req.Input) == "" {
		return fmt.Errorf("input video not found: %s", videoPath)
	}

	// Use f2 for Douyin, yt-dlp for other platforms
	if strings.Contains(req.Input, "douyin.com") {
		return downloadDouyinVideoForGeminiDub(req.Input, videoPath)
	}

	baseName := strings.TrimSuffix(req.Video, filepath.Ext(req.Video))
	outputPattern := filepath.Join(req.Workdir, baseName+".%(ext)s")
	cmd := exec.Command(
		"yt-dlp",
		"--no-playlist",
		"-f", "bv*+ba/b",
		"--merge-output-format", "mp4",
		"-o", outputPattern,
		req.Input,
	)
	cmd.Stdout = os.Stderr
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return err
	}
	if !fileExists(videoPath) {
		return fmt.Errorf("downloaded video not found: %s", videoPath)
	}
	return nil
}

func downloadDouyinVideoForGeminiDub(inputURL string, videoPath string) error {
	// Find f2 binary
	f2Path, err := exec.LookPath("f2")
	if err != nil {
		localF2Path := "./bin/f2"
		if _, err := os.Stat(localF2Path); err == nil {
			f2Path = localF2Path
		} else {
			localF2PathWindows := ".\\bin\\f2.exe"
			if _, err := os.Stat(localF2PathWindows); err == nil {
				f2Path = localF2PathWindows
			} else {
				return fmt.Errorf("f2 binary not found in PATH or ./bin/f2")
			}
		}
	}

	// Create temp download directory
	tmpDir := filepath.Join(filepath.Dir(videoPath), "f2_tmp")
	if err := os.MkdirAll(tmpDir, 0755); err != nil {
		return fmt.Errorf("create f2 temp dir failed: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	// Read cookie if available
	cookiePath := filepath.Join(".", "cookie_string.txt")
	var cookie string
	if cookieData, err := os.ReadFile(cookiePath); err == nil {
		cookie = strings.TrimSpace(string(cookieData))
	}

	// Build f2 command
	args := []string{"dy", "-u", inputURL, "--mode", "one", "-p", tmpDir, "-f", "false", "-v", "false", "-d", "false"}
	if cookie != "" {
		args = append(args, "-k", cookie)
	}

	cmd := exec.Command(f2Path, args...)
	fmt.Fprintf(os.Stderr, "[f2] downloading Douyin video...\n")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("f2 download failed: %w\n%s", err, string(output))
	}

	// Walk tmpDir to find mp4
	var mp4File string
	filepath.WalkDir(tmpDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if !d.IsDir() && strings.HasSuffix(strings.ToLower(path), ".mp4") {
			mp4File = path
			return io.EOF
		}
		return nil
	})
	if mp4File == "" {
		return fmt.Errorf("no mp4 file found in f2 output directory")
	}

	// Move to target
	if err := os.Rename(mp4File, videoPath); err != nil {
		return fmt.Errorf("move video failed: %w", err)
	}

	fmt.Fprintf(os.Stderr, "[f2] video saved to %s\n", videoPath)
	return nil
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func geminiDubFailure(req GeminiDubRequest, code string, err error, start time.Time) pipeline.Response {
	return pipeline.Response{
		OK:      false,
		Stage:   pipeline.StageGeminiDub,
		Workdir: req.Workdir,
		TaskID:  req.TaskID,
		Error: &pipeline.Error{
			Kind:      pipeline.ErrorKindRetryable,
			Code:      code,
			Message:   err.Error(),
			Retryable: true,
		},
		DurationMS: time.Since(start).Milliseconds(),
	}
}

func renderStageFromCommand(name string) pipeline.Stage {
	if name == "render-horizontal" {
		return pipeline.StageRenderHorizontal
	}
	return pipeline.StageRenderVertical
}

func newFlagSet(name string) *flag.FlagSet {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	return fs
}

func hasHelpArg(args []string) bool {
	for _, arg := range args {
		if isHelpArg(arg) {
			return true
		}
	}
	return false
}

func isHelpArg(arg string) bool {
	return arg == "-h" || arg == "--help" || arg == "help"
}

func responseWithError(resp pipeline.Response, err error) pipeline.Response {
	if err == nil {
		return resp
	}
	if resp.Error != nil {
		return resp
	}
	resp.OK = false
	resp.Error = &pipeline.Error{
		Kind:      pipeline.ErrorKindRetryable,
		Code:      "command_failed",
		Message:   err.Error(),
		Retryable: true,
	}
	return resp
}
