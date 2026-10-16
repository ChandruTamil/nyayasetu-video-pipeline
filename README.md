# NyayaSetu Shorts Pipeline

Auto-generate vertical legal explainers with Grok Imagine Video and post them as YouTube Shorts.

## One-time setup (do this on your machine)

1. **Python 3.10+** installed.
2. Create a project folder and drop in `pipeline.py` and `topics.txt` from this repo.
3. Install dependencies:
   ```bash
   pip install xai-sdk google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
   ```
4. **xAI key**: sign up at https://console.x.ai , create an API key, then:
   ```bash
   export XAI_API_KEY=your_key_here
   ```
   (On Windows: `set XAI_API_KEY=...`)
5. **Google Cloud OAuth** (for YouTube uploads):
   - Go to https://console.cloud.google.com/apis/library and enable **YouTube Data API v3**.
   - Go to APIs & Services > Credentials > Create Credentials > **OAuth client ID**.
     Choose **Desktop app**. Download the JSON and save it as `client_secrets.json`
     in the project folder.
   - First run: `python pipeline.py --auth` — a browser window opens, you approve
     once, and `youtube_token.json` is saved. You won't do this again.
6. Test without uploading: `python pipeline.py --dry-run` (generates + downloads only).
7. Go live: `python pipeline.py` — each new topic becomes a public Short titled
   "NyayaSetu: <topic> #Shorts". Already-posted topics are tracked in
   `posted_topics.json` so nothing repeats.

## Automated runs (pick one)

### Option A — local cron (Mac/Linux)
```bash
crontab -e
```
Add (runs every weekday at 9 AM):
```
0 9 * * 1-5 cd /path/to/project && /usr/bin/python3 pipeline.py >> pipeline.log 2>&1
```

### Option B — local Task Scheduler (Windows)
Create a task that runs daily at 9 AM:
`python pipeline.py`
working directory = project folder.

### Option C — Grok Automations (no server needed)
In this chat, ask Eve to create a scheduled automation that SSHes into your
machine or runs the pipeline wherever it's hosted, e.g. daily at 09:00 IST.
The automation prompt should be: "Run: cd <project> && python3 pipeline.py and
report the youtube ids created."

## Env vars

- `YT_PRIVACY` — `public` (default), `unlisted`, or `private`
- `YT_SCHEDULE_OFFSET_H` — if >0, uploads are scheduled that many hours apart
  instead of going live immediately (useful for pacing a batch)

## Cost

`grok-imagine-video-1.5-lite` at 720p is $0.03/sec → a 10s Short costs about
30 cents. Ten Shorts a week ≈ $3/week.

## Notes

- Clips are 10 seconds (max 15). That's ideal Shorts length.
- Aspect ratio is 9:16 vertical.
- Category set to News & Politics (25). Switch to Education (27) in pipeline.py
  if you prefer.
- Content moderation applies to generated clips; a rejected topic prints an ERROR
  and the pipeline moves on.
