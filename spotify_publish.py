#!/usr/bin/env python3
"""Save an episode to Spotify (private, user's library) via the save-to-spotify CLI.

Usage: spotify_publish.py EPISODE_SLUG --post-url URL [--dry-run]
 - builds episodes/<slug>/timeline.json (chapters + link companions to each source and to the blog post)
 - builds episodes/<slug>/description.html (summary, blog link, (M:SS) chapters with source links)
 - creates the show once if show.json has no spotify_show_uri (stored back into show.json)
 - uploads audio + cover, pushes the timeline, polls `episodes status` until READY
 - writes spotify_episode_uri / spotify_url into episode.json (so build.py links it on the post page)
Never reuses/touches other shows: it only uses show.json's spotify_show_uri.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = str(Path.home() / ".local/bin/save-to-spotify")


def cli(*args):
    r = subprocess.run([CLI, "--json", *args], capture_output=True, text=True)
    try:
        out = json.loads(r.stdout)
    except Exception:
        sys.exit(f"CLI non-JSON output ({r.returncode}): {r.stdout}\n{r.stderr}")
    if r.returncode != 0 or (isinstance(out, dict) and out.get("error")):
        sys.exit(f"CLI error: {out} {r.stderr}")
    return out


def ts(ms):
    s = ms // 1000
    return f"({s // 60}:{s % 60:02d})"


def build_assets(d, ep, show, post_url):
    ch = json.loads((d / "chapters.json").read_text())
    chapters, total = ch["chapters"], ch["duration_ms"]
    items = []
    for i, c in enumerate(chapters):
        items.append({"chapter": {"title": c["title"], "start_time_ms": c["start_time_ms"]}})
        end = chapters[i + 1]["start_time_ms"] if i + 1 < len(chapters) else total
        links = list(c.get("sources", [])) or [post_url]   # intro / outro point at the blog post
        if i == len(chapters) - 1 and post_url not in links:
            links = [post_url]
        usable = end - c["start_time_ms"] - 1000 * (len(links) + 1)
        slot = max(usable // len(links), 1000)
        for j, u in enumerate(links):
            start = c["start_time_ms"] + 1000 + j * (slot + 1000)
            items.append({"link": {"start_time_ms": start, "duration_ms": slot, "url": u}})
    comps = sorted([list(x.values())[0] for x in items if "chapter" not in x], key=lambda x: x["start_time_ms"])
    for a, b in zip(comps, comps[1:]):
        assert a["start_time_ms"] + a["duration_ms"] <= b["start_time_ms"], "companion overlap"
    assert max(c["start_time_ms"] for c in chapters) < total
    (d / "timeline.json").write_text(json.dumps({"items": items}, indent=2))
    summ = ep["summary"].replace("\u2014", "-")
    parts = [f"<p>{summ}</p>",
             f"<p><b>Read the companion blog post (full summaries, numbers and all source links):</b> <a href='{post_url}'>{post_url}</a></p>"]
    for c in chapters:
        srcs = c.get("sources", [])
        link = "".join(f" - <a href='{u}'>source</a>" for u in srcs)
        parts.append(f"<p>{ts(c['start_time_ms'])} - {c['title']}{link}</p>")
    parts.append(f"<p>{show['title']} - {show['subtitle']}. Narration is synthetic (Kokoro TTS).</p>")
    desc = "".join(parts).replace("\n", " ")
    (d / "description.html").write_text(desc)
    return desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug"); ap.add_argument("--post-url", required=True); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    d = ROOT / "episodes" / a.slug
    show_path = ROOT / "show.json"
    show = json.loads(show_path.read_text())
    ep = json.loads((d / "episode.json").read_text())
    desc = build_assets(d, ep, show, a.post_url)
    print("description chars:", len(desc))
    if a.dry_run:
        return
    if ep.get("spotify_episode_uri"):
        sys.exit(f"episode already saved: {ep['spotify_episode_uri']} (delete it first to re-save)")
    cover = str(ROOT / "cover.jpg")
    if not show.get("spotify_show_uri"):
        out = cli("shows", "create", "--title", show["title"], "--summary", show["description"], "--image", cover,
                  "--language", show.get("language", "en"))
        show["spotify_show_uri"] = out.get("show_uri") or out.get("uri") or out.get("id")
        show_path.write_text(json.dumps(show, indent=2, ensure_ascii=False))
        print("created show:", out)
    out = cli("upload", str(d / "audio.mp3"), "--title", ep.get("spotify_title", ep["title"]), "--summary", desc,
              "--show-id", show["spotify_show_uri"], "--image", cover, "--language", show.get("language", "en"))
    uri = out["episode_uri"]; eid = uri.split(":")[-1]
    ep["spotify_episode_uri"] = uri; ep["spotify_url"] = f"https://open.spotify.com/episode/{eid}"
    (d / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False))
    print("uploaded:", out)
    print("timeline set:", cli("timeline", "set", "--episode-id", uri, "--from-file", str(d / "timeline.json")))
    for _ in range(60):
        st = cli("episodes", "status", uri)
        print("status:", st.get("readiness"), flush=True)
        if st.get("readiness") in ("READY", "FAILED"):
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
