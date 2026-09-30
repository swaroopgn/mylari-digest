#!/usr/bin/env bash
# Weekly run: audio -> site on GitHub Pages -> Spotify (private, saved show) -> site again with the Spotify link.
# Usage: ./publish_week.sh YYYY-MM-DD [--skip-tts]
# Prereqs: episodes/<date>/{episode.json,segments.json,post.md} written; `gh` authenticated as swaroopgn;
#          save-to-spotify authenticated; show.json has base_url and spotify_show_uri.
set -euo pipefail
cd "$(dirname "$0")"
SLUG="${1:?usage: $0 YYYY-MM-DD [--skip-tts]}"
BASE="$(python3 -c 'import json;print(json.load(open("show.json"))["base_url"].rstrip("/"))')"
POST="$BASE/episodes/$SLUG/"
MP3="$BASE/audio/small-models-real-systems-$SLUG.mp3"

wait_live() {  # wait until every URL returns 200 (Pages rebuild usually takes 30-90 s)
  for i in $(seq 1 40); do
    ok=1; for u in "$@"; do [ "$(curl -s -o /dev/null -w '%{http_code}' "$u?v=$RANDOM")" = 200 ] || ok=0; done
    [ $ok = 1 ] && { echo "live: $*"; return 0; }; sleep 15
  done; echo "timed out waiting for: $*" >&2; return 1
}

ENGINE="$(python3 -c 'import json;print(json.load(open("show.json")).get("tts",{}).get("engine","kokoro"))')"
if [ "$ENGINE" = elevenlabs ] && [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "WARNING: ELEVENLABS_API_KEY not set in this environment - narration will fall back to Kokoro" >&2
fi
[ "${2:-}" = "--skip-tts" ] || python3 build.py tts "$SLUG"   # ElevenLabs (show.json tts), auto-fallback to Kokoro
python3 -c "import json;m=json.load(open('episodes/$SLUG/audio.meta.json'));print('narration:',m['engine'],m.get('voice'),m.get('model_id',''),'credits:',m.get('character_cost','-'))" 2>/dev/null || true
python3 build.py deploy --base-url "$BASE"
wait_live "$BASE/" "$POST" "$MP3" "$BASE/feed.xml"
python3 spotify_publish.py "$SLUG" --post-url "$POST"    # uploads once, pushes timeline, polls READY
python3 build.py deploy --base-url "$BASE"               # post page now carries the Spotify link
sleep 20; wait_live "$POST"
curl -s "$POST?v=$RANDOM" | grep -q "open.spotify.com/episode" && echo "Spotify link is live on $POST"
python3 -c "import json;e=json.load(open('episodes/$SLUG/episode.json'));print(e.get('spotify_episode_uri'), e.get('spotify_url'))"
