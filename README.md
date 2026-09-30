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
make_audio.py    TTS per segment + pauses -> loudnorm -> 128k mono MP3 + chapters.json + <stem>.meta.json
                 (ElevenLabs by default, automatic whole-episode fallback to Kokoro)
make_cover.py    save-to-spotify cover recipe (CDN base art + white Montserrat Bold title)
build.py         renders site/ (index, episode pages w/ audio player + chapters + transcript, feed.xml)
serve.py         threaded static server for site/ with HTTP Range support
spotify_publish.py  creates the Spotify show once, uploads episode (private), pushes timeline, polls READY
site/            GENERATED — don't edit
```

## Live
- Site: https://swaroopgn.github.io/mylari-digest/  (GitHub Pages, `gh-pages` branch of swaroopgn/mylari-digest)
- Podcast RSS: https://swaroopgn.github.io/mylari-digest/feed.xml
- Spotify: saved (private) into show `spotify_show_uri` in show.json

## Adding a weekly edition
1. Research; write `episodes/<date>/episode.json` (bump `number`, set `title`, `spotify_title`, `date`, `summary`),
   `segments.json` (one segment per chapter, ~700-750 words total, no URLs read aloud, acronyms spelled out on
   first use, `sources` per segment) and `post.md` (every item: title, authors/org, date, URL; real numbers only).
   Add tricky words to `pronunciations` in show.json.
2. Run the whole pipeline:
   ```
   ./publish_week.sh <date>            # tts -> build+push Pages -> wait live -> Spotify upload+timeline+READY -> re-push with Spotify link
   ./publish_week.sh <date> --skip-tts # if audio.mp3 is already final
   ```
   Check the printed duration after tts (target 4.5-5.5 min; tweak `kokoro.speed` in show.json).

Individual steps:
```
python3 build.py tts <date>                 # Kokoro narration -> audio.mp3, chapters.json, script.txt
python3 build.py build                      # render site/ locally (base_url from show.json)
python3 build.py deploy                     # build + push sources to main + site/ to gh-pages
python3 spotify_publish.py <date> --post-url <base>/episodes/<date>/ [--dry-run]
python3 serve.py 8787                       # local preview of site/ (Range-capable)
```

## Narration (TTS)
- Default: **ElevenLabs**, voice "Daniel - Steady Broadcaster" (`onwK4e9ZLuTAKqWW03F9`), model `eleven_v4`,
  `mp3_44100_128`, configured in show.json -> `tts.elevenlabs`. Needs `ELEVENLABS_API_KEY` in the environment
  (never commit or print it). Change voice/model there; list options with `GET /v1/voices` and `GET /v1/models`.
- Fallback: if ElevenLabs errors (missing key, auth/permission, quota, repeated 429/5xx), the whole episode is
  re-rendered with **Kokoro** (`kokoro.voice`, `kokoro.speed`) so the voice never switches mid-episode.
  Force an engine: `./make_audio.py <date> --engine kokoro` (or `--no-fallback` to fail instead).
- Paid ElevenLabs segments are cached in `episodes/<date>/.tts-cache/` (keyed on voice+model+text), so
  re-renders (e.g. a different `--tempo` or gap) cost nothing unless the text changes.
- Pace: Daniel on eleven_v4 reads ~125 words/min (769 words -> 6:15), slower than Kokoro. For the 4.5-5.5 min
  target write ~600-680 words, or set `tts.elevenlabs.tempo` (pitch-preserving ffmpeg atempo, e.g. 1.1) -
  `voice_settings.speed` had no measurable effect on eleven_v4 in testing.
- Each render writes `<stem>.meta.json` (engine, voice, model, ElevenLabs `character-cost` credits billed).
- Alternate renders: `./make_audio.py <date> --out audio-test.mp3` writes chapters-audio-test.json and
  never touches audio.mp3 (git-ignored: `audio-*.mp3`).

## Notes
- `spotify_publish.py` uploads exactly once. If a call errors ambiguously (e.g. HTTP 504) it checks the show for an
  episode with the same title before doing anything else, and refuses to upload if one already exists.
  Spotify metadata is immutable; to change title/description, delete the episode and re-run.
- Git pushes use `gh auth git-credential` per command (no global git config changes). Commits are authored as
  swaroopgn (noreply address).
- Before submitting feed.xml to Spotify for Creators / Apple, set `owner_email` in show.json (feed ownership check).
