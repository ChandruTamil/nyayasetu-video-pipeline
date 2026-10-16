# NyayaSetu Video Pipeline

Auto-generate short legal explainers with **Grok Imagine Video** and upload them to YouTube.

## Flow

1. `topics.txt` — one topic per line
2. Pipeline calls the xAI Imagine API (`grok-imagine-video-1.5-lite`, 10s, 720p, 16:9) — about three cents per second
3. Downloads the clip (URLs are temporary)
4. Uploads to YouTube via Data API v3 as private/unlisted/public

## Setup

```bash
pip install xai-sdk google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
export XAI_API_KEY=your_key
# download OAuth client secrets from Google Cloud Console (YouTube Data API v3 enabled)
python pipeline.py --auth
python pipeline.py
```

## Limits to know

- Clips max out at 15 seconds — stitch several in an editor for a full video
- Content moderation applies to generated clips
- YouTube category set to News & Politics (25); switch if you prefer Education (27)

## Cost example

Ten 10-second 720p clips ≈ $3.00 in API fees, before YouTube monetization.
