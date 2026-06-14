import subprocess
from pathlib import Path

def run(cmd):
    print(f"Running: {cmd}")
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        print(f"Error: {r.stderr}")
    return r.returncode == 0

def main():
    wd = Path("tasks/douyin-new")
    
    # 1. Extract and slow down original audio
    # factor = 1.9383 -> atempo = 0.5159 (needs 2 stages of atempo because FFmpeg atempo limit is 0.5 - 2.0. Wait, 0.5159 > 0.5 so single stage is fine)
    run(f'ffmpeg -y -i "{wd}/origin_video.mp4" -vn -filter:a "atempo=0.5159" -acodec pcm_s16le -ar 44100 -ac 2 "{wd}/origin_audio_slow.wav"')
    
    # 2. Mix slow original audio (15%) + TTS (100%)
    # duration is 349.5s
    # Make sure we pad/trim to 349.5s
    pad_samples = int(349.5 * 44100)
    run(f'ffmpeg -y -i "{wd}/origin_audio_slow.wav" -i "{wd}/tts_final_audio.wav" -filter_complex '
        f'"[0:a]volume=0.15,apad=whole_len={pad_samples}[bg];'
        f'[1:a]volume=1.0,apad=whole_len={pad_samples}[voice];'
        f'[bg][voice]amix=inputs=2:duration=first:dropout_transition=0" '
        f'-acodec pcm_s16le "{wd}/mixed_audio.wav"')

if __name__ == "__main__":
    main()
