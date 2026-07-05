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
