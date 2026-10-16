#!/usr/bin/env python3
"""
NyayaSetu Shorts Pipeline
-------------------------
1. Reads topics from topics.txt (one per line)
2. Generates a 10s 720p 9:16 vertical clip via Grok Imagine Video API
3. Downloads the temporary video URL
4. Uploads to YouTube as a Short (privacy default: public)

Setup (one-time, local):
  pip install xai-sdk google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
  export XAI_API_KEY=...
  # Google Cloud: create OAuth client (Desktop app), enable YouTube Data API v3,
  # download client_secrets.json into this folder
  python pipeline.py --auth

Run:
  python pipeline.py                 # all topics in topics.txt
  python pipeline.py --topic "..."   # single topic
  python pipeline.py --dry-run       # generate + download only, no upload

Env:
  XAI_API_KEY          required
  YT_PRIVACY           public | unlisted | private (default: public)
  YT_SCHEDULE_OFFSET_H hours from now to schedule publish (Shorts: set >=0)
"""

import argparse, os, sys, time, json
from pathlib import Path
from datetime import datetime, timedelta, timezone

try:
    from xai_sdk import Client
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
STATE_FILE = Path("posted_topics.json")

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

def load_posted():
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except Exception:
            return set()
    return set()

def save_posted(posted):
    STATE_FILE.write_text(json.dumps(sorted(posted), indent=1))

def generate_video(topic: str, duration: int = 10, resolution: str = "720p"):
    if not HAS_XAI:
        raise RuntimeError("xai-sdk not installed: pip install xai-sdk")
    if not os.environ.get("XAI_API_KEY"):
        raise RuntimeError("XAI_API_KEY not set")
    client = Client(api_key=os.environ["XAI_API_KEY"])
    prompt = (
        f"Vertical 9:16 Shorts-style cinematic explainer about Indian law: {topic}. "
        f"Warm parchment and ink aesthetic, subtle motion, calm visuals, educational tone."
    )
    response = client.video.generate(
        prompt=prompt,
        model="grok-imagine-video-1.5-lite",
        duration=duration,
        aspect_ratio="9:16",
        resolution=resolution,
    )
    return response.video.url

def download(url: str, path: Path):
    import requests
    r = requests.get(url, stream=True, timeout=180)
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(1024 * 256):
            f.write(chunk)
    return path

def get_youtube_service():
    if not HAS_GAPI:
        raise RuntimeError("pip install google-api-python-client google-auth-oauthlib")
    creds = None
    if Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not Path(SECRETS_FILE).exists():
                raise RuntimeError(f"{SECRETS_FILE} missing — see README setup steps")
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(TOKEN_FILE).write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_youtube(path: Path, title: str, description: str, privacy="public",
                   publish_at=None):
    yt = get_youtube_service()
    if "#shorts" not in title.lower():
        title = (title + " #Shorts")[:100]
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "categoryId": "25",
            "tags": ["Indian law", "legal information", "NyayaSetu", "education", "shorts"],
        },
        "status": {"privacyStatus": privacy},
    }
    if publish_at is not None:
        body["status"]["publishAt"] = publish_at.astimezone(timezone.utc).isoformat()
        body["status"]["privacyStatus"] = "private"
    media = MediaFileUpload(str(path), chunksize=-1, resumable=True, mimetypes="video/mp4")
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
    ap.add_argument("--privacy", default=os.environ.get("YT_PRIVACY", "public"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--schedule-offset-h", type=float,
                    default=float(os.environ.get("YT_SCHEDULE_OFFSET_H", "0")))
    args = ap.parse_args()

    if args.auth:
        get_youtube_service()
        print("YouTube authorized ->", TOKEN_FILE)
        return

    topics = [args.topic] if args.topic else load_topics()
    posted = load_posted()
    fresh = [t for t in topics if t not in posted]
    if not fresh:
        print("No new topics (all already posted). Add lines to topics.txt.")
        return
    print(f"{len(fresh)} new topic(s) of {len(topics)} total")

    for i, topic in enumerate(fresh):
        print("TOPIC:", topic)
        try:
            url = generate_video(topic)
            print("  generated url ok")
            out = OUT_DIR / (topic.lower().replace(" ", "_")[:40] + ".mp4")
            download(url, out)
            print("  saved:", out, f"({out.stat().st_size/1e6:.1f} MB)")
            if args.dry_run:
                print("  dry-run: skipping upload")
            else:
                pub_at = None
                if args.schedule_offset_h > 0:
                    pub_at = datetime.now(timezone.utc) + timedelta(hours=args.schedule_offset_h * (i + 1))
                vid = upload_youtube(
                    out,
                    title=f"NyayaSetu: {topic}",
                    description=(
                        f"Plain-language overview of {topic} under Indian central law. "
                        f"General information only — not legal advice. "
                        f"Full texts: https://indiacode.ecourtsindia.com #Shorts"
                    ),
                    privacy=args.privacy,
                    publish_at=pub_at,
                )
                print("  youtube id:", vid, ("scheduled" if pub_at else "live"))
                posted.add(topic)
                save_posted(posted)
        except Exception as e:
            print("  ERROR:", e)
        time.sleep(2)

if __name__ == "__main__":
    main()
