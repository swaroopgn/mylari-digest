#!/home/box/.config/save-to-spotify/kokoro-env/bin/python3
"""Kokoro narration for one episode, per the save-to-spotify pipeline.

Usage: make_audio.py EPISODE_SLUG
Reads  episodes/<slug>/segments.json  ({"segments":[{"title","text","sources"}...]})
Writes episodes/<slug>/audio.mp3, episodes/<slug>/chapters.json (chapter start times),
       episodes/<slug>/script.txt (transcript = joined segment text)
Voice / speed / pause / pronunciations come from show.json ("kokoro" block).
Run with the Kokoro venv python (path from `save-to-spotify --json tts status` -> kokoro_python).
"""
import glob, json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent
SHOW = json.loads((ROOT / "show.json").read_text())
K = SHOW.get("kokoro", {})
VOICE, SPEED = K.get("voice", "af_heart"), float(K.get("speed", 1.0))
GAP_S, LEAD_S = float(K.get("gap_seconds", 0.8)), 0.25


def find_model(pattern):
    cfg = os.path.expanduser("~/.config/save-to-spotify")
    for d in (os.path.join(cfg, "kokoro-env"), cfg):
        hits = glob.glob(os.path.join(d, pattern))
        if hits:
            return sorted(hits)[-1]
    sys.exit(f"No {pattern} found - run: save-to-spotify tts setup")


def speakable(text):
    for a, b in SHOW.get("pronunciations", {}).items():
        text = text.replace(a, b)
    return text.replace("\u2014", ", ").replace("\u2013", "-")


def main(slug):
    d = ROOT / "episodes" / slug
    segs = json.loads((d / "segments.json").read_text())["segments"]
    kokoro = Kokoro(find_model("kokoro-v*.onnx"), find_model("voices-v*.bin"))
    chunks, chapters, cursor = [], [], 0
    sr = 24000
    for i, s in enumerate(segs):
        samples, sr = kokoro.create(speakable(s["text"]), voice=VOICE, speed=SPEED, lang="en-us")
        lead = np.zeros(int(sr * LEAD_S), dtype=np.float32) if i == 0 else np.zeros(0, dtype=np.float32)
        gap = np.zeros(int(sr * GAP_S), dtype=np.float32) if i < len(segs) - 1 else np.zeros(int(sr * 1.0), dtype=np.float32)
        chapters.append({"title": s["title"], "start_time_ms": int(round(cursor / sr * 1000)), "sources": s.get("sources", [])})
        seg = np.concatenate([lead, samples.astype(np.float32), gap])
        chunks.append(seg)
        cursor += len(seg)
        print(f"[{i}] {s['title']}: {len(samples)/sr:.1f}s", flush=True)
    wav = Path(tempfile.gettempdir()) / f"mylari_{slug}.wav"
    sf.write(wav, np.concatenate(chunks), sr)
    ep = json.loads((d / "episode.json").read_text())
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", str(wav),
                           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1",
                           "-c:a", "libmp3lame", "-b:a", "128k", "-id3v2_version", "3",
                           "-metadata", f"title={ep.get('spotify_title', ep['title'])}",
                           "-metadata", f"artist={SHOW['author']}", "-metadata", f"album={SHOW['title']}",
                           "-metadata", "genre=Podcast", str(d / "audio.mp3")])
    total_ms = int(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                  "-of", "csv=p=0", str(d / "audio.mp3")], text=True)) * 1000)
    assert chapters[-1]["start_time_ms"] < total_ms
    (d / "chapters.json").write_text(json.dumps({"duration_ms": total_ms, "chapters": chapters}, indent=2))
    (d / "script.txt").write_text("\n\n".join(s["text"] for s in segs) + "\n")
    print(f"audio.mp3 {total_ms/1000:.1f}s ({total_ms/60000:.2f} min)")


if __name__ == "__main__":
    main(sys.argv[1])
