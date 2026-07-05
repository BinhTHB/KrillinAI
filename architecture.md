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

---

# 🏗️ Kiến trúc tổng thể

```text
                          +----------------+
                          |     USER       |
                          +-------+--------+
                                  |
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
                                  |
                                  ▼
                     GitHub Repository Dispatch
                                  |
                                  ▼
        =====================================================
                GITHUB ACTIONS WORKFLOW #1 (INGEST)
        =====================================================

        Download Video
                │
                ▼

        Extract Audio (FFmpeg)

                │
                ▼

        Convert WAV → FLAC

                │
                ▼

        Upload Assets

                │
                ▼

             Cloudflare R2
        (Video + Audio + Metadata)

                │
                ▼

     Trigger Workflow #2

        =====================================================
                GITHUB ACTIONS WORKFLOW #2 (AI)
        =====================================================

          Download Audio From R2

                │
                ▼

        Wake HuggingFace Space
        (Health Check Until Ready)

                │
                ▼

          Faster-Whisper
        base CPU/int8 default

                │
                ▼

         Word Timestamp SRT

                │
                ▼

       Anchor Alignment Engine

                │
                ▼

       Gemini Translation

                │
                ▼

      Gemini Voice / Edge TTS

                │
                ▼

      Upload Generated Assets

                │
                ▼

             Cloudflare R2

                │
                ▼

     Trigger Workflow #3

        =====================================================
              GITHUB ACTIONS WORKFLOW #3 (RENDER)
        =====================================================

      Download Assets

                │
                ▼

        Blur Original Subtitle

                │
                ▼

         FFmpeg Rendering

                │
                ▼

      Upload Final Video

         ┌───────────────┐
         │ Google Drive  │
         └──────┬────────┘
                │
                ▼
        Telegram Bot Reply

                │
                ▼
               USER
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

## 3. GitHub Actions Workflow #1 – Ingest

Chỉ chịu trách nhiệm chuẩn bị dữ liệu.

### Các bước

1. Download video
2. Trích xuất audio
3. Chuyển WAV → FLAC
4. Upload lên Cloudflare R2
5. Gửi Workflow #2

Không chạy AI.

---

## 4. Cloudflare R2

Đóng vai trò Storage trung gian.

Lưu:

* Video gốc
* Audio FLAC
* Metadata
* Subtitle
* Audio TTS
* Video render

Ưu điểm:

* Không cần truyền file lớn giữa các workflow
* Có thể resume
* Retry dễ dàng

---

## 5. GitHub Actions Workflow #2 – AI Pipeline

Workflow AI hoàn toàn độc lập.

### Bước 1

Đánh thức HuggingFace Space.

Health Check:

```
GET /health

status = loading

↓

status = ready
```

Chỉ gửi audio sau khi model load xong.

---

### Bước 2

Speech Recognition

Free-tier mặc định:

```
base CPU/int8
```

Nếu cần chất lượng tối đa trên GPU trả phí:

```
base / distil-large-v3 (GPU)
```

---

### Bước 3

Sinh Word Timestamp

Ví dụ:

```
Xin
00:00:01.24

chào

00:00:01.58

mọi

00:00:01.80
```

---

### Bước 4

Anchor Alignment

Thực hiện:

* Merge
* Split
* Anchor Lock
* Boundary Balance

Đảm bảo subtitle dịch khớp tuyệt đối.

---

### Bước 5

Gemini Translation

Input:

```
Chinese SRT
```

Output:

```
Vietnamese SRT
```

---

### Bước 6

Gemini Voice / Edge-TTS

Sinh:

```
Vietnamese Audio
```

---

### Bước 7

Upload kết quả lên R2.

---

## 6. HuggingFace Space

Đóng vai trò AI Worker.

Chỉ thực hiện:

```
Audio

↓

Speech Recognition

↓

Timestamp
```

Không render.

Không dịch.

Không chạy FFmpeg.

---

## 7. GitHub Actions Workflow #3 – Render

Workflow cuối.

### Download

Tải:

* Video
* Subtitle
* Audio TTS

Từ R2.

---

### FFmpeg

Thực hiện:

* Blur subtitle cũ
* Overlay subtitle mới
* Replace audio
* Encode H264

---

### Upload

Nếu:

```
< 50MB
```

↓

Telegram

Nếu:

```
> 50MB
```

↓

Google Drive

↓

Telegram gửi link.

---

# 🔄 Retry Strategy

Workflow được tách biệt hoàn toàn.

```
Workflow 1

↓

Workflow 2

↓

Workflow 3
```

Nếu Workflow 3 lỗi:

Chỉ chạy lại Workflow 3.

Không cần:

* Download lại video
* Chạy Whisper lại
* Dịch lại
* Sinh TTS lại

---

# 📊 Luồng dữ liệu

```
Telegram

↓

Cloudflare Worker

↓

Workflow #1

↓

Cloudflare R2

↓

Workflow #2

↓

Cloudflare R2

↓

Workflow #3

↓

Google Drive

↓

Telegram
```

---

# 🧠 AI Stack

## Speech Recognition

* Faster-Whisper
* base CPU/int8 (mặc định Free Tier)
* base / distil-large-v3 (GPU) (tuỳ chọn GPU trả phí)

---

## Translation

* Google Gemini

---

## Text To Speech

* Gemini Voice
* Edge-TTS

---

## Video Processing

* FFmpeg

---

# 📈 Ưu điểm của kiến trúc

* Serverless hoàn toàn
* Chi phí gần bằng 0 USD
* Retry từng workflow
* Không truyền file lớn trực tiếp giữa các job
* Dễ mở rộng nhiều AI Worker
* Không phụ thuộc vào một GitHub Runner duy nhất
* Dễ thay thế ASR, Translator hoặc TTS trong tương lai
* Có thể bổ sung hàng đợi (Queue) hoặc nhiều AI Worker mà không cần thay đổi kiến trúc tổng thể

---

# 🚀 Khả năng mở rộng

Trong tương lai có thể bổ sung:

* Cloudflare Queues
* Nhiều HuggingFace Space chạy song song
* Worker Pool cho AI
* GPU Worker khi cần
* Hỗ trợ nhiều ngôn ngữ
* Dashboard quản lý tiến trình
* Hệ thống cache subtitle và audio để tái sử dụng

---

# 📌 Kết luận

KrillinAI v2 áp dụng mô hình **Serverless Event-Driven Pipeline**, trong đó mỗi workflow đảm nhận một giai đoạn độc lập của quá trình xử lý.

Việc sử dụng **Cloudflare Workers**, **GitHub Actions**, **Cloudflare R2**, **Hugging Face Spaces**, **Google Gemini**, **FFmpeg** và **Google Drive** giúp hệ thống đạt được sự cân bằng giữa **chi phí thấp**, **khả năng mở rộng**, **khả năng chịu lỗi** và **hiệu năng**, đồng thời tạo nền tảng để nâng cấp lên kiến trúc quy mô lớn hơn trong tương lai mà không cần thay đổi thiết kế cốt lõi.
