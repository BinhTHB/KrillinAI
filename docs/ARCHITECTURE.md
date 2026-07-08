# 🚀 KrillinAI v2 - Serverless Production Architecture (2026)

## Tổng quan

KrillinAI v2 được thiết kế theo mô hình **End-to-End Multimodal Serverless Pipeline**, trong đó mỗi thành phần chỉ đảm nhiệm một nhiệm vụ duy nhất (Single Responsibility).

Mục tiêu của kiến trúc:

* Chi phí gần bằng **0 USD**
* Có thể xử lý video dài
* Retry từng bước khi lỗi
* Dễ mở rộng
* Không cần duy trì VPS chạy 24/7
* Tận dụng tối đa hạ tầng miễn phí
* Logic xử lý đồng bộ 100% giữa local và CI

---

# 🏗️ Kiến trúc tổng thể

```text
                          +----------------+
                          |     USER       |
                          +-------+--------+
                                  |
                         Send Video URL
                                  |
                                  ▼
                     +-------------------------+
                     |     Telegram Bot        |
                     +-----------+-------------+
                                 |
                                 | Webhook
                                 ▼
                   +-----------------------------+
                   |    Cloudflare Workers        |
                   | API Gateway + Dispatcher     |
                   +--------------+--------------+
                                  |
                                  ▼
                     GitHub Repository Dispatch
                                  |
                                  ▼
        =====================================================
                GITHUB ACTIONS WORKFLOW #1 (INGEST)
        =====================================================
        Download Video
                |
                ▼
        Extract Audio (FFmpeg)
                |
                ▼
        Upload Assets to R2
        (Video gốc + Audio FLAC + Metadata)
                |
                ▼
        Trigger Workflow #2 (workflow_dispatch)

        =====================================================
                GITHUB ACTIONS WORKFLOW #2 (GO CLI PIPELINE)
        =====================================================

        Download Video gốc từ R2

                |
                ▼

        Chạy krillinai-cli pipeline "local:video_orig.mp4"
                |
                ├── WhisperX (ASR cục bộ trên runner)
                ├── Subtitle normalization (gom câu)
                ├── Gemini translation
                ├── Gemini Voice / Edge TTS (theo từng câu)
                ├── Blur subtitle gốc + overlay phụ đề dịch
                ├── Ghép audio TTS
                └── FFmpeg render final.mp4
                |
                ▼

        Upload final.mp4 lên R2

                |
                ▼

        Telegram notification (link/video)
```

---

# 📦 Thành phần hệ thống

## 1. Telegram Bot

Chức năng:

* Nhận link video
* Hiển thị trạng thái xử lý
* Trả video hoặc link tải

Không xử lý AI.

---

## 2. Cloudflare Workers

Vai trò:

* API Gateway
* Webhook Receiver
* Validate URL
* Dispatch GitHub Actions

Ưu điểm:

* Luôn hoạt động
* Cold start cực thấp
* Không cần VPS

---

## 3. GitHub Actions Workflow #1 - Ingest

Chỉ chịu trách nhiệm chuẩn bị dữ liệu.

### Các bước

1. Download video gốc từ Telegram URL (yt-dlp + f2 fallback cho Douyin)
2. Trích xuất audio (FFmpeg: FLAC 16kHz mono)
3. Upload `video_orig.mp4` + `audio_orig.flac` + metadata lên Cloudflare R2
4. Gửi `workflow_dispatch` để kích Workflow #2

Không chạy AI.

---

## 4. Cloudflare R2

Đóng vai trò Storage trung gian giữa các workflow.

Lưu:

* `jobs/{job_id}/video_orig.mp4` - Video gốc
* `jobs/{job_id}/audio_orig.flac` - Audio gốc (dự phòng)
* `jobs/{job_id}/metadata.json` - Trạng thái job
* `jobs/{job_id}/video_final.mp4` - Video sau render

Ưu điểm:

* Không cần truyền file lớn giữa các workflow
* Có thể resume
* Retry dễ dàng

---

## 5. GitHub Actions Workflow #2 - Unified Go CLI Pipeline

Workflow duy nhất thực hiện tất cả xử lý AI và render.

### Thiết lập

Trong mỗi lần chạy, workflow tự động:

1. Cài đặt Go, Python, venv, ffmpeg, yt-dlp, WhisperX (venv)
2. Tạo `config/config.toml` từ GitHub Secrets/Variables
3. Build Go CLI: `go build -o krillinai-cli ./cmd/cli`
4. Tải `video_orig.mp4` từ R2 xuống runner

### Pipeline (krillinai-cli pipeline)

```text
local:video_orig.mp4
        |
        ▼
Extract audio
        |
        ▼
WhisperX (model medium, CPU, không GPU)
   - Tạo segments với word-level timestamps
   - Không dùng Hugging Face Space
        |
        ▼
Go subtitle normalization:
   - Parse segments từ WhisperX JSON
   - Merge word-level thành sentence-level
   - Sinh origin_language_srt.srt (câu)
        |
        ▼
Gemini API:
   - Dịch SRT từ ngôn ngữ gốc → tiếng Việt
   - Giữ nguyên cấu trúc cues
        |
        ▼
TTS (mặc định Gemini Voice, fallback Edge-TTS):
   - Sinh audio cho từng cue
   - Căn chỉnh thời gian theo timeline
        |
        ▼
Render:
   - Blur vùng subtitle gốc
   - Overlay phụ đề dịch (ASS)
   - Ghép TTS audio với video
   - FFmpeg: H264 + AAC
        |
        ▼
final.mp4
```

### Kết thúc

1. Upload `final.mp4` lên R2
2. Gửi thông báo Telegram (video nếu ≤ 50MB, presigned URL nếu lớn hơn)

Workflow #2 hoàn toàn độc lập, không phụ thuộc Hugging Face Space hay dịch vụ ASR ngoài.

---

## 6. Workflow #3 - Render (Manual Only)

Workflow cũ chỉ dùng cho fallback thủ công, không được tự động kích hoạt.

Không dùng trong pipeline chính.

---

# 🔄 Chiến lược Retry

Workflow được tách biệt hoàn toàn.

```text
Workflow 1 (Ingest)

    ↓ (workflow_dispatch)

Workflow 2 (Go CLI Pipeline)
```

Nếu Workflow 2 lỗi:

- Chạy lại Workflow 2 (có thể dùng `workflow_dispatch` với cùng `job_id`)
- Workflow 2 tải lại `video_orig.mp4` từ R2 và chạy lại pipeline

Không cần chạy lại Ingest.

---

# 🧠 AI Stack

## Speech Recognition

* WhisperX
* Model: medium (CPU, không GPU)
* Chạy trực tiếp trên GitHub Actions runner
* Không dùng Hugging Face Space

## Translation

* Google Gemini (Gemini 3.1 Flash Lite)

## Text To Speech

* Gemini Voice (mặc định)
* Edge-TTS (fallback)

## Video Processing

* FFmpeg

---

# 📈 Ưu điểm của kiến trúc

* Serverless hoàn toàn
* Chi phí gần bằng 0 USD
* Retry từng workflow
* Không truyền file lớn trực tiếp giữa các job
* **Logic local và CI đồng bộ 100%** - không cần port code giữa Python và Go
* Dễ mở rộng
* Không phụ thuộc vào GPU hay Hugging Face Space free tier
* Dễ debug vì log tập trung trong workflow run

---

# 🚀 Khả năng mở rộng trong tương lai

* Cache WhisperX model trên GitHub Actions (giảm thời gian cài đặt)
* Cloudflare Queues cho load balancing
* Hỗ trợ nhiều ngôn ngữ
* Dashboard quản lý tiến trình
* Cache subtitle và audio để tái sử dụng

---

# 📌 Kết luận

KrillinAI v2 áp dụng mô hình **Serverless Event-Driven Pipeline** với **Go CLI làm single source of truth** cho toàn bộ logic xử lý.

Toàn bộ ASR, dịch, TTS, đồng bộ và render đều đi qua một pipeline Go duy nhất, chạy giống hệt trên local và GitHub Actions. Điều này giúp tránh việc nhân bản logic và đảm bảo mọi cải tiến ở local tự động áp dụng cho Telegram pipeline.

