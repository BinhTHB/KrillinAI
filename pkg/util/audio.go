package util

import (
	"go.uber.org/zap"
	"krillin-ai/internal/storage"
	"krillin-ai/log"
	"os/exec"
	"path/filepath"
	"strings"
)

// ProcessAudio 把音频处理成单声道、16k采样率 PCM WAV (uncompressed)
func ProcessAudio(filePath string) (string, error) {
	if strings.HasSuffix(strings.ToLower(filePath), ".wav") {
		return filePath, nil
	}
	dest := strings.ReplaceAll(filePath, filepath.Ext(filePath), "_mono_16K.wav")
	cmdArgs := []string{"-i", filePath, "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", "-y", dest}
	cmd := exec.Command(storage.FfmpegPath, cmdArgs...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		log.GetLogger().Error("处理音频为16K Mono WAV PCM失败", zap.Error(err), zap.String("audio file", filePath), zap.String("output", string(output)))
		return "", err
	}
	return dest, nil
}
