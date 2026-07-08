package service

import (
	"context"
	"errors"
	"fmt"
	"io"
	"krillin-ai/config"
	"krillin-ai/internal/storage"
	"krillin-ai/internal/types"
	"krillin-ai/log"
	"krillin-ai/pkg/util"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"go.uber.org/zap"
)

func (s Service) linkToFile(ctx context.Context, stepParam *types.SubtitleTaskStepParam) error {
	var (
		err    error
		output []byte
	)
	link := stepParam.Link
	audioPath := fmt.Sprintf("%s/%s", stepParam.TaskBasePath, types.SubtitleTaskAudioFileName)
	videoPath := fmt.Sprintf("%s/%s", stepParam.TaskBasePath, types.SubtitleTaskVideoFileName)
	stepParam.TaskPtr.ProcessPct = 3
	if strings.Contains(link, "local:") {
		// 本地文件
		videoPath = strings.ReplaceAll(link, "local:", "")
		cmd := exec.Command(storage.FfmpegPath, "-i", videoPath, "-vn", "-ar", "44100", "-ac", "2", "-ab", "192k", "-f", "mp3", audioPath)
		output, err = cmd.CombinedOutput()
		if err != nil {
			log.GetLogger().Error("generateAudioSubtitles.linkToFile ffmpeg error", zap.Any("step param", stepParam), zap.String("output", string(output)), zap.Error(err))
			return fmt.Errorf("generateAudioSubtitles.linkToFile ffmpeg error: %w", err)
		}
	} else if strings.Contains(link, "youtube.com") {
		var videoId string
		videoId, err = util.GetYouTubeID(link)
		if err != nil {
			log.GetLogger().Error("linkToFile.GetYouTubeID error", zap.Any("step param", stepParam), zap.Error(err))
			return fmt.Errorf("linkToFile.GetYouTubeID error: %w", err)
		}
		stepParam.Link = "https://www.youtube.com/watch?v=" + videoId
		if !stepParam.VttSwitch {
			// 使用更灵活的音频格式选择器，避免 HTTP 403 错误。
			cmdArgs := []string{
				"-f", "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/worst",
				"--extract-audio",
				"--audio-format", "mp3",
				"--audio-quality", "192K",
				"-o", audioPath,
				stepParam.Link,
			}
			if config.Conf.App.Proxy != "" {
				cmdArgs = append(cmdArgs, "--proxy", config.Conf.App.Proxy)
			}
			cmdArgs = appendCookiesArgs(cmdArgs, youtubeCookiesPath)
			if storage.FfmpegPath != "ffmpeg" {
				cmdArgs = append(cmdArgs, "--ffmpeg-location", storage.FfmpegPath)
			}
			cmd := exec.Command(storage.YtdlpPath, cmdArgs...)
			output, err = cmd.CombinedOutput()
			if err != nil {
				log.GetLogger().Error("linkToFile download audio yt-dlp error", zap.Any("step param", stepParam), zap.String("output", string(output)), zap.Error(err))
				return fmt.Errorf("linkToFile download audio yt-dlp error: %w", err)
			}
		}
	} else if strings.Contains(link, "douyin.com") {
		videoId := util.GetDouyinVideoId(link)
		if videoId != "" {
			stepParam.Link = "https://www.douyin.com/video/" + videoId
		}
		if err := downloadDouyinVideoWithF2(stepParam.Link, videoPath, config.Conf.App.Proxy); err != nil {
			log.GetLogger().Error("linkToFile download douyin video with f2 error", zap.Any("step param", stepParam), zap.Error(err))
			return fmt.Errorf("linkToFile download douyin video with f2 error: %w", err)
		}
		// Extract audio from downloaded video
		cmd := exec.Command(storage.FfmpegPath, "-i", videoPath, "-vn", "-ar", "44100", "-ac", "2", "-ab", "192k", "-f", "mp3", audioPath)
		output, err = cmd.CombinedOutput()
		if err != nil {
			log.GetLogger().Error("linkToFile extract audio ffmpeg error", zap.Any("step param", stepParam), zap.String("output", string(output)), zap.Error(err))
			return fmt.Errorf("linkToFile extract audio ffmpeg error: %w", err)
		}
	} else if strings.Contains(link, "bilibili.com") {
		videoId := util.GetBilibiliVideoId(link)
		if videoId == "" {
			return errors.New("linkToFile error: invalid link")
		}
		stepParam.Link = "https://www.bilibili.com/video/" + videoId
		cmdArgs := []string{"-f", "bestaudio[ext=m4a]", "-x", "--audio-format", "mp3", "-o", audioPath, stepParam.Link}
		if config.Conf.App.Proxy != "" {
			cmdArgs = append(cmdArgs, "--proxy", config.Conf.App.Proxy)
		}
		if storage.FfmpegPath != "ffmpeg" {
			cmdArgs = append(cmdArgs, "--ffmpeg-location", storage.FfmpegPath)
		}
		cmd := exec.Command(storage.YtdlpPath, cmdArgs...)
		output, err = cmd.CombinedOutput()
		if err != nil {
			log.GetLogger().Error("linkToFile download audio yt-dlp error", zap.Any("step param", stepParam), zap.String("output", string(output)), zap.Error(err))
			return fmt.Errorf("linkToFile download audio yt-dlp error: %w", err)
		}
	} else {
		log.GetLogger().Info("linkToFile.unsupported link type", zap.Any("step param", stepParam))
		return errors.New("linkToFile error: unsupported link, only support youtube, bilibili, douyin and local file")
	}
	stepParam.TaskPtr.ProcessPct = 6
	asrAudioPath := filepath.Join(stepParam.TaskBasePath, types.AsrMono16kAudioFileName)
	if _, statErr := os.Stat(audioPath); statErr == nil {
		if err = convertAudioForASR(audioPath, asrAudioPath); err != nil {
			return fmt.Errorf("linkToFile convert audio for ASR error: %w", err)
		}
		stepParam.AudioFilePath = asrAudioPath
		log.GetLogger().Info("ASR audio normalized to 16kHz mono PCM WAV", zap.String("src", audioPath), zap.String("dst", asrAudioPath))
	} else {
		stepParam.AudioFilePath = audioPath
		log.GetLogger().Info("No origin_audio.mp3 found, ASR may use YouTube VTT subs instead", zap.String("audioPath", audioPath))
	}

	if !strings.HasPrefix(link, "local:") && !strings.Contains(link, "douyin.com") && stepParam.EmbedSubtitleVideoType != "none" {
		// 需要下载原视频
		cmdArgs := []string{"-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]", "-o", videoPath, stepParam.Link}
		if config.Conf.App.Proxy != "" {
			cmdArgs = append(cmdArgs, "--proxy", config.Conf.App.Proxy)
		}
		if storage.FfmpegPath != "ffmpeg" {
			cmdArgs = append(cmdArgs, "--ffmpeg-location", storage.FfmpegPath)
		}
		cmd := exec.Command(storage.YtdlpPath, cmdArgs...)
		output, err = cmd.CombinedOutput()
		if err != nil {
			log.GetLogger().Error("linkToFile download video yt-dlp error", zap.Any("step param", stepParam), zap.String("output", string(output)), zap.Error(err))
			return fmt.Errorf("linkToFile download video yt-dlp error: %w", err)
		}
	}

	// For Douyin, if video is not needed, clean it up
	// Keep video if OCR is enabled (OCR needs video file to extract hardcoded subtitles)
	if strings.Contains(link, "douyin.com") && stepParam.EmbedSubtitleVideoType == "none" && !config.Conf.App.EnableOcr {
		_ = os.Remove(videoPath)
	}
	stepParam.InputVideoPath = videoPath

	// 更新字幕任务信息
	stepParam.TaskPtr.ProcessPct = 10
	return nil
}

func downloadDouyinVideoWithF2(url string, outputPath string, proxy string) error {
	// Find f2 binary
	f2Path, err := exec.LookPath("f2")
	if err != nil {
		// Try local bin directory
		localF2Path := "./bin/f2"
		if _, err := os.Stat(localF2Path); err == nil {
			f2Path = localF2Path
		} else {
			return fmt.Errorf("f2 binary not found in PATH or ./bin/f2")
		}
	}

	// Create temporary directory for f2 download
	tmpDir := filepath.Join(filepath.Dir(outputPath), "f2_tmp")
	if err := os.MkdirAll(tmpDir, 0755); err != nil {
		return fmt.Errorf("create temp dir failed: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	// Read cookie string from file if exists
	cookiePath := filepath.Join(".", "cookie_string.txt")
	var cookie string
	if cookieData, err := os.ReadFile(cookiePath); err == nil {
		cookie = strings.TrimSpace(string(cookieData))
	}

	// Build f2 command
	args := []string{"dy", "-u", url, "--mode", "one", "-p", tmpDir}
	if cookie != "" {
		args = append(args, "-k", cookie)
	}
	if proxy != "" {
		args = append(args, "-P", proxy)
	}

	cmd := exec.Command(f2Path, args...)
	cmd.Env = append(os.Environ(), "PYTHONUTF8=1", "PYTHONIOENCODING=utf-8")
	output, err := cmd.CombinedOutput()
	log.GetLogger().Info("f2 download output", zap.String("url", url), zap.String("output", string(output)), zap.Error(err))
	if err != nil {
		return fmt.Errorf("f2 download failed: %w, output: %s", err, string(output))
	}

	// Find the downloaded mp4 file (f2 creates douyin/one/<author>/<file>.mp4 structure)
	var mp4File string
	filepath.WalkDir(tmpDir, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // skip errors
		}
		if !d.IsDir() && strings.HasSuffix(strings.ToLower(path), ".mp4") {
			mp4File = path
			return io.EOF // stop walking
		}
		return nil
	})
	if mp4File == "" {
		return fmt.Errorf("no mp4 file found in f2 output directory")
	}

	// Move the found mp4 to outputPath
	if err := os.Rename(mp4File, outputPath); err != nil {
		return fmt.Errorf("move video file failed: %w", err)
	}

	return nil
}

func convertAudioForASR(srcPath, dstPath string) error {
	cmdArgs := []string{
		"-i", srcPath,
		"-vn",
		"-acodec", "pcm_s16le",
		"-ar", "16000",
		"-ac", "1",
		"-y",
		dstPath,
	}
	cmd := exec.Command(storage.FfmpegPath, cmdArgs...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		log.GetLogger().Error("convertAudioForASR ffmpeg conversion failed",
			zap.String("src", srcPath),
			zap.String("dst", dstPath),
			zap.String("output", string(output)),
			zap.Error(err))
		return fmt.Errorf("ffmpeg ASR conversion error: %w, output: %s", err, string(output))
	}
	log.GetLogger().Info("convertAudioForASR succeeded", zap.String("dst", dstPath))
	return nil
}
