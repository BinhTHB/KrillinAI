# Hướng dẫn upstream dự án gốc KrillinAI

Tài liệu này hướng dẫn cách đồng bộ thay đổi từ repository gốc KrillinAI vào fork hiện tại.

## Remote đang dùng

- Fork hiện tại: `origin` -> `https://github.com/BinhTHB/KrillinAI.git`
- Dự án gốc: `upstream` -> `https://github.com/krillinai/KrillinAI.git`
- Nhánh phát triển chính của fork: `master`

## Quy trình đồng bộ upstream

Thực hiện trên nhánh `master` của fork:

```bash
git checkout master
git fetch upstream
git merge upstream/master -X ours -m "merge: merge upstream/master into master, preferring current fork changes on conflict"
git status
git push origin master
```

Khi có conflict, dùng `-X ours` để ưu tiên thay đổi từ fork hiện tại. Cờ này chỉ tự xử lý conflict theo vùng code; sau merge vẫn phải kiểm tra lại bằng `git status` và review các file liên quan.

## Thay đổi đã nhận từ upstream

Lần đồng bộ gần nhất đã merge `upstream/master` vào `master` tại commit `59386d7`.

Các nhóm thay đổi chính từ upstream:

- Thêm nhà cung cấp TTS MiniMax: `pkg/minimax/tts.go`, `pkg/minimax/tts_test.go`, cấu hình liên quan và danh sách voices.
- Thêm registry voices: `internal/voices/voices.go`, `internal/voices/voices_test.go`.
- Thêm updater/version CLI: `internal/updater/updater.go`, `internal/updater/updater_test.go`, `internal/cli/version.go`, cập nhật `cmd/cli/main.go`.
- Cải thiện kiểm tra dependency: `internal/deps/checker.go`, `internal/deps/checker_test.go`.
- Cải thiện render/nhúng subtitle và hỗ trợ tùy chọn subtitle nền tảng: `internal/service/srt_embed.go`, `internal/service/srt_embed_test.go`, `internal/service/render_stage.go`, `static/index.html`.
- Cập nhật handler/task types và pipeline metadata: `internal/handler/subtitle_task.go`, `internal/types/subtitle_task.go`, `internal/pipeline/types.go`.
- Cập nhật tài liệu/cấu hình upstream: `README.md`, `docs/zh/cli.md`, `config/config-example.toml`, `.goreleaser.yaml`.

Tổng quan merge upstream: 27 file thay đổi, khoảng 2.318 dòng thêm và 62 dòng xóa trong phần thay đổi đến từ upstream.
