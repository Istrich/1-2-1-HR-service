import subprocess
import uuid
from pathlib import Path
from app.core.config import TARGET_SAMPLE_RATE, TARGET_BITRATE, CHUNK_DURATION_SECONDS

def run_ffmpeg(args: list[str]) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + args
    subprocess.run(cmd, check=True)

def convert_to_mp3(input_path: Path, output_dir: Path) -> Path:
    output_path = output_dir / f"{uuid.uuid4().hex}.mp3"
    try:
        run_ffmpeg([
            "-i", str(input_path),
            "-ac", "1",
            "-ar", str(TARGET_SAMPLE_RATE),
            "-b:a", TARGET_BITRATE,
            str(output_path),
        ])
    except subprocess.CalledProcessError as e:
        raise ValueError("Не удалось обработать файл — не аудио/видео или повреждён.") from e
    return output_path

def convert_to_playback_mp3(input_path: Path, output_path: Path) -> Path:
    try:
        run_ffmpeg([
            "-i", str(input_path),
            "-ac", "1",
            "-ar", "44100",
            "-b:a", "128k",
            str(output_path),
        ])
    except subprocess.CalledProcessError:
        import shutil
        shutil.copy2(input_path, output_path)
    return output_path

def split_audio_by_time(input_path: Path, output_dir: Path) -> list[Path]:
    pattern = output_dir / (input_path.stem + "_part_%03d.mp3")
    run_ffmpeg([
        "-i", str(input_path),
        "-f", "segment",
        "-segment_time", str(CHUNK_DURATION_SECONDS),
        "-c", "copy",
        str(pattern),
    ])
    parts = sorted(output_dir.glob(input_path.stem + "_part_*.mp3"))
    return parts or [input_path]

def format_hhmmss(total_seconds: float) -> str:
    total_seconds = int(total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"
