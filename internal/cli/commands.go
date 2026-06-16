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
	Input       string
	Workdir     string
	TaskID      string
	OriginLang  string
	TargetLang  string
	UserLang    string
	CaptionSrc  string
	SRT         string
	Video       string
	OutputDir   string
	Provider    string
	Model       string
	Voice       string
	Speed       string
	Gap         string
	VoiceVolume string
	Python      string
	Script      string
	MaxChunks   string
	KeepCache   bool
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
	srt := fs.String("srt", "target_language_srt_clean.srt", "input translated srt")
	video := fs.String("video", "origin_video.mp4", "input video")
	outputDir := fs.String("output-dir", "controlled_gemini_live", "output directory under workdir")
	provider := fs.String("provider", "gemini", "tts provider")
	model := fs.String("model", "gemini-3.1-flash-live-preview", "gemini live model")
	voice := fs.String("voice", "Aoede", "gemini voice")
	speed := fs.String("speed", "2.1", "local speed-up factor")
	gap := fs.String("gap", "0.02", "gap after each chunk")
	voiceVolume := fs.String("voice-volume", "1.6", "voice volume multiplier")
	python := fs.String("python", "python", "python executable")
	script := fs.String("script", filepath.Join("scripts", "controlled_tts_segment_freezing_dub.py"), "dubbing script")
	maxChunks := fs.String("max-chunks", "", "optional preview limit")
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
			Input:       input,
			Workdir:     resolvedWorkdir,
			TaskID:      *taskID,
			OriginLang:  *originLang,
			TargetLang:  *targetLang,
			UserLang:    *userLang,
			CaptionSrc:  *captionSource,
			SRT:         *srt,
			Video:       *video,
			OutputDir:   *outputDir,
			Provider:    *provider,
			Model:       *model,
			Voice:       *voice,
			Speed:       *speed,
			Gap:         *gap,
			VoiceVolume: *voiceVolume,
			Python:      *python,
			Script:      *script,
			MaxChunks:   *maxChunks,
			KeepCache:   *keepCache,
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
	}
	if strings.TrimSpace(req.MaxChunks) != "" {
		args = append(args, "--max-chunks", req.MaxChunks)
	}
	if req.KeepCache {
		args = append(args, "--keep-cache")
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
	if cjkCount > viCount {
		// Too many CJK — not enough Vietnamese; retranslate using fallback script
		return "", fmt.Errorf("too many untranslated CJK entries (%d vs %d Vietnamese), need to retranslate", cjkCount, viCount)
	}
	if cjkCount > 0 && viCount > 0 {
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
	videoPath := filepath.Join(req.Workdir, req.Video)
	videoDur := getGeminiDubVideoDuration(videoPath)

	cleaned := sanitizeGeminiDubEntries(entries)
	cleaned = capGeminiDubTimeline(cleaned, videoDur)

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

type geminiDubSRTEntry struct {
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
		entries = append(entries, geminiDubSRTEntry{Text: text, Start: start, End: end})
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

func sanitizeGeminiDubEntries(entries []geminiDubSRTEntry) []geminiDubSRTEntry {
	cleaned := make([]geminiDubSRTEntry, 0, len(entries))
	lastEnd := 0.0
	for _, entry := range entries {
		text := strings.TrimSpace(entry.Text)
		if text == "" {
			continue
		}
		dur := entry.End - entry.Start
		estDur := estimateGeminiDubDuration(text)
		if dur < 1.5 || dur > 12.0 {
			dur = estDur
		}

		start := entry.Start
		if start < lastEnd || start-lastEnd > 2.0 {
			start = lastEnd + 0.05
		}

		end := start + dur
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
