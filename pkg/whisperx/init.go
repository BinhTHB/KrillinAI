package whisperx

type WhisperXProcessor struct {
	WorkDir   string // 生成中间文件的目录
	Model     string
	EnableGPU bool
}

func NewWhisperXProcessor(model string, enableGPU bool) *WhisperXProcessor {
	return &WhisperXProcessor{
		Model:     model,
		EnableGPU: enableGPU,
	}
}
