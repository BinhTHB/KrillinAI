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
Sử dụng các giá trị cấu hình được thiết lập sẵn trong hệ thống để thực hiện nhanh từ URL video đầu vào ra video lồng tiếng Việt cuối cùng.

```bash
# Sử dụng go run
go run ./cmd/cli gemini-dub 'YOUR_VIDEO_URL' --workdir tasks/my-task --provider gemini

# Hoặc sử dụng file build sẵn (.exe trên Windows)
./krillinai-cli.exe gemini-dub 'YOUR_VIDEO_URL' --workdir tasks/my-task --provider gemini
```

**Kết quả đầu ra sẽ nằm tại:**
`tasks/my-task/controlled_gemini_live/controlled_tts_final.mp4`

---

## 3. Các cờ cấu hình chi tiết (Customization)

Khi cần tùy biến sâu quy trình dịch thuật và lồng tiếng, bạn có thể truyền thêm các tham số sau vào lệnh `gemini-dub`:

| Cờ (Flag) | Giá trị mặc định | Giải thích |
| :--- | :--- | :--- |
| `--workdir <dir>` | *Tự động sinh theo thời gian* | Thư mục làm việc cho tác vụ hiện tại. |
| `--provider <name>` | `edge` | Nhà cung cấp TTS: `gemini`, `hybrid`, hoặc `edge`. |
| `--model <model>` | `gemini-3.1-flash-live-preview` | Model dùng cho Gemini Live TTS API. |
| `--voice <voice>` | `Aoede` | Giọng đọc Gemini: `Aoede` (nữ), `Fenrir` (nam), `Kore`, `Puck`, `Charon`. |
| `--speed <factor>` | `2.1` | Hệ số tăng tốc âm thanh cục bộ (FFmpeg). |
| `--voice-volume <n>` | `1.6` | Hệ số khuếch đại âm lượng giọng lồng tiếng. |
| `--bg-volume <n>` | `0.15` | Hệ số âm lượng của nhạc nền gốc (mix ở mức 15%). |
| `--timeline-mode <m>` | `freeze` | Chế độ dòng thời gian: `freeze` (đóng băng hình chờ tiếng) hoặc `overlay`. |
| `--origin-lang <lang>`| `zh` | Ngôn ngữ gốc của video đầu vào (ví dụ: `zh`, `en`, `ja`). |
| `--target-lang <lang>`| `vi` | Ngôn ngữ dịch đích của phụ đề và giọng nói. |
| `--caption-source <s>`| `whisper` | Nguồn lấy phụ đề gốc: `whisper`, `manual`, `auto`, hoặc `any`. |
| `--output-dir <dir>` | `controlled_gemini_live` | Tên thư mục chứa kết quả nằm trong `--workdir`. |

### Ví dụ lệnh chạy cấu hình chi tiết đầy đủ:

```bash
go run ./cmd/cli gemini-dub 'https://example.com/video.mp4' \
  --workdir tasks/special-task \
  --origin-lang zh \
  --target-lang vi \
  --provider gemini \
  --model gemini-3.1-flash-live-preview \
  --voice Aoede \
  --speed 2.1 \
  --voice-volume 1.8 \
  --bg-volume 0.12 \
  --timeline-mode freeze
```

---

## 4. Các lệnh đơn lẻ (Chạy từng bước)
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
