# Vaultcast publish: 2026-11-18-small-models (Small Models, Real Systems #8)
18 Nov 2026 ~07:55 CET: Spotify + blog DONE. Vaultcast PARTIAL.

Done:
- Transcript uploaded to Vaultcast folder 12eh1m2JmEk_mOdMm40KyPbth5Afsgl57:
  2026-11-18-small-models.transcript.json  id 11OJ1YzEkt82QoAm4XAAgmjyFlVUws93c (7,836 bytes, matches local, not shared)
- Cover already in folder: small-models-real-systems.jpg (10ve9gLcqTfSf_2272Utz2sctIMWkoSLY)
- Staged entry (with showId/kind/summary/topics/headline): vc-staging/entry.json

Blocked: executor has no cursor UploadFile; Drive create_file caps ~750 KB, the m4a is 5,501,934 bytes.

Remaining (in order):
1. UploadFile /workspace/mylari-digest/episodes/2026-11-18/2026-11-18-small-models.m4a -> folderId 12eh1m2JmEk_mOdMm40KyPbth5Afsgl57
   (do NOT re-upload the transcript; it is already there)
2. mkdir /workspace/vaultcast/.catalog.lock (owner file), download CURRENT catalog.json (id 1HrVWva_lPH0sPo7czXHeYVC7xchkUVcs).
3. In show small-models-real-systems append entry.json minus showId/kind/summary/topics/headline (same shape as 2026-11-11-small-models).
   Keep playbackControl as is ("15-seconds"/unset).
4. Verify audioFile, imageFile, transcriptFile exist in folder (list all pages), overwrite catalog.json in place
   (update_file_content, application/json), re-download, confirm exactly one catalog.json, release lock.
5. API (cd /tmp/vc && git pull -q; set -a; . /workspace/vaultcaster/.secrets/vaultcast-api.env; set +a):
   python3 server/vaultcast_publish.py put-episode --from-staging /workspace/mylari-digest/episodes/2026-11-18/vc-staging
   python3 server/vaultcast_publish.py backfill-transcripts /workspace/mylari-digest/episodes/2026-11-18/vc-staging/2026-11-18-small-models.transcript.json
   python3 server/vaultcast_publish.py readable-from-transcript --episode 2026-11-18-small-models --transcript /workspace/mylari-digest/episodes/2026-11-18/vc-staging/2026-11-18-small-models.transcript.json
   python3 server/vaultcast_publish.py get | grep -c '"2026-11-18-small-models"'   # >= 1

## DONE 18 Nov 2026 ~07:55 CET (executor)
- m4a in folder: 10oQLHNOTwjR0OMWWOfLP8YMryj2cCXsr (5,501,934 bytes)
- catalog.json 1HrVWva_lPH0sPo7czXHeYVC7xchkUVcs overwritten in place (279,574 bytes), re-download identical, exactly one catalog.json, all 389 refs present, lock released
- API: put-episode ok, transcript blocks=25, readable sections=7 (3 min), get count=1
