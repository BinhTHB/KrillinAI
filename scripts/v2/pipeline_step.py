import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib import request

from config import load_config


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_json(path: str, data: dict) -> None:
    ensure_parent(path)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def download_video(args: argparse.Namespace) -> None:
    if load_config().dry_run:
        ensure_parent(args.out)
        Path(args.out).write_bytes(b"KRILLINAI_DRY_RUN_VIDEO")
        write_json(args.metadata, {"video_url": args.url, "video_path": args.out})
        return

    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is required for real video download")

    subprocess.run(["yt-dlp", "-o", args.out, args.url], check=True)
    write_json(args.metadata, {"video_url": args.url, "video_path": args.out})


def extract_audio(args: argparse.Namespace) -> None:
    if load_config().dry_run:
        ensure_parent(args.audio)
        Path(args.audio).write_bytes(b"KRILLINAI_DRY_RUN_AUDIO")
        return

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for audio extraction")

    ensure_parent(args.audio)
    subprocess.run(
        ["ffmpeg", "-y", "-i", args.video, "-vn", "-ac", "1", "-ar", "16000", args.audio],
        check=True,
    )


def upload_r2(args: argparse.Namespace) -> None:
    cfg = load_config()
    if cfg.dry_run:
        print(json.dumps({"uploaded": True, "key": args.key, "dry_run": True}))
        return

    # TODO: integrate boto3 S3-compatible upload using CF_R2_* env vars.
    raise NotImplementedError("R2 upload placeholder: configure CF_R2_* env vars and integrate boto3")


def download_r2(args: argparse.Namespace) -> None:
    cfg = load_config()
    if cfg.dry_run:
        ensure_parent(args.path)
        Path(args.path).write_text(f"dry-run asset from r2://{args.key}\n", encoding="utf-8")
        return

    # TODO: integrate boto3 S3-compatible download using CF_R2_* env vars.
    raise NotImplementedError("R2 download placeholder: configure CF_R2_* env vars and integrate boto3")


def transcribe(args: argparse.Namespace) -> None:
    cfg = load_config()
    if cfg.dry_run:
        ensure_parent(args.srt)
        Path(args.srt).write_text("1\n00:00:00,000 --> 00:00:01,000\nplaceholder\n", encoding="utf-8")
        return

    if not cfg.hf_space_url:
        raise RuntimeError("HF_SPACE_URL is required")

    # TODO: POST multipart audio to HF Space /transcribe and save SRT response.
    endpoint = cfg.hf_space_url.rstrip("/") + "/transcribe"
    raise NotImplementedError(f"HF Space transcription placeholder: {endpoint}")


def align(args: argparse.Namespace) -> None:
    ensure_parent(args.output)
    source = Path(args.input).read_text(encoding="utf-8")
    # TODO: replace pass-through with Anchor Alignment Engine.
    Path(args.output).write_text(source, encoding="utf-8")


def translate(args: argparse.Namespace) -> None:
    cfg = load_config()
    ensure_parent(args.output)
    source = Path(args.input).read_text(encoding="utf-8")
    if cfg.dry_run:
        Path(args.output).write_text(source.replace("placeholder", "bản dịch mẫu"), encoding="utf-8")
        return

    if not cfg.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required")

    # TODO: call Gemini Translation API with source SRT and save translated SRT.
    raise NotImplementedError("Gemini translation placeholder")


def tts(args: argparse.Namespace) -> None:
    cfg = load_config()
    ensure_parent(args.audio)
    if cfg.dry_run:
        Path(args.audio).write_bytes(b"KRILLINAI_DRY_RUN_TTS")
        return

    # TODO: integrate Gemini Voice or Edge-TTS provider based on env/config.
    raise NotImplementedError("TTS provider placeholder")


def render(args: argparse.Namespace) -> None:
    cfg = load_config()
    ensure_parent(args.output)
    if cfg.dry_run:
        Path(args.output).write_bytes(b"KRILLINAI_DRY_RUN_RENDER")
        return

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for render")

    # TODO: replace with blur-original-subtitle + overlay + audio mux pipeline.
    subprocess.run(["ffmpeg", "-y", "-i", args.video, "-i", args.audio, "-c:v", "copy", "-c:a", "aac", args.output], check=True)


def upload_result(args: argparse.Namespace) -> None:
    cfg = load_config()
    if cfg.dry_run:
        print(json.dumps({"result": args.path, "uploaded": True, "dry_run": True}))
        return

    # TODO: upload <50MB to Telegram, otherwise Google Drive and return link.
    raise NotImplementedError("Result upload placeholder")


def notify(args: argparse.Namespace) -> None:
    cfg = load_config()
    if cfg.dry_run:
        print(json.dumps({"chat_id": args.chat_id, "message": args.message, "dry_run": True}))
        return

    if not cfg.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    endpoint = f"{cfg.telegram_api_url}{cfg.telegram_bot_token}/sendMessage"
    payload = json.dumps({"chat_id": args.chat_id, "text": args.message}).encode("utf-8")
    req = request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=20) as resp:
        print(resp.read().decode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KrillinAI v2 workflow step runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("download-video")
    p.add_argument("--url", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--metadata", required=True)
    p.set_defaults(func=download_video)

    p = sub.add_parser("extract-audio")
    p.add_argument("--video", required=True)
    p.add_argument("--audio", required=True)
    p.set_defaults(func=extract_audio)

    p = sub.add_parser("upload-r2")
    p.add_argument("--path", required=True)
    p.add_argument("--key", required=True)
    p.set_defaults(func=upload_r2)

    p = sub.add_parser("download-r2")
    p.add_argument("--key", required=True)
    p.add_argument("--path", required=True)
    p.set_defaults(func=download_r2)

    p = sub.add_parser("transcribe")
    p.add_argument("--audio", required=True)
    p.add_argument("--srt", required=True)
    p.set_defaults(func=transcribe)

    p = sub.add_parser("align")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=align)

    p = sub.add_parser("translate")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=translate)

    p = sub.add_parser("tts")
    p.add_argument("--input", required=True)
    p.add_argument("--audio", required=True)
    p.set_defaults(func=tts)

    p = sub.add_parser("render")
    p.add_argument("--video", required=True)
    p.add_argument("--subtitle", required=True)
    p.add_argument("--audio", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=render)

    p = sub.add_parser("upload-result")
    p.add_argument("--path", required=True)
    p.set_defaults(func=upload_result)

    p = sub.add_parser("notify")
    p.add_argument("--chat-id", required=True)
    p.add_argument("--message", required=True)
    p.set_defaults(func=notify)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
