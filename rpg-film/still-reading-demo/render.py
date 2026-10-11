"""Render a fixed-picture reading sample without modifying the source artwork."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import wave
import zipfile


HERE = Path(__file__).resolve().parent
FILM = HERE.parent
DURATION = 26.5
OUTPUT = "window-still-mambo-demo.mp4"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    image = FILM / "handdrawn-style-review/01-rainy-classroom.png"
    archive = FILM / "narration/mambo/mambo-narration.zip"
    full_timing = json.loads((FILM / "narration/mambo/timings.json").read_text())
    sentences = full_timing["sentences"][:4]
    assert full_timing["sentences"][4]["start_seconds"] == DURATION
    assert sentences[-1]["end_seconds"] < DURATION
    cover = HERE / "cover.png"
    if cover.exists():
        assert sha256(cover) == sha256(image), "Existing cover differs from source"
    else:
        shutil.copyfile(image, cover)
    with zipfile.ZipFile(archive) as z:
        pcm_bytes = z.read("narration.wav")
    with wave.open(io.BytesIO(pcm_bytes), "rb") as source:
        params = source.getparams()
        audio = source.readframes(round(params.framerate * DURATION))
    assert len(audio) == round(params.framerate * DURATION) * params.nchannels * params.sampwidth
    with wave.open(str(HERE / "narration.wav"), "wb") as out:
        out.setparams(params)
        out.writeframes(audio)
    (HERE / "original.txt").write_text("\n".join(s["text"] for s in sentences) + "\n")
    timing = {
        "scope": "original article, first four complete sentences only",
        "complete_article": False,
        "voice_direction": "曼波朗读",
        "duration_seconds": DURATION,
        "speed": 1.0,
        "sentences": sentences,
    }
    (HERE / "timings.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2) + "\n")
    blocks = (FILM / "film-light-rain/subtitles.srt").read_text().strip().split("\n\n")[:4]
    for block, sentence in zip(blocks, sentences):
        assert "".join(block.splitlines()[2:]) == sentence["text"]
    (HERE / "subtitles.srt").write_text("\n\n".join(blocks) + "\n")
    ass_lines = (FILM / "film-light-rain/subtitles.ass").read_text().splitlines()
    chosen = []
    texts = {}
    for line in ass_lines:
        if line.startswith("Title:"):
            line = "Title: 窗 · 固定画面朗读演示 · 前四句"
        if line.startswith("Dialogue:"):
            fields = line.split(",", 9)
            h, m, s = fields[1].split(":")
            start = int(h) * 3600 + int(m) * 60 + float(s)
            if start >= DURATION:
                continue
            texts.setdefault(start, []).append(re.sub(r"\{[^}]*\}", "", fields[9]))
        chosen.append(line)
    for sentence in sentences:
        assert "".join(texts[sentence["start_seconds"]]) == sentence["text"]
    (HERE / "subtitles.ass").write_text("\n".join(chosen) + "\n")
    (HERE / "sources.json").write_text(json.dumps({
        "image": {"path": str(image.relative_to(FILM.parent)), "sha256": sha256(image)},
        "audio_archive": {"path": str(archive.relative_to(FILM.parent)), "sha256": sha256(archive)},
        "reference_url": "https://www.bilibili.com/video/BV13THd6aEH1/",
        "reference_access": "Environment returned proxy 403; video not viewed. Format follows user's description.",
        "picture_motion": "none; one unchanged source image for every video frame",
        "subtitle_layout": "existing large original-text sentence captions; constant bottom shade",
        "voice": "existing Mambo voice, not a clone of the user's voice",
    }, ensure_ascii=False, indent=2) + "\n")


def command():
    return [
        "ffmpeg", "-hide_banner", "-nostdin", "-n",
        "-loop", "1", "-framerate", "24", "-i", "cover.png",
        "-i", "narration.wav",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
        "drawbox=x=0:y=832:w=iw:h=248:color=black@0.30:t=fill,ass=subtitles.ass",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=9",
        "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage", "-crf", "18",
        "-pix_fmt", "yuv420p", "-threads", "4",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", str(DURATION), "-movflags", "+faststart", OUTPUT,
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="prepare deterministic inputs and print the encoder command")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    prepare()
    cmd = command()
    plan = {"cwd": str(HERE), "command": cmd, "duration_seconds": DURATION, "frames": 636,
            "picture_motion": "none", "complete_article": False}
    (HERE / "render-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    with (HERE / "render.log").open("w") as log:
        subprocess.run(cmd, cwd=HERE, stderr=log, check=True)
    print(json.dumps({"output": str(HERE / OUTPUT), "duration_seconds": DURATION}))


if __name__ == "__main__":
    main()
