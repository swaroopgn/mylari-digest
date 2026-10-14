#!/usr/bin/env python3
"""Vaultcast transcript builder (contract: publish-to-vaultcast SKILL.md, "Transcripts").

Library + CLI. Turns a narrated script plus timing evidence into `{episode-id}.transcript.json`:
  {"version": 1, "episodeId", "title", "blocks": [{"id", "text", "role"?: "heading", "startTimeMs", "endTimeMs"}]}

Timing evidence (seconds on the audio clock):
  * TTS segment lengths: the pipelines concatenate per-paragraph ElevenLabs renders with fixed
    lead/gap/tail silences, so paragraph onsets/ends follow from the cached segment mp3s
    (`tts_spans`), refined to the nearest pause found by ffmpeg silencedetect (`snap_spans`).
  * Pause detection: for audio without a cache, paragraph gaps from silencedetect (`gap_spans`).
Long paragraphs (> 3 sentences or > 60 words) are split into sentence-group blocks; split points
are interpolated by character count and snapped to an in-paragraph pause when one is close.
A heading block is inserted for each timeline chapter (startTimeMs == chapter startTimeMs exactly);
the first spoken block after it starts at the speech onset, at least MIN_HEAD_GAP later.

CLI (Mylari weekly episodes):
  python3 transcript.py <date> [--episode-id 2026-10-14-small-models] [--out PATH]
reads episodes/<date>/{segments.json, chapters.json, audio.mp3, audio.meta.json, .tts-cache/}
and writes episodes/<date>/<episode-id>.transcript.json (validated; exits non-zero on any error).
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

MIN_HEAD_GAP = 0.25        # s between a heading and its first spoken block
SNAP_TOL = 0.45            # s window to snap predicted paragraph edges to a detected pause
SPLIT_TOL = 1.2            # s window to snap an in-paragraph split point to a pause
MAX_SENT, MAX_WORDS = 3, 60
ID_RE = re.compile(r"^[a-z0-9-]+$")
MARKUP_RE = re.compile(r"<[A-Za-z/!][^>]*>|\*\*|__|`|^\s*#|^\s*[-*+]\s|\[[^\]]*\]\([^)]*\)|&[a-z]+;|&#\d+;", re.M)


# ------------------------------------------------------------------ audio helpers
def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)], text=True))


def silences(path, noise="-40dB", d=0.2):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    if len(en) < len(st):
        en.append(duration(path))
    return [(max(0.0, a), b) for a, b in zip(st, en)]


def pcm(path, sr=44100):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "pipe:1"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32), sr


def segment_profile(path, thr_db=-40.0, frame=0.01):
    """(decoded length, leading silence, trailing silence) of one TTS segment, in seconds.
    Decoded length is what the pipelines concatenate, so it is the exact clock contribution."""
    import numpy as np
    x, sr = pcm(path)
    n = int(sr * frame); k = len(x) // n
    if k == 0:
        return len(x) / sr, 0.0, 0.0
    rms = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(axis=1) + 1e-12)
    voiced = np.nonzero(rms > 10 ** (thr_db / 20))[0]
    if not len(voiced):
        return len(x) / sr, 0.0, 0.0
    return len(x) / sr, voiced[0] * frame, max(0.0, len(x) / sr - (voiced[-1] + 1) * frame)


def el_cache_key(voice_id, model, fmt, settings, text):
    return hashlib.sha256(json.dumps([voice_id, model, fmt, settings, text]).encode()).hexdigest()[:24]


def tts_spans(chunk_files, tempo=1.0, lead=0.25, gap=0.8, tail=1.0):
    """chunk_files: per paragraph, the list of cached segment files rendered for it (in order).
    Returns per paragraph (segment_start, speech_onset, speech_end) and the predicted total length."""
    t, out = lead, []
    for i, files in enumerate(chunk_files):
        profs = [segment_profile(f) for f in files]
        total = sum(p[0] for p in profs)
        out.append((t / tempo, (t + profs[0][1]) / tempo, (t + total - profs[-1][2]) / tempo))
        t += total + (gap if i < len(chunk_files) - 1 else tail)
    return out, t / tempo


def snap_spans(spans, sil, tol=SNAP_TOL):
    """Move each predicted onset to the nearest pause end, each end to the nearest pause start."""
    ends = [b for _, b in sil]; starts = [a for a, _ in sil]
    res = []
    for on, off in spans:
        n = min(ends, key=lambda e: abs(e - on)) if ends else on
        m = min(starts, key=lambda s: abs(s - off)) if starts else off
        on2 = n if abs(n - on) <= tol else on
        off2 = m if abs(m - off) <= tol and m > on2 else off
        res.append((on2, off2))
    return res


def gap_spans(sil, n_paras, total, min_gap=0.7, first_onset=None):
    """Paragraph spans from pause detection alone. Returns None when the gap count doesn't match."""
    inner = [s for s in sil if s[1] - s[0] >= min_gap and s[0] > 0.3 and s[1] < total - 0.3]
    if len(inner) != n_paras - 1:
        return None
    lead = [s for s in sil if s[0] <= 0.05]
    on0 = first_onset if first_onset is not None else (lead[0][1] if lead else 0.0)
    trail = [s for s in sil if s[1] >= total - 0.3]
    off_last = trail[0][0] if trail else total
    ons = [on0] + [b for _, b in inner]
    offs = [a for a, _ in inner] + [off_last]
    return list(zip(ons, offs))


# ------------------------------------------------------------------ text helpers
ABBR = r"(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bDr)(?<!\bSt)(?<!\bvs)(?<!\be\.g)(?<!\bi\.e)(?<!\bU\.S)(?<!\bInc)(?<!\bNo)"
SENT_SPLIT = re.compile(ABBR + r"(?<=[.!?])[\"'\u201d\u2019)]?\s+(?=[\"'\u201c\u2018(]?[A-Z0-9])")


def clean(text):
    return " ".join(text.split())


def sentences(par):
    out, last = [], 0
    for m in SENT_SPLIT.finditer(par):
        out.append(par[last:m.start() + len(m.group(0).rstrip())].strip()); last = m.end()
    out.append(par[last:].strip())
    return [s for s in out if s]


def sentence_groups(par, max_sent=MAX_SENT, max_words=MAX_WORDS):
    sents = sentences(par)
    words = [len(s.split()) for s in sents]
    if len(sents) <= max_sent and sum(words) <= max_words:
        return [par]
    n = max(-(-len(sents) // max_sent), -(-sum(words) // max_words))
    n = min(n, len(sents))
    target = sum(words) / n
    groups, cur, cw = [], [], 0
    for i, (s, w) in enumerate(zip(sents, words)):
        left_s, left_g = len(sents) - i, n - len(groups)
        if cur and (len(cur) >= max_sent or cw + w > max_words or (cw >= target * 0.8 and left_g > 1)
                    or left_s < left_g):
            groups.append(cur); cur, cw = [], 0
        cur.append(s); cw += w
    if cur:
        groups.append(cur)
    return [" ".join(g) for g in groups]


def slugify(title, maxlen=40):
    s = re.sub(r"['\u2019]", "", title.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "section"
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0] if "-" in s[:maxlen] else s[:maxlen]
    return s


# ------------------------------------------------------------------ builder
def split_times(groups, on, off, sil, tol=SPLIT_TOL):
    """Times for the sentence groups of one paragraph spoken in [on, off]."""
    if len(groups) == 1:
        return [(on, off)]
    total = sum(len(g) for g in groups)
    inner = [s for s in sil if s[0] > on + 0.3 and s[1] < off - 0.3]
    times, cur, acc, used = [], on, 0, set()
    for g in groups[:-1]:
        acc += len(g)
        est = on + (off - on) * acc / total
        cands = [s for s in inner if abs((s[0] + s[1]) / 2 - est) <= tol and s not in used and s[0] > cur + 0.3]
        if cands:
            s = min(cands, key=lambda s: abs((s[0] + s[1]) / 2 - est)); used.add(s)
            times.append((cur, s[0])); cur = s[1]
        else:
            times.append((cur, est)); cur = est
    times.append((cur, off))
    return times


def build(episode_id, paragraphs, spans=None, chapters=(), title=None, sil=(), duration_s=None,
          assign_tol=0.8):
    """paragraphs: spoken text per paragraph. spans: per paragraph (onset, end) seconds, or None (untimed).
    chapters: [(title, start_ms)] from the episode timeline. Returns (doc, notes)."""
    notes = []
    timed = spans is not None
    spoken = []                                    # dicts: text, start, end (seconds) or no times
    for i, p in enumerate(paragraphs):
        groups = sentence_groups(clean(p))
        if timed:
            on, off = spans[i]
            for g, (a, b) in zip(groups, split_times(groups, on, off, sil)):
                spoken.append({"text": g, "start": a, "end": b, "para": i})
        else:
            for g in groups:
                spoken.append({"text": g, "para": i})
    chapters = sorted(chapters, key=lambda c: c[1])
    if chapters and not timed:
        notes.append("untimed transcript: chapter headings placed by script order is impossible; headings omitted")
        chapters = []
    # attach headings
    heads = {}                                     # spoken index -> chapter
    j = 0
    for c in chapters:
        cs = c[1] / 1000
        while j < len(spoken) and spoken[j]["start"] < cs - assign_tol:
            j += 1
        if j >= len(spoken):
            raise ValueError(f"chapter {c[0]!r} at {c[1]} ms is after the last spoken block")
        if j in heads:
            raise ValueError(f"two chapters before the same block ({heads[j][0]!r}, {c[0]!r})")
        heads[j] = c
        delta = spoken[j]["start"] - cs
        if j > 0 and spoken[j - 1]["para"] == spoken[j]["para"]:
            notes.append(f"chapter {c[0]!r} falls inside a paragraph (placed at a sentence boundary, delta {delta:+.2f}s)")
        elif delta > 2.0:
            notes.append(f"chapter {c[0]!r} starts {delta:.2f}s before its first block")
    blocks, used, slug, n = [], set(), None, 0

    def uid(base):
        k, cand = 1, base
        while cand in used:
            k += 1; cand = f"{base}-part-{k}"
        used.add(cand); return cand

    for i, b in enumerate(spoken):
        if i in heads:
            t, ms = heads[i]
            slug = uid(slugify(t)); n = 0
            blocks.append({"id": slug, "role": "heading", "text": clean(t), "startTimeMs": int(ms)})
            if timed:
                b["start"] = max(b["start"], ms / 1000 + MIN_HEAD_GAP)
        n += 1
        bid = f"{slug}-{n}" if slug else f"p-{n}"
        while bid in used:
            n += 1; bid = f"{slug}-{n}" if slug else f"p-{n}"
        used.add(bid)
        blk = {"id": bid, "text": b["text"]}
        if timed:
            s = int(round(b["start"] * 1000)); e = int(round(b["end"] * 1000))
            if duration_s is not None:
                e = min(e, int(duration_s * 1000))
            blk["startTimeMs"], blk["endTimeMs"] = s, e
        blocks.append(blk)
    doc = {"version": 1, "episodeId": episode_id}
    if title:
        doc["title"] = title
    doc["blocks"] = blocks
    return doc, notes


# ------------------------------------------------------------------ validation
def validate(doc, episode_id, chapters=(), duration_ms=None, raw=None):
    err = []
    if raw is not None:
        if raw.startswith(b"\xef\xbb\xbf"):
            err.append("BOM present")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            err.append("not UTF-8")
    if doc.get("version") != 1: err.append("version != 1")
    if doc.get("episodeId") != episode_id: err.append("episodeId mismatch")
    if "title" in doc and not (isinstance(doc["title"], str) and doc["title"].strip()): err.append("bad title")
    extra = set(doc) - {"version", "episodeId", "title", "blocks"}
    if extra: err.append(f"unknown top-level keys {extra}")
    blocks = doc.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        return err + ["blocks missing/empty"]
    ids, prev = set(), None
    timed = ["startTimeMs" in b for b in blocks]
    heads = []
    for k, b in enumerate(blocks):
        extra = set(b) - {"id", "text", "role", "startTimeMs", "endTimeMs"}
        if extra: err.append(f"{b.get('id')}: unknown keys {extra}")
        bid = b.get("id")
        if not isinstance(bid, str) or not ID_RE.match(bid): err.append(f"bad id {bid!r}")
        if bid in ids: err.append(f"duplicate id {bid}")
        ids.add(bid)
        t = b.get("text")
        if not isinstance(t, str) or not t.strip(): err.append(f"{bid}: empty text")
        elif MARKUP_RE.search(t): err.append(f"{bid}: markup in text")
        role = b.get("role")
        if role not in (None, "heading"): err.append(f"{bid}: bad role")
        if role == "heading": heads.append(b)
        if "startTimeMs" in b:
            s = b["startTimeMs"]
            if not isinstance(s, int) or s < 0: err.append(f"{bid}: bad start")
            if prev is not None and s <= prev: err.append(f"{bid}: start {s} not > previous {prev}")
            prev = s
            if duration_ms is not None and s >= duration_ms: err.append(f"{bid}: start beyond audio")
            if role != "heading":
                e = b.get("endTimeMs")
                if not isinstance(e, int) or e <= s: err.append(f"{bid}: bad end {e}")
                elif duration_ms is not None and e > duration_ms: err.append(f"{bid}: end beyond audio")
        elif "endTimeMs" in b:
            err.append(f"{bid}: end without start")
    spoken_timed = [t for t, b in zip(timed, blocks) if b.get("role") != "heading"]
    if any(spoken_timed) and not all(spoken_timed): err.append("mixed timed/untimed spoken blocks")
    if chapters and any(timed):
        hs = [h["startTimeMs"] for h in heads]
        cs = sorted(int(c[1]) for c in chapters)
        if hs != cs: err.append(f"heading starts {hs} != chapter starts {cs}")
        if [clean(h["text"]) for h in heads] != [clean(c[0]) for c in sorted(chapters, key=lambda c: c[1])]:
            err.append("heading texts != chapter titles")
    if blocks[0].get("role") == "heading" and len(blocks) == 1: err.append("only a heading")
    return err


def write(doc, path):
    data = (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    Path(path).write_bytes(data)
    return data


# ------------------------------------------------------------------ Mylari weekly CLI
def mylari(date, episode_id=None, out=None):
    root = Path(__file__).resolve().parent
    show = json.loads((root / "show.json").read_text())
    d = root / "episodes" / date
    segs = json.loads((d / "segments.json").read_text())["segments"]
    meta = json.loads((d / "audio.meta.json").read_text())
    chap = json.loads((d / "chapters.json").read_text())
    audio = d / "audio.mp3"
    total = duration(audio)
    eid = episode_id or f"{date}-small-models"
    ep = json.loads((d / "episode.json").read_text())
    import datetime as _dt
    _d = _dt.date.fromisoformat(date)
    title = ep.get("vaultcast_title") or f"{show['title']} \u2014 {_d.day} {_d.strftime('%b')}"   # same as the catalog title
    chapters = [(c["title"], c["start_time_ms"]) for c in chap["chapters"]]
    paras = [s["text"] for s in segs]
    sil = silences(audio)
    if meta.get("engine") == "elevenlabs":
        tts = show["tts"]; el = tts["elevenlabs"]

        def speakable(t):
            for a, b in show.get("pronunciations", {}).items():
                t = t.replace(a, b)
            return t.replace("\u2014", ", ").replace("\u2013", "-")
        files = []
        for s in segs:
            f = d / ".tts-cache" / f"el-{el_cache_key(meta['voice_id'], meta['model_id'], el.get('output_format', 'mp3_44100_128'), el.get('voice_settings'), speakable(s['text']))}.mp3"
            if not f.exists():
                sys.exit(f"TTS cache miss for segment {s['title']!r}: cannot time the transcript from segment lengths")
            files.append([f])
        sp, pred = tts_spans(files, tempo=float(meta.get("tempo", 1.0)), gap=float(tts.get("gap_seconds", 0.8)))
        if abs(pred - total) > 1.0:
            sys.exit(f"predicted length {pred:.2f}s != audio {total:.2f}s: segments don't match the audio")
        spans = snap_spans([(on, off) for _, on, off in sp], sil)
    else:  # Kokoro fallback render: per-segment gap pauses
        spans = gap_spans(silences(audio, d=0.5), len(paras), total, min_gap=0.6)
        if spans is None:
            sys.exit("pause count doesn't match the segment count; not writing an unaligned transcript")
    doc, notes = build(eid, paras, spans, chapters, title=title, sil=sil, duration_s=total)
    out = Path(out) if out else d / f"{eid}.transcript.json"
    raw = write(doc, out)
    errs = validate(json.loads(raw), eid, chapters, int(total * 1000), raw)
    for n in notes:
        print("note:", n)
    if errs:
        sys.exit("transcript invalid: " + "; ".join(errs))
    print(f"{out.name}: {len(doc['blocks'])} blocks, timed")
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("date"); ap.add_argument("--episode-id"); ap.add_argument("--out")
    a = ap.parse_args()
    mylari(a.date, a.episode_id, a.out)
