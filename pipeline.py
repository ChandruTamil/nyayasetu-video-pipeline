#!/usr/bin/env python3
"""
NyayaSetu Video Pipeline
-------------------------
1. Reads a topic list (topics.txt, one per line)
2. Generates a 10s 720p 16:9 clip via Grok Imagine Video API (xAI SDK)
3. Downloads the temporary video URL
4. Uploads to YouTube as a private/unlisted draft (YouTube Data API v3)

Setup:
  pip install xai-sdk google-api-python-client google-auth-httplib2 google-auth-oauthlib
  export XAI_API_KEY=...
  # One-time YouTube OAuth: python pipeline.py --auth
  python pipeline.py              # process all topics
  python pipeline.py --topic "contract law basics"  # single topic

Notes:
- Grok Imagine clips max 15s; stitch several in CapCut/DaVinci for a full video.
- Video URLs are ephemeral — download immediately.
- YouTube upload uses resumable upload; needs OAuth client secrets.
"""

import argparse, os, sys, time
from pathlib import Path

try:
    from xai_sdk import Client
    from xai_sdk.video import Video
    HAS_XAI = True
except ImportError:
    HAS_XAI = False

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    HAS_GAPI = True
except ImportError:
    HAS_GAPI = False

SCOPES = ["https://www.googleapis.com/auth/youtube"]
TOKEN_FILE = "youtube_token.json"
SECRETS_FILE = "client_secrets.json"
OUT_DIR = Path("videos")
OUT_DIR.mkdir(exist_ok=True)

TOPICS_FILE = Path("topics.txt")
DEFAULT_TOPICS = [
    "Introduction to the Indian Constitution",
    "What is a contract under Indian law",
    "Fundamental Rights in simple terms",
    "How property transfer works in India",
    "Basics of labour law for workers",
]

def load_topics():
    if TOPICS_FILE.exists():
        return [t.strip() for t in TOPICS_FILE.read_text().splitlines() if t.strip()]
    return DEFAULT_TOPICS

def generate_video(topic: str, duration: int = 10, resolution: str = "720p"):
    if not HAS_XAI:
        raise RuntimeError("xai-sdk not installed: pip install xai-sdk")
    client = Client(api_key=os.environ.get("XAI_API_KEY"))
    prompt = (
        f"Cinematic educational explainer about Indian law: {topic}. "
        f"Warm parchment and ink aesthetic, subtle motion, calm narrator-friendly visuals, 16:9."
    )
    response = client.video.generate(
        prompt=prompt,
        model="grok-imagine-video-1.5-lite",
        duration=duration,
        aspect_ratio="16:9",
        resolution=resolution,
    )
    return response.video.url

def download(url: str, path: Path):
    import requests
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(1024 * 256):
            f.write(chunk)
    return path

def get_youtube_service():
    if not HAS_GAPI:
        raise RuntimeError("google api libs missing: pip install google-api-python-client google-auth-oauthlib")
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_youtube(path: Path, title: str, description: str, privacy="unlisted"):
    yt = get_youtube_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "categoryId": "25",
            "tags": ["Indian law", "legal information", "NyayaSetu", "education"],
        },
        "status": {"privacyStatus": privacy},
    }
    media = MediaFileUpload(str(path), chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  upload {int(status.progress() * 100)}%")
    return resp["id"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth", action="store_true", help="one-time YouTube OAuth")
    ap.add_argument("--topic", help="single topic instead of topics.txt")
    ap.add_argument("--privacy", default="unlisted", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    if args.auth:
        get_youtube_service()
        print("YouTube authorized ->", TOKEN_FILE)
        return

    topics = [args.topic] if args.topic else load_topics()
    print(f"{len(topics)} topic(s) to process")
    for topic in topics:
        print("TOPIC:", topic)
        try:
            url = generate_video(topic)
            print("  generated:", url[:80], "...")
            out = OUT_DIR / (topic.lower().replace(" ", "_")[:40] + ".mp4")
            download(url, out)
            print("  saved:", out)
            vid = upload_youtube(
                out,
                title=f"NyayaSetu: {topic}",
                description=(
                    f"Plain-language overview of {topic} under Indian central law. "
                    f"General information only — not legal advice. "
                    f"Full texts: https://indiacode.ecourtsindia.com"
                ),
                privacy=args.privacy,
            )
            print("  youtube id:", vid)
        except Exception as e:
            print("  ERROR:", e)
        time.sleep(2)

if __name__ == "__main__":
    main()
