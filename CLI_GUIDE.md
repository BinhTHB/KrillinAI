# Hướng dẫn sử dụng KrillinAI CLI (Lồng tiếng & Phụ đề Video)

KrillinAI cung cấp giao diện dòng lệnh (CLI) mạnh mẽ để tự động tải video, nhận diện giọng nói (Whisper), dịch phụ đề (Gemini + DeepL fallback), phát sinh giọng nói lồng tiếng (Gemini Live/Edge-TTS) và ghép khớp trục thời gian video (Segment Freezing).

---

## 1. Thiết lập môi trường nhanh
Trước khi chạy CLI, xuất biến môi trường cần thiết (trên Git Bash Windows):

```bash
export GOOGLE_API_KEY="AIzaSy..."
```

---

## 2. Cách chạy mặc định (Rút gọn tối đa)
Sử dụng lệnh `pipeline` để chạy nhanh từ URL video đầu vào ra video lồng tiếng Việt cuối cùng. Mặc định pipeline sẽ dùng:

- Phụ đề dịch đích בלבד (`target-only`)
- TTS bằng Gemini Live (`--provider gemini`)
- Làm mờ phụ đề gốc và chèn phụ đề dịch (`blur`)

```bash
# Git Bash / Linux / macOS
go run ./cmd/cli pipeline 'YOUR_VIDEO_URL' --workdir tasks/my-task
./krillinai-cli.exe pipeline 'YOUR_VIDEO_URL' --workdir tasks/my-task

# Windows cmd.exe / PowerShell: dùng dấu nháy kép, không dùng dấu nháy đơn; dùng .\ thay vì ./
go run ./cmd/cli pipeline "YOUR_VIDEO_URL" --workdir tasks/my-task
.\krillinai-cli.exe pipeline "YOUR_VIDEO_URL" --workdir tasks/my-task
```

**Kết quả đầu ra sẽ nằm tại:**
`tasks/my-task/controlled_gemini_live/final.mp4`

---

## 3. Lưu ý Windows cmd.exe / PowerShell

Nếu chạy trong `E:\projects\KrillinAI>` bằng cmd.exe hoặc PowerShell:

- Không dùng dấu nháy đơn `'...'` cho URL. Dùng dấu nháy kép `"..."` hoặc không nháy nếu URL không có ký tự đặc biệt.
- Không dùng `./krillinai-cli.exe`. Dùng `.\krillinai-cli.exe`.
- Nếu URL Douyin bị yt-dlp báo `is not a valid URL`, nguyên nhân thường là URL được truyền kèm cả dấu nháy đơn do chạy trong cmd.exe.

Ví dụ đúng:

```powershell
.\krillinai-cli.exe pipeline "https://www.douyin.com/video/7513809997889834277" --workdir tasks/my-task
```

---

## 4. Các cờ cấu hình chi tiết (Customization)

Khi cần tùy biến sâu quy trình dịch thuật và lồng tiếng, bạn có thể truyền thêm các tham số sau vào lệnh `pipeline` hoặc `gemini-dub`:

| Cờ (Flag) | Giá trị mặc định | Giải thích |
| :--- | :--- | :--- |
| `--workdir <dir>` | *Tự động sinh theo thời gian* | Thư mục làm việc cho tác vụ hiện tại. |
| `--outputs <list>` | `target-only,tts,blur` | Đầu ra pipeline: phụ đề dịch đích, TTS, và làm mờ phụ đề gốc. |
| `--provider <name>` | `gemini` | Nhà cung cấp TTS: `gemini`, `hybrid`, hoặc `edge`. |
| `--model <model>` | `gemini-3.1-flash-live-preview` | Model dùng cho Gemini Live TTS API. |
| `--voice <voice>` | `Aoede` | Giọng đọc Gemini: `Aoede` (nữ), `Fenrir` (nam), `Kore`, `Puck`, `Charon`. |
| `--speed <factor>` | `2.1` | Hệ số tăng tốc âm thanh cục bộ (FFmpeg). |
| `--voice-volume <n>` | `1.6` | Hệ số khuếch đại âm lượng giọng lồng tiếng. |
| `--bg-volume <n>` | `0.15` | Hệ số âm lượng của nhạc nền gốc (mix ở mức 15%). |
| `--timeline-mode <m>` | `overlay` | Chế độ dòng thời gian: `overlay` giữ timeline gốc; `voiceover` cho phép giọng đọc tràn an toàn. |
| `--origin-lang <lang>`| `zh` | Ngôn ngữ gốc của video đầu vào (ví dụ: `zh`, `en`, `ja`). |
| `--target-lang <lang>`| `vi` | Ngôn ngữ dịch đích của phụ đề và giọng nói. |
| `--caption-source <s>`| `whisper` | Nguồn lấy phụ đề gốc: `whisper`, `manual`, `auto`, hoặc `any`. |
| `--output-dir <dir>` | `controlled_gemini_live` | Tên thư mục chứa kết quả nằm trong `--workdir`. |

### Ví dụ lệnh chạy cấu hình chi tiết đầy đủ:

```bash
go run ./cmd/cli pipeline 'https://example.com/video.mp4' \
  --workdir tasks/special-task \
  --origin-lang zh \
  --target-lang vi \
  --outputs target-only,tts,blur \
  --provider gemini \
  --model gemini-3.1-flash-live-preview \
  --voice Aoede \
  --speed 2.1 \
  --voice-volume 1.8 \
  --bg-volume 0.12 \
  --timeline-mode overlay
```

---

## 5. Các lệnh đơn lẻ (Chạy từng bước)
KrillinAI CLI hỗ trợ chạy bóc tách từng giai đoạn nhỏ để kiểm tra dữ liệu trung gian:

### Bước A: Tạo phụ đề từ video
Sinh phụ đề dịch thuật và lưu vào thư mục làm việc:
```bash
go run ./cmd/cli subtitle 'YOUR_VIDEO_URL_OR_PATH' \
  --workdir tasks/my-task \
  --origin-lang zh \
  --target-lang vi
```
*Kết quả:* Phụ đề tiếng Việt được lưu tại `tasks/my-task/target_language_srt.srt`.

### Bước B: Phát sinh giọng lồng tiếng (TTS) từ SRT có sẵn
Tạo giọng lồng tiếng rời từ file phụ đề đã dịch:
```bash
go run ./cmd/cli tts \
  --workdir tasks/my-task \
  --input-srt target_language_srt.srt \
  --voice vi-VN-HoaiAnNeural
```

### Bước C: Render ghép sub cứng vào video
```bash
go run ./cmd/cli render-horizontal \
  --workdir tasks/my-task \
  --video origin_video.mp4 \
  --subtitle target_language_srt.srt
```
