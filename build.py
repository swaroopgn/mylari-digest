#!/usr/bin/env python3
"""Build the 'Small Models, Real Systems' static site + podcast feed.

Usage:
  python3 build.py cover                      # (re)generate cover art (make_cover.py)
  python3 build.py tts EPISODE_SLUG           # segments.json -> audio.mp3 + chapters.json (make_audio.py, Kokoro)
  python3 build.py build [--base-url URL]     # render site/ (index, episode pages, feed.xml)
  python3 build.py deploy [--base-url URL]    # build, then push source to `main` and site/ to `gh-pages` (GitHub Pages)

Layout:
  show.json                      show-level metadata (title, author, base_url, voice, ...)
  episodes/<slug>/episode.json   episode metadata (title, date, summary, number)
  episodes/<slug>/post.md        companion blog post (Markdown)
  episodes/<slug>/segments.json  spoken script, one segment per chapter (+ chapter title, source URLs)
  episodes/<slug>/script.txt     transcript (written by `tts`)
  episodes/<slug>/chapters.json  chapter start times (written by `tts`)
  episodes/<slug>/audio.mp3      final audio (written by `tts`)
  site/                          generated output - do not edit by hand
"""
import argparse, email.utils, html, json, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xesc

import markdown

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
EPIS = ROOT / "episodes"
SHOW = json.loads((ROOT / "show.json").read_text())
SLUG = "small-models-real-systems"


# ---------------------------------------------------------------- helpers
def duration_seconds(mp3: Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", str(mp3)], text=True)
    return float(out.strip())


def hms(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def load_episodes():
    eps = []
    for d in sorted(EPIS.iterdir()):
        meta = d / "episode.json"
        if not meta.exists():
            continue
        ep = json.loads(meta.read_text())
        ep["dir"] = d
        ep["dt"] = datetime.fromisoformat(ep["date"])
        eps.append(ep)
    eps.sort(key=lambda e: e["dt"], reverse=True)
    return eps


# ---------------------------------------------------------------- cover / audio (delegated)
KOKORO_PY = "/home/box/.config/save-to-spotify/kokoro-env/bin/python3"   # from `save-to-spotify --json tts status`


def cmd_cover(_args=None):
    subprocess.check_call([sys.executable, str(ROOT / "make_cover.py")])


def cmd_tts(args):
    subprocess.check_call([KOKORO_PY, str(ROOT / "make_audio.py"), args.slug])


# ---------------------------------------------------------------- html
CSS = """
:root{--bg:#0e1626;--card:#152036;--fg:#e9edf3;--mut:#9aa7bb;--acc:#ffb03b;--link:#7cc4ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--link)}header.site{border-bottom:1px solid #22304a;padding:18px 0}
.wrap{max-width:820px;margin:0 auto;padding:0 20px}header.site a{color:var(--fg);text-decoration:none;font-weight:700}
header.site .tag{color:var(--mut);font-size:14px;margin-left:8px}
.hero{display:flex;gap:24px;align-items:center;margin:32px 0}.hero img{width:170px;height:170px;border-radius:14px}
h1{font-size:30px;line-height:1.25;margin:.2em 0}h2{font-size:22px;margin-top:2em;border-top:1px solid #22304a;padding-top:1em}
.meta{color:var(--mut);font-size:14px}.player{background:var(--card);border-radius:12px;padding:16px;margin:20px 0}
audio{width:100%}table{border-collapse:collapse;width:100%;font-size:15px}td,th{border:1px solid #2a3a57;padding:6px 8px;text-align:left}
.ep{background:var(--card);border-radius:12px;padding:18px 20px;margin:16px 0}.ep h3{margin:.1em 0}
code{background:#1d2a44;padding:1px 5px;border-radius:4px}details{background:var(--card);border-radius:12px;padding:12px 16px;margin:24px 0}
footer{color:var(--mut);font-size:13px;margin:48px 0 32px;border-top:1px solid #22304a;padding-top:16px}
.badge{display:inline-block;background:var(--acc);color:#1b1b1b;border-radius:6px;padding:1px 8px;font-size:12px;font-weight:700}
"""


def page(title, body, base, depth=0):
    rel = "../" * depth
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{rel}style.css">
<link rel="alternate" type="application/rss+xml" title="{html.escape(SHOW['title'])}" href="{base}/feed.xml">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:image" content="{base}/cover.jpg">
</head><body><header class="site"><div class="wrap"><a href="{rel}index.html">{html.escape(SHOW['title'])}</a>
<span class="tag">{html.escape(SHOW['subtitle'])}</span></div></header>
<main class="wrap">{body}</main>
<footer class="wrap">{html.escape(SHOW['title'])} · by {html.escape(SHOW['author'])} ·
<a href="{rel}feed.xml">Podcast RSS feed</a> · Audio is synthetic narration (neural TTS).</footer></body></html>"""


def cmd_build(args):
    base = (args.base_url or SHOW.get("base_url") or "").rstrip("/")
    if not base:
        sys.exit("need --base-url (or base_url in show.json) for absolute feed URLs")
    SITE.mkdir(exist_ok=True)
    for p in SITE.iterdir():                     # clean contents but keep the dir (a server may be serving it)
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    (SITE / "style.css").write_text(CSS)
    if not (ROOT / "cover.jpg").exists():
        cmd_cover()
    shutil.copy(ROOT / "cover.jpg", SITE / "cover.jpg")
    (SITE / "audio").mkdir()
    eps = load_episodes()
    md = markdown.Markdown(extensions=["tables", "sane_lists"])
    items_xml, cards = [], []
    for ep in eps:
        d, slug = ep["dir"], ep["slug"]
        mp3_name = f"{SLUG}-{slug}.mp3"
        shutil.copy(d / "audio.mp3", SITE / "audio" / mp3_name)
        size = (SITE / "audio" / mp3_name).stat().st_size
        dur = duration_seconds(SITE / "audio" / mp3_name)
        audio_url = f"{base}/audio/{mp3_name}"
        post_url = f"{base}/episodes/{slug}/"
        md.reset()
        post_html = md.convert((d / "post.md").read_text())
        script = (d / "script.txt").read_text().strip()
        transcript = "".join(f"<p>{html.escape(p)}</p>" for p in script.split("\n\n"))
        date_h = ep["dt"].strftime("%A %d %B %Y")
        chap_html = ""
        if (d / "chapters.json").exists():
            rows = []
            for c in json.loads((d / "chapters.json").read_text())["chapters"]:
                t = c["start_time_ms"] // 1000
                src = "".join(f' · <a href="{html.escape(u)}">source</a>' for u in c.get("sources", []))
                rows.append(f"<li><code>{t // 60}:{t % 60:02d}</code> {html.escape(c['title'])}{src}</li>")
            chap_html = "<details open><summary><strong>Chapters</strong></summary><ul>" + "".join(rows) + "</ul></details>"
        spot = ""
        if ep.get("spotify_url") and ep.get("spotify_ready"):   # only link once Spotify reports READY
            spot = f' · <a href="{html.escape(ep["spotify_url"])}">Listen on Spotify</a>'
        body = f"""<p class="meta">Episode {ep['number']} · {date_h} · {hms(dur)[3:]} min</p>
<h1>{html.escape(ep['title'])}</h1>
<div class="player"><audio controls preload="metadata" src="../../audio/{mp3_name}"></audio>
<div class="meta"><a href="../../audio/{mp3_name}">Download MP3</a> · <a href="../../feed.xml">Subscribe (RSS)</a>{spot}</div></div>
{chap_html}
{post_html}
<details><summary><strong>Episode transcript</strong></summary>{transcript}</details>"""
        out = SITE / "episodes" / slug
        out.mkdir(parents=True)
        (out / "index.html").write_text(page(f"{ep['title']} · {SHOW['title']}", body, base, depth=2))
        cards.append(f"""<div class="ep"><div class="meta">Episode {ep['number']} · {date_h} · {hms(dur)[3:]} min</div>
<h3><a href="episodes/{slug}/">{html.escape(ep['title'])}</a></h3><p>{html.escape(ep['summary'])}</p>
<audio controls preload="none" src="audio/{mp3_name}"></audio></div>""")
        desc = f"{ep['summary']} Show notes and sources: {post_url}"
        items_xml.append(f"""    <item>
      <title>{xesc(ep['title'])}</title>
      <description>{xesc(desc)}</description>
      <content:encoded><![CDATA[<p>{html.escape(ep['summary'])}</p><p>Show notes and all source links: <a href="{post_url}">{post_url}</a></p>]]></content:encoded>
      <link>{post_url}</link>
      <guid isPermaLink="false">{SLUG}-{slug}</guid>
      <pubDate>{email.utils.format_datetime(ep['dt'])}</pubDate>
      <enclosure url="{audio_url}" length="{size}" type="audio/mpeg"/>
      <itunes:title>{xesc(ep['title'])}</itunes:title>
      <itunes:summary>{xesc(ep['summary'])}</itunes:summary>
      <itunes:duration>{hms(dur)}</itunes:duration>
      <itunes:episode>{ep['number']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
      <itunes:image href="{base}/cover.jpg"/>
    </item>""")
    idx = f"""<div class="hero"><img src="cover.jpg" alt="cover"><div><h1>{html.escape(SHOW['title'])}</h1>
<p>{html.escape(SHOW['description'])}</p><p><a href="feed.xml">Podcast RSS feed</a></p></div></div>
<h2>Episodes</h2>{''.join(cards)}"""
    (SITE / "index.html").write_text(page(SHOW["title"], idx, base))
    owner_email = SHOW.get("owner_email", "")
    owner = (f"<itunes:owner><itunes:name>{xesc(SHOW['owner_name'])}</itunes:name>"
             + (f"<itunes:email>{xesc(owner_email)}</itunes:email>" if owner_email else "") + "</itunes:owner>")
    last = email.utils.format_datetime(eps[0]["dt"]) if eps else email.utils.format_datetime(datetime.now().astimezone())
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>{xesc(SHOW['title'])}</title>
    <link>{base}/</link>
    <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{xesc(SHOW['description'])}</description>
    <language>{SHOW['language']}</language>
    <copyright>© {datetime.now().year} {xesc(SHOW['author'])}</copyright>
    <lastBuildDate>{last}</lastBuildDate>
    <image><url>{base}/cover.jpg</url><title>{xesc(SHOW['title'])}</title><link>{base}/</link></image>
    <itunes:author>{xesc(SHOW['author'])}</itunes:author>
    <itunes:summary>{xesc(SHOW['description'])}</itunes:summary>
    <itunes:subtitle>{xesc(SHOW['subtitle'])}</itunes:subtitle>
    <itunes:image href="{base}/cover.jpg"/>
    <itunes:category text="{xesc(SHOW['category'])}"/>
    <itunes:explicit>{'true' if SHOW['explicit'] else 'false'}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    {owner}
    <podcast:locked>no</podcast:locked>
{chr(10).join(items_xml)}
  </channel>
</rss>
"""
    (SITE / "feed.xml").write_text(feed)
    (SITE / ".nojekyll").write_text("")
    print(f"built {len(eps)} episode(s) into {SITE} with base {base}")


# ---------------------------------------------------------------- deploy (GitHub Pages)
DEPLOY = ROOT / ".deploy"          # local checkout of the gh-pages branch (generated output only)
GIT_ID = ["-c", "user.name=swaroopgn", "-c", "user.email=1071795+swaroopgn@users.noreply.github.com",
          "-c", "credential.https://github.com.helper=", "-c", "credential.https://github.com.helper=!gh auth git-credential"]


def git(*a, cwd=ROOT, check=True):
    return subprocess.run(["git", *GIT_ID, *a], cwd=cwd, check=check, capture_output=True, text=True)


def commit_and_push(cwd, branch, msg):
    git("add", "-A", cwd=cwd)
    if git("diff", "--cached", "--quiet", cwd=cwd, check=False).returncode != 0:
        git("commit", "-m", msg, cwd=cwd)
    r = git("push", "origin", f"HEAD:{branch}", cwd=cwd, check=False)
    if r.returncode != 0:
        sys.exit(f"git push {branch} failed:\n{r.stderr}")
    print(f"pushed {branch}: {git('rev-parse', '--short', 'HEAD', cwd=cwd).stdout.strip()}")


def cmd_deploy(args):
    cmd_build(args)
    remote = git("remote", "get-url", "origin").stdout.strip()
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    commit_and_push(ROOT, "main", f"Update sources {stamp}")
    if not (DEPLOY / ".git").exists():
        if git("clone", "--branch", "gh-pages", "--single-branch", remote, str(DEPLOY), check=False).returncode != 0:
            DEPLOY.mkdir(exist_ok=True)
            git("init", "-q", cwd=DEPLOY); git("checkout", "-q", "--orphan", "gh-pages", cwd=DEPLOY)
            git("remote", "add", "origin", remote, cwd=DEPLOY)
    else:
        git("fetch", "-q", "origin", "gh-pages", cwd=DEPLOY)
        git("reset", "-q", "--hard", "origin/gh-pages", cwd=DEPLOY)   # generated branch: local copy follows remote
    for p in DEPLOY.iterdir():
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(SITE, DEPLOY, dirs_exist_ok=True)
    commit_and_push(DEPLOY, "gh-pages", f"Deploy site {stamp}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cover")
    t = sub.add_parser("tts"); t.add_argument("slug")
    b = sub.add_parser("build"); b.add_argument("--base-url")
    dp = sub.add_parser("deploy"); dp.add_argument("--base-url")
    a = ap.parse_args()
    {"cover": cmd_cover, "tts": cmd_tts, "build": cmd_build, "deploy": cmd_deploy}[a.cmd](a)


if __name__ == "__main__":
    main()
