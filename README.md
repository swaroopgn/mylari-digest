# Small Models, Real Systems — weekly digest by Mylari

Weekly ~5-minute research digest (audio + companion blog post + podcast RSS) on small-model
fine-tuning for metadata generation and content understanding.

## Layout
```
show.json                      show metadata, Kokoro voice/speed/gap, TTS pronunciation map,
                               spotify_show_uri (filled in once the Spotify show exists)
cover.jpg                      1400x1400 show/episode cover (make_cover.py)
episodes/<YYYY-MM-DD>/
  episode.json                 number, title, spotify_title, date (ISO with +02:00/+01:00), summary
  segments.json                spoken script: one segment per chapter {title, text, sources[]}
  post.md                      companion blog post (Markdown; tables supported)
  script.txt / chapters.json / audio.mp3        written by `build.py tts`
  timeline.json / description.html              written by spotify_publish.py
make_audio.py    Kokoro TTS per segment + pauses -> loudnorm -> 128k mono MP3 + chapters.json
make_cover.py    save-to-spotify cover recipe (CDN base art + white Montserrat Bold title)
build.py         renders site/ (index, episode pages w/ audio player + chapters + transcript, feed.xml)
serve.py         threaded static server for site/ with HTTP Range support
spotify_publish.py  creates the Spotify show once, uploads episode (private), pushes timeline, polls READY
site/            GENERATED — don't edit
```

## Adding a weekly edition
1. Research; write `episodes/<date>/episode.json`, `segments.json` (≈700–750 words total; no URLs,
   spell out acronyms on first use), and `post.md` (every item: title, authors/org, date, URL; real numbers only).
   Add any new tricky words to `pronunciations` in show.json. Bump `number`.
2. `python3 build.py tts <date>` → check the printed duration (target 4.5–5.5 min; tweak `kokoro.speed`).
3. `python3 build.py build --base-url <PUBLIC_BASE_URL>` (feed URLs must be absolute).
4. Host: serve `site/` (see below), then curl the post page, MP3 and feed.xml over the public URL.
5. `python3 spotify_publish.py <date> --post-url <PUBLIC_BASE_URL>/episodes/<date>/`
   (`--dry-run` first to inspect description.html / timeline.json). It writes spotify_url into episode.json.
6. Re-run step 3 so the post page shows the "Listen on Spotify" link; redeploy.

## Hosting (current: temporary)
```
setsid nohup python3 serve.py 8787 >/tmp/mylari_http.log 2>&1 &
nohup ~/.local/bin/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8787 >/tmp/mylari_cf.log 2>&1 &
grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/mylari_cf.log
```
Quick-tunnel URLs are random and die when the process/box restarts, so every rebuild with a new URL changes
the feed's enclosure URLs. For a permanent home (needed before submitting feed.xml to Spotify for Creators),
push `site/` to GitHub Pages / Cloudflare Pages / Netlify and rebuild with that base URL. Also set
`owner_email` in show.json (Spotify verifies feed ownership by emailing `itunes:owner/itunes:email`).
