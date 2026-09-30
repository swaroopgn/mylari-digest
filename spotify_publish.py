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


class CLIError(Exception):
    pass


def cli(*args, soft=False):
    """Run the CLI in JSON mode. soft=True raises CLIError instead of exiting (for ambiguous-failure handling)."""
    r = subprocess.run([CLI, "--json", *args], capture_output=True, text=True)
    try:
        out = json.loads(r.stdout)
    except Exception:
        out = {"error": f"non-JSON output ({r.returncode}): {r.stdout} {r.stderr}"}
    if r.returncode != 0 or (isinstance(out, dict) and out.get("error")):
        if soft:
            raise CLIError(str(out))
        sys.exit(f"CLI error: {out} {r.stderr}")
    return out


def find_existing(show_uri, key, value, tries=4):
    """After an ambiguous error (e.g. 504), look for the object the call may have created anyway."""
    for _ in range(tries):
        time.sleep(15)
        if key == "episode":
            for e in cli("episodes", "--show-id", show_uri).get("episodes", []):
                if e.get("title") == value:
                    return e.get("episode_uri") or e.get("uri")
        else:
            for sh in cli("shows").get("shows", []):
                if sh.get("title") == value:
                    return sh.get("show_uri")
    return None


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
    ap.add_argument("--poll-only", action="store_true", help="episode already uploaded: just poll status until READY")
    a = ap.parse_args()
    d = ROOT / "episodes" / a.slug
    show_path = ROOT / "show.json"
    show = json.loads(show_path.read_text())
    ep = json.loads((d / "episode.json").read_text())
    desc = build_assets(d, ep, show, a.post_url)
    print("description chars:", len(desc))
    if a.dry_run:
        return
    if a.poll_only:
        return poll(d, ep, ep["spotify_episode_uri"])
    if ep.get("spotify_episode_uri"):
        sys.exit(f"episode already saved: {ep['spotify_episode_uri']} (use --poll-only, or delete it first to re-save)")
    cover = str(ROOT / "cover.jpg")
    if not show.get("spotify_show_uri"):
        try:
            out = cli("shows", "create", "--title", show["title"], "--summary", show["description"], "--image", cover,
                      "--language", show.get("language", "en"), soft=True)
            show["spotify_show_uri"] = out.get("show_uri") or out.get("uri") or out.get("id")
        except CLIError as e:
            print("show create errored, checking whether it exists anyway:", e)
            show["spotify_show_uri"] = find_existing(None, "show", show["title"]) or sys.exit("show not created")
            out = {"show_uri": show["spotify_show_uri"], "note": "found after ambiguous error"}
        show_path.write_text(json.dumps(show, indent=2, ensure_ascii=False))
        print("created show:", out)
    title = ep.get("spotify_title", ep["title"])
    existing = [e for e in cli("episodes", "--show-id", show["spotify_show_uri"]).get("episodes", []) if e.get("title") == title]
    if existing:
        sys.exit(f"an episode titled {title!r} already exists in the show: {existing[0]} - not uploading again")
    try:   # upload exactly once; never blind-retry
        out = cli("upload", str(d / "audio.mp3"), "--title", title, "--summary", desc,
                  "--show-id", show["spotify_show_uri"], "--image", cover, "--language", show.get("language", "en"), soft=True)
        uri = out["episode_uri"]
    except CLIError as e:
        print("upload errored, checking whether the episode exists anyway:", e, flush=True)
        uri = find_existing(show["spotify_show_uri"], "episode", title)
        if not uri:
            sys.exit("upload failed and no episode found - check the show manually before retrying")
        out = {"episode_uri": uri, "note": "found after ambiguous error"}
    eid = uri.split(":")[-1]
    ep["spotify_episode_uri"] = uri; ep["spotify_url"] = f"https://open.spotify.com/episode/{eid}"
    (d / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False))
    print("uploaded:", out)
    try:   # timeline set is an idempotent PUT, so one retry is safe
        print("timeline set:", cli("timeline", "set", "--episode-id", uri, "--from-file", str(d / "timeline.json"), soft=True))
    except CLIError as e:
        print("timeline set errored, retrying once:", e); time.sleep(10)
        print("timeline set:", cli("timeline", "set", "--episode-id", uri, "--from-file", str(d / "timeline.json")))
    poll(d, ep, uri)


def poll(d, ep, uri):
    for _ in range(60):
        try:
            st = cli("episodes", "status", uri, soft=True)
        except CLIError as e:
            print("status errored (will retry):", e); time.sleep(10); continue
        print("status:", st.get("readiness"), flush=True)
        if st.get("readiness") == "READY":
            ep["spotify_ready"] = True
            (d / "episode.json").write_text(json.dumps(ep, indent=2, ensure_ascii=False))
            break
        if st.get("readiness") == "FAILED":
            sys.exit("episode processing FAILED")
        time.sleep(10)
    else:
        sys.exit("episode not READY after ~10 min - re-run with --poll-only later; "
                 "check `save-to-spotify --json shows get <show>` status")


if __name__ == "__main__":
    main()
