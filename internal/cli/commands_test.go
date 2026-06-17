package cli

import (
	"context"
	"errors"
	"krillin-ai/internal/pipeline"
	subtitlestyle "krillin-ai/internal/subtitle_style"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestParseSubtitleCommand(t *testing.T) {
	cmd, err := Parse([]string{
		"subtitle",
		"https://www.youtube.com/watch?v=abc",
		"--origin-lang", "en",
		"--target-lang", "zh_cn",
		"--workdir", "tasks/demo",
		"--caption-source", "any",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if cmd.Name != "subtitle" {
		t.Fatalf("Name = %q, want subtitle", cmd.Name)
	}
	if cmd.Subtitle.Input != "https://www.youtube.com/watch?v=abc" {
		t.Fatalf("Input = %q", cmd.Subtitle.Input)
	}
	if cmd.Subtitle.Workdir != "tasks/demo" {
		t.Fatalf("Workdir = %q", cmd.Subtitle.Workdir)
	}
	if !cmd.Subtitle.BilingualTop {
		t.Fatalf("BilingualTop = false, want true by default")
	}
}

func TestParseSubtitleCommandCanPutTargetLanguageOnBottom(t *testing.T) {
	cmd, err := Parse([]string{
		"subtitle",
		"https://www.youtube.com/watch?v=abc",
		"--origin-lang", "en",
		"--target-lang", "zh_cn",
		"--workdir", "tasks/demo",
		"--bilingual-top=false",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if cmd.Subtitle.BilingualTop {
		t.Fatalf("BilingualTop = true, want false when explicitly disabled")
	}
}

func TestParseSubtitleCommandAcceptsSubtitleStyleFile(t *testing.T) {
	cmd, err := Parse([]string{
		"subtitle",
		"local:demo.mp4",
		"--origin-lang", "en",
		"--target-lang", "zh_cn",
		"--workdir", "tasks/demo",
		"--subtitle-style-file", "style.json",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if cmd.SubtitleStyleFile != "style.json" {
		t.Fatalf("SubtitleStyleFile = %q", cmd.SubtitleStyleFile)
	}
}

func TestParseTTSCommandRequiresInputSRT(t *testing.T) {
	_, err := Parse([]string{"tts", "--workdir", "tasks/demo"})
	if err == nil {
		t.Fatalf("Parse() error = nil, want error")
	}
}

func TestParseGeminiDubDefaultsToGeminiProvider(t *testing.T) {
	cmd, err := Parse([]string{"gemini-dub", "https://example.com/video", "--workdir", "tasks/demo"})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if cmd.GeminiDub.Provider != "gemini" {
		t.Fatalf("Provider = %q, want gemini", cmd.GeminiDub.Provider)
	}
	if cmd.GeminiDub.Model != "gemini-3.1-flash-live-preview" {
		t.Fatalf("Model = %q, want gemini live default", cmd.GeminiDub.Model)
	}
	if cmd.GeminiDub.Voice != "Aoede" {
		t.Fatalf("Voice = %q, want Aoede", cmd.GeminiDub.Voice)
	}
	if !cmd.GeminiDub.PreserveCues {
		t.Fatal("PreserveCues should default to true")
	}
}

func TestParseRenderCommandAcceptsSubtitleStyleFile(t *testing.T) {
	cmd, err := Parse([]string{
		"render-horizontal",
		"--workdir", "tasks/demo",
		"--video", "origin.mp4",
		"--subtitle", "bilingual.srt",
		"--subtitle-style-file", "style.json",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if cmd.SubtitleStyleFile != "style.json" {
		t.Fatalf("SubtitleStyleFile = %q", cmd.SubtitleStyleFile)
	}
}

func TestParseRootHelp(t *testing.T) {
	cmd, err := Parse([]string{"--help"})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if !cmd.Help || cmd.Name != "" {
		t.Fatalf("Command = %#v, want root help", cmd)
	}
	help := Help(cmd)
	if !strings.Contains(help, "Usage:") || !strings.Contains(help, "subtitle") {
		t.Fatalf("Help() = %q, want root usage with commands", help)
	}
}

func TestParseSubcommandHelp(t *testing.T) {
	cmd, err := Parse([]string{"subtitle", "--help"})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if !cmd.Help || cmd.Name != "subtitle" {
		t.Fatalf("Command = %#v, want subtitle help", cmd)
	}
	help := Help(cmd)
	if !strings.Contains(help, "Usage:") || !strings.Contains(help, "--origin-lang") {
		t.Fatalf("Help() = %q, want subtitle usage with flags", help)
	}
}

func TestParseCoverCommand(t *testing.T) {
	cmd, err := Parse([]string{
		"cover",
		"--workdir", "tasks/demo",
		"--task-id", "demo",
		"--prompt", "电影感科技封面，醒目中文标题",
		"--size", "1536x1024",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if cmd.Name != "cover" {
		t.Fatalf("Name = %q, want cover", cmd.Name)
	}
	if cmd.Cover.Workdir != "tasks/demo" {
		t.Fatalf("Workdir = %q", cmd.Cover.Workdir)
	}
	if cmd.Cover.Prompt != "电影感科技封面，醒目中文标题" {
		t.Fatalf("Prompt = %q", cmd.Cover.Prompt)
	}
	if cmd.Cover.Size != "1536x1024" {
		t.Fatalf("Size = %q", cmd.Cover.Size)
	}
}

func TestParseCoverCommandRequiresPrompt(t *testing.T) {
	_, err := Parse([]string{"cover", "--workdir", "tasks/demo"})
	if err == nil {
		t.Fatalf("Parse() error = nil, want error")
	}
}

func TestParseCoverCommandHelp(t *testing.T) {
	cmd, err := Parse([]string{"cover", "--help"})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	if !cmd.Help || cmd.Name != "cover" {
		t.Fatalf("Command = %#v, want cover help", cmd)
	}
	help := Help(cmd)
	if !strings.Contains(help, "--prompt") {
		t.Fatalf("Help() = %q, want cover flags", help)
	}
}

func TestHelpDryRunTextDoesNotClaimManifestWrites(t *testing.T) {
	commands := []string{"subtitle", "render-horizontal", "render-vertical"}
	for _, name := range commands {
		cmd, err := Parse([]string{name, "--help"})
		if err != nil {
			t.Fatalf("Parse(%s --help) error = %v", name, err)
		}
		help := Help(cmd)
		if strings.Contains(help, "write manifest") {
			t.Fatalf("%s help still claims dry-run writes manifest:\n%s", name, help)
		}
	}
}

func TestFixGeminiDubSRTTimingUsesOriginTiming(t *testing.T) {
	dir := t.TempDir()
	origin := `1
00:00:00,000 --> 00:00:05,000
一句话

2
00:00:05,000 --> 00:00:10,000
第二句话

3
00:00:10,000 --> 00:00:12,000
第三句话

`
	target := `1
00:00:00,000 --> 00:00:01,000
Câu thứ nhất.

2
00:01:00,000 --> 00:01:01,000
Câu thứ hai dài hơn.

3
00:02:00,000 --> 00:02:01,000
Câu thứ ba.

`
	originPath := filepath.Join(dir, "origin_language_srt.srt")
	inputPath := filepath.Join(dir, "target_language_srt.srt")
	if err := os.WriteFile(originPath, []byte(origin), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(inputPath, []byte(target), 0644); err != nil {
		t.Fatal(err)
	}
	entries, err := parseGeminiDubSRT(target)
	if err != nil {
		t.Fatal(err)
	}

	fixed, err := fixGeminiDubSRTTiming(dir, inputPath, entries, "target_language_srt.srt", 12)
	if err != nil {
		t.Fatal(err)
	}
	if len(fixed) != 3 {
		t.Fatalf("fixed entries = %d, want 3", len(fixed))
	}
	if fixed[0].Start != 0 || fixed[1].Start != 5 || fixed[2].Start != 10 {
		t.Fatalf("starts = %.3f %.3f %.3f, want 0 5 10", fixed[0].Start, fixed[1].Start, fixed[2].Start)
	}
	if _, err := os.Stat(filepath.Join(dir, "target_language_srt.bad.srt")); err != nil {
		t.Fatalf("bad backup not written: %v", err)
	}
	fixedPath := filepath.Join(dir, "target_language_srt_fixed.srt")
	if _, err := os.Stat(fixedPath); err != nil {
		t.Fatalf("fixed SRT not written: %v", err)
	}
}

func TestFixGeminiDubSRTTimingUsesShortOriginWhenLengthsDiffer(t *testing.T) {
	dir := t.TempDir()
	badOrigin := `1
00:00:00,000 --> 00:00:01,000
一

2
00:01:00,000 --> 00:01:01,000
二

3
00:02:00,000 --> 00:02:01,000
三

4
00:03:00,000 --> 00:03:01,000
四

`
	shortOrigin := `1
00:00:00,000 --> 00:00:05,000
第一段

2
00:00:05,000 --> 00:00:10,000
第二段

`
	target := `1
00:00:00,000 --> 00:00:01,000
Một.

2
00:01:00,000 --> 00:01:01,000
Hai.

3
00:00:00,500 --> 00:00:01,500
Ba.

4
00:03:00,000 --> 00:03:01,000
Bốn.

`
	if err := os.WriteFile(filepath.Join(dir, "origin_language_srt.srt"), []byte(badOrigin), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "short_origin_srt.srt"), []byte(shortOrigin), 0644); err != nil {
		t.Fatal(err)
	}
	inputPath := filepath.Join(dir, "target_language_srt.srt")
	if err := os.WriteFile(inputPath, []byte(target), 0644); err != nil {
		t.Fatal(err)
	}
	entries, err := parseGeminiDubSRT(target)
	if err != nil {
		t.Fatal(err)
	}

	fixed, err := fixGeminiDubSRTTiming(dir, inputPath, entries, "target_language_srt.srt", 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(fixed) != 4 {
		t.Fatalf("fixed entries = %d, want 4", len(fixed))
	}
	if fixed[0].Start != 0 || fixed[1].Start <= fixed[0].End || fixed[2].Start != 5 || fixed[3].Start <= fixed[2].End {
		t.Fatalf("unexpected distributed timing: %#v", fixed)
	}
	for i, entry := range fixed {
		if strings.TrimSpace(entry.Text) == "" {
			t.Fatalf("entry %d lost text", i+1)
		}
	}
}

func TestExecuteDryRunSubtitleReturnsJSONReadyResponse(t *testing.T) {
	cmd, err := Parse([]string{
		"subtitle",
		"local:demo.mp4",
		"--origin-lang", "en",
		"--target-lang", "zh_cn",
		"--workdir", t.TempDir(),
		"--dry-run",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	resp := Execute(context.Background(), nil, cmd)
	if !resp.OK {
		t.Fatalf("OK = false, error = %#v", resp.Error)
	}
	if resp.Stage != pipeline.StageSubtitle {
		t.Fatalf("Stage = %s", resp.Stage)
	}
}

func TestExecuteDryRunRenderRejectsInvalidSubtitleStyleFile(t *testing.T) {
	cmd, err := Parse([]string{
		"render-horizontal",
		"--workdir", t.TempDir(),
		"--video", "origin.mp4",
		"--subtitle", "bilingual.srt",
		"--subtitle-style-file", "missing.json",
		"--dry-run",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	resp := Execute(context.Background(), nil, cmd)
	if resp.OK {
		t.Fatalf("OK = true, want false for missing style file")
	}
	if resp.Error == nil || !strings.Contains(resp.Error.Message, "missing.json") {
		t.Fatalf("error = %#v, want missing style file message", resp.Error)
	}
}

func TestExecuteDryRunRenderLoadsSubtitleStyleFile(t *testing.T) {
	dir := t.TempDir()
	stylePath := filepath.Join(dir, "style.json")
	if err := os.WriteFile(stylePath, []byte(`{"horizontal":{"major":{"primary_color":"#FFFFFF"}}}`), 0644); err != nil {
		t.Fatal(err)
	}
	cmd, err := Parse([]string{
		"render-horizontal",
		"--workdir", dir,
		"--video", "origin.mp4",
		"--subtitle", "bilingual.srt",
		"--subtitle-style-file", stylePath,
		"--dry-run",
	})
	if err != nil {
		t.Fatalf("Parse() error = %v", err)
	}
	resp := Execute(context.Background(), nil, cmd)
	if !resp.OK {
		t.Fatalf("OK = false, error = %#v", resp.Error)
	}
	manifestPath := filepath.Join(dir, "krillinai_manifest.json")
	if _, err := os.Stat(manifestPath); !os.IsNotExist(err) {
		t.Fatalf("manifest exists after dry-run: err = %v", err)
	}
}

func TestLoadSubtitleStyleFindsRepoDefaultFromDifferentWorkingDir(t *testing.T) {
	originalWd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	defaultPath, ok, err := findDefaultSubtitleStylePath()
	if err != nil {
		t.Fatalf("findDefaultSubtitleStylePath() error = %v", err)
	}
	if !ok {
		t.Fatal("default subtitle style path not found")
	}
	tempDir := t.TempDir()
	t.Cleanup(func() {
		if err := os.Chdir(originalWd); err != nil {
			t.Fatalf("restore cwd: %v", err)
		}
	})
	if err := os.Chdir(tempDir); err != nil {
		t.Fatal(err)
	}

	style, err := loadSubtitleStyleForCLI("")
	if err != nil {
		t.Fatalf("loadSubtitleStyleForCLI() error = %v", err)
	}
	defaultFile, err := subtitlestyle.LoadOverrideFile(defaultPath)
	if err != nil {
		t.Fatalf("load default file: %v", err)
	}
	if style.Horizontal.Major.PrimaryColor != defaultFile.Horizontal.Major.PrimaryColor {
		t.Fatalf("primary color = %q, want repo default %q", style.Horizontal.Major.PrimaryColor, defaultFile.Horizontal.Major.PrimaryColor)
	}
}

func TestStyleLoadFailureClassifiesDefaultStyleErrorsAsInternal(t *testing.T) {
	err := defaultStyleLoadError(errors.New("broken default style"))
	resp := styleLoadFailure(pipeline.StageRenderHorizontal, "work", "task", err)
	if resp.Error == nil {
		t.Fatal("Error = nil, want style load error")
	}
	if resp.Error.Kind != pipeline.ErrorKindInternal {
		t.Fatalf("Kind = %s, want internal", resp.Error.Kind)
	}
	if resp.Error.Code != "default_subtitle_style_load_failed" {
		t.Fatalf("Code = %q, want default_subtitle_style_load_failed", resp.Error.Code)
	}
}

func TestStyleLoadFailureClassifiesUserStyleErrorsAsUsage(t *testing.T) {
	err := userStyleLoadError(errors.New("missing user style"))
	resp := styleLoadFailure(pipeline.StageRenderHorizontal, "work", "task", err)
	if resp.Error == nil {
		t.Fatal("Error = nil, want style load error")
	}
	if resp.Error.Kind != pipeline.ErrorKindUsage {
		t.Fatalf("Kind = %s, want usage", resp.Error.Kind)
	}
	if resp.Error.Code != "subtitle_style_load_failed" {
		t.Fatalf("Code = %q, want subtitle_style_load_failed", resp.Error.Code)
	}
}
