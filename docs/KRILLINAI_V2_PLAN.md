# 🚀 Kế hoạch triển khai KrillinAI v2 - Serverless Production Architecture

Dựa trên tài liệu phân tích kiến trúc `architecture.md`, dưới đây là kế hoạch chi tiết để triển khai hệ thống **End-to-End Multimodal Serverless Pipeline** tối ưu chi phí và tăng khả năng chịu lỗi.

---

## 🏗️ Phân tích Kiến trúc KrillinAI v2

Hệ thống chuyển đổi từ mô hình monolith/chạy local sang mô hình **Event-Driven Serverless**, chia nhỏ quy trình xử lý video thành 3 Workflows độc lập giao tiếp qua **Cloudflare R2**:

1. **API Gateway & Telegram Bot**: Tiếp nhận request từ client, chuyển tiếp qua webhook đến Cloudflare Workers để dispatch GitHub Actions.
2. **Workflow #1 (Ingest)**: Tải video, tách audio và nén dạng FLAC đẩy lên R2.
3. **Workflow #2 (AI Pipeline)**: Nhận dạng giọng nói (Faster-Whisper trên Hugging Face), đồng bộ trục thời gian (Anchor Alignment), dịch thuật (Gemini), lồng tiếng TTS (Gemini Voice / Edge-TTS).
4. **Workflow #3 (Render)**: Blur sub cũ, overlay sub/audio mới bằng FFmpeg và đẩy kết quả về Google Drive / Telegram.

---

## 📅 Kế hoạch triển khai chi tiết (Action Plan)

### Pha 1: Thiết lập hạ tầng & Lưu trữ (Storage & Cloud Providers)
- [ ] **Cloudflare R2**:
  - Tạo R2 Bucket làm bộ nhớ lưu trữ trung gian.
  - Cấu hình API tokens (`Access Key`, `Secret Key`, `Endpoint URL`).
- [ ] **Hugging Face Space**:
  - Triển khai ứng dụng Fast API bọc `faster-whisper` (`distil-large-v3` / `large-v3` int8).
  - Cung cấp route `/health` để kiểm tra trạng thái hoạt động.
- [ ] **Google Drive API**:
  - Thiết lập Service Account và cấu hình credentials để upload video dung lượng lớn (>50MB).

### Pha 2: Xây dựng API Gateway & Dispatcher (Cloudflare Workers)
- [ ] Phát triển Cloudflare Workers xử lý Telegram Webhook.
- [ ] Xác thực link video gửi lên.
- [ ] Kích hoạt Workflow #1 qua GitHub REST API (`repository_dispatch`).

### Pha 3: Xây dựng luồng GitHub Actions (3 Workflows)
- [ ] **Workflow #1 (`ingest.yml`)**:
  - Download video (sử dụng yt-dlp/downloader).
  - Trích xuất audio và convert sang FLAC.
  - Upload audio và metadata lên R2.
  - Trigger Workflow #2.
- [ ] **Workflow #2 (`ai_pipeline.yml`)**:
  - Kiểm tra trạng thái HF Space đến khi sẵn sàng.
  - Gọi HF Space để lấy SRT kèm Word Timestamp.
  - Thực hiện Alignment (Anchor Alignment Engine).
  - Dịch phụ đề qua Gemini Translation.
  - Phát sinh âm thanh lồng tiếng bằng Gemini Voice / Edge-TTS.
  - Upload assets lên R2 và trigger Workflow #3.
- [ ] **Workflow #3 (`render.yml`)**:
  - Tải video gốc, subtitle mới và audio TTS từ R2.
  - Chạy FFmpeg blur phụ đề cũ, ghép âm thanh/phụ đề mới.
  - Upload final video lên Google Drive hoặc Telegram.

### Pha 4: Tích hợp, Quản lý lỗi & Logs
- [ ] **Cấu hình cơ chế Retry**: Đảm bảo các workflow có thể trigger lại độc lập từ điểm lỗi (chỉ chạy lại Workflow 3 nếu lỗi render mà không cần dịch/TTS lại).
- [ ] **Hệ thống Logs**: Cập nhật trạng thái xử lý thời gian thực qua Telegram Bot tin nhắn phản hồi cho người dùng.
