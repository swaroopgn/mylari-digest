#!/home/box/.config/save-to-spotify/kokoro-env/bin/python3
"""Narration for one episode, per the save-to-spotify pipeline (per-segment TTS + pauses -> loudnorm -> MP3).

Usage: make_audio.py EPISODE_SLUG [--engine elevenlabs|kokoro] [--out audio.mp3] [--no-fallback]
Reads  episodes/<slug>/segments.json  ({"segments":[{"title","text","sources"}...]})
Writes episodes/<slug>/<out>                 final MP3 (default audio.mp3)
       episodes/<slug>/chapters.json         chapter start times (chapters-<stem>.json if --out isn't audio.mp3)
       episodes/<slug>/<stem>.meta.json      engine / voice / model / characters billed
       episodes/<slug>/script.txt            transcript (joined segment text)
Engine config lives in show.json: "tts" (engine, fallback, gap_seconds, elevenlabs{voice_id, model_id, ...})
and "kokoro" (voice, speed). ElevenLabs reads ELEVENLABS_API_KEY from the environment (never logged).
If ElevenLabs fails (auth, quota, repeated 429/5xx) the WHOLE episode is re-rendered with the fallback engine
so the voice stays consistent. Run with the Kokoro venv python (path: `save-to-spotify --json tts status`).
"""
import argparse, glob, json, os, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path
import numpy as np, soundfile as sf

ROOT = Path(__file__).resolve().parent
SHOW = json.loads((ROOT / "show.json").read_text())
TTS = SHOW.get("tts", {})
GAP_S, LEAD_S, TAIL_S = float(TTS.get("gap_seconds", 0.8)), 0.25, 1.0


class TTSFailed(Exception):
    pass


def speakable(text):
    for a, b in SHOW.get("pronunciations", {}).items():
        text = text.replace(a, b)
    return text.replace("\u2014", ", ").replace("\u2013", "-")


# ------------------------------------------------------------------ engines -> (float32 mono samples, sr, meta)
class KokoroEngine:
    name = "kokoro"

    def __init__(self):
        from kokoro_onnx import Kokoro
        cfg = os.path.expanduser("~/.config/save-to-spotify")

        def find(pattern):
            for d in (os.path.join(cfg, "kokoro-env"), cfg):
                hits = glob.glob(os.path.join(d, pattern))
                if hits:
                    return sorted(hits)[-1]
            raise TTSFailed(f"No {pattern} found - run: save-to-spotify tts setup")
        k = SHOW.get("kokoro", {})
        self.voice, self.speed = k.get("voice", "af_heart"), float(k.get("speed", 1.0))
        self.k = Kokoro(find("kokoro-v*.onnx"), find("voices-v*.bin"))
        self.meta = {"engine": "kokoro", "voice": self.voice, "speed": self.speed}

    def synth(self, text):
        samples, sr = self.k.create(text, voice=self.voice, speed=self.speed, lang="en-us")
        return samples.astype(np.float32), sr


class ElevenLabsEngine:
    name = "elevenlabs"
    SR = 44100

    def __init__(self):
        self.key = os.environ.get("ELEVENLABS_API_KEY")
        if not self.key:
            raise TTSFailed("ELEVENLABS_API_KEY not set")
        c = TTS.get("elevenlabs", {})
        self.voice_id, self.model = c["voice_id"], c.get("model_id", "eleven_multilingual_v2")
        self.fmt = c.get("output_format", "mp3_44100_128")
        self.settings = c.get("voice_settings")
        self.meta = {"engine": "elevenlabs", "voice": c.get("voice_name"), "voice_id": self.voice_id,
                     "model_id": self.model, "character_cost": 0, "text_characters": 0}

    def _request(self, text):
        body = {"text": text, "model_id": self.model}
        if self.settings:
            body["voice_settings"] = self.settings
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}?output_format={self.fmt}"
        for attempt in range(3):
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
                "xi-api-key": self.key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
            try:
                r = urllib.request.urlopen(req, timeout=180)
                data = r.read()
                self.meta["character_cost"] += int(r.headers.get("character-cost") or 0)
                self.meta["text_characters"] += len(text)
                return data
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code in (429, 500, 502, 503, 504) and "quota" not in detail and attempt < 2:
                    time.sleep(5 * (attempt + 1)); continue
                raise TTSFailed(f"ElevenLabs HTTP {e.code}: {detail}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 2:
                    time.sleep(5 * (attempt + 1)); continue
                raise TTSFailed(f"ElevenLabs network error: {e}")

    def synth(self, text):
        import hashlib
        key = hashlib.sha256(json.dumps([self.voice_id, self.model, self.fmt, self.settings, text]).encode()).hexdigest()[:24]
        cache = CACHE_DIR / f"el-{key}.mp3" if CACHE_DIR else None
        if cache and cache.exists():
            mp3 = cache.read_bytes(); self.meta["cached_segments"] = self.meta.get("cached_segments", 0) + 1
        else:
            mp3 = self._request(text)
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True); cache.write_bytes(mp3)
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(self.SR),
                              "pipe:1"], input=mp3, capture_output=True, check=True).stdout
        return np.frombuffer(pcm, dtype=np.float32).copy(), self.SR


CACHE_DIR = None   # set per episode in main(): episodes/<slug>/.tts-cache (paid segments are never re-billed)
ENGINES = {"kokoro": KokoroEngine, "elevenlabs": ElevenLabsEngine}


def render(engine, segs):
    chunks, chapters, cursor, sr = [], [], 0, None
    for i, s in enumerate(segs):
        samples, sr = engine.synth(speakable(s["text"]))
        lead = np.zeros(int(sr * LEAD_S) if i == 0 else 0, dtype=np.float32)
        gap = np.zeros(int(sr * (GAP_S if i < len(segs) - 1 else TAIL_S)), dtype=np.float32)
        chapters.append({"title": s["title"], "start_time_ms": int(round(cursor / sr * 1000)), "sources": s.get("sources", [])})
        seg = np.concatenate([lead, samples, gap]); chunks.append(seg); cursor += len(seg)
        print(f"  [{i}] {s['title']}: {len(samples) / sr:.1f}s", flush=True)
    return np.concatenate(chunks), sr, chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("--engine"); ap.add_argument("--out", default="audio.mp3")
    ap.add_argument("--no-fallback", action="store_true")
    ap.add_argument("--tempo", type=float, help="pitch-preserving speed-up applied after TTS (default: tts.<engine>.tempo or 1.0)")
    a = ap.parse_args()
    d = ROOT / "episodes" / a.slug
    global CACHE_DIR
    CACHE_DIR = d / ".tts-cache"
    segs = json.loads((d / "segments.json").read_text())["segments"]
    order = [a.engine or TTS.get("engine", "kokoro")]
    if not a.no_fallback and TTS.get("fallback") and TTS["fallback"] not in order:
        order.append(TTS["fallback"])
    audio = None
    for name in order:
        try:
            print(f"engine: {name}", flush=True)
            eng = ENGINES[name]()
            audio, sr, chapters = render(eng, segs)
            meta = eng.meta
            break
        except TTSFailed as e:
            print(f"!! {name} failed: {e}", flush=True)
    if audio is None:
        sys.exit("all TTS engines failed")
    tempo = a.tempo or float(TTS.get(meta["engine"], {}).get("tempo", 1.0) if meta["engine"] == "elevenlabs"
                             else SHOW.get("kokoro", {}).get("tempo", 1.0))
    for c in chapters:
        c["start_time_ms"] = int(round(c["start_time_ms"] / tempo))
    meta["tempo"] = tempo
    out = d / a.out
    wav = Path(tempfile.gettempdir()) / f"mylari_{a.slug}_{out.stem}.wav"
    sf.write(wav, audio, sr)
    ep = json.loads((d / "episode.json").read_text())
    subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-i", str(wav),
                           "-af", (f"atempo={tempo}," if abs(tempo - 1) > 1e-3 else "") + "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1",
                           "-c:a", "libmp3lame", "-b:a", "128k", "-id3v2_version", "3",
                           "-metadata", f"title={ep.get('spotify_title', ep['title'])}",
                           "-metadata", f"artist={SHOW['author']}", "-metadata", f"album={SHOW['title']}",
                           "-metadata", "genre=Podcast", str(out)])
    wav.unlink(missing_ok=True)
    total_ms = int(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                  "-of", "csv=p=0", str(out)], text=True)) * 1000)
    assert chapters[-1]["start_time_ms"] < total_ms
    chap_file = d / ("chapters.json" if a.out == "audio.mp3" else f"chapters-{out.stem}.json")
    chap_file.write_text(json.dumps({"duration_ms": total_ms, "chapters": chapters}, indent=2))
    meta.update({"file": out.name, "duration_ms": total_ms, "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    (d / f"{out.stem}.meta.json").write_text(json.dumps(meta, indent=2))
    (d / "script.txt").write_text("\n\n".join(s["text"] for s in segs) + "\n")
    print(f"{out.name}: {total_ms / 1000:.1f}s ({total_ms / 60000:.2f} min) via {meta['engine']}"
          + (f", {meta.get('character_cost')} credits for {meta.get('text_characters')} chars" if meta["engine"] == "elevenlabs" else ""))


if __name__ == "__main__":
    main()
