# VideoNotes AI 🎬

> Turn Any YouTube Video Into Smart Notes, Blog Posts & Social Content in Seconds

## What It Does

Paste a YouTube URL → get:
- ✅ AI-generated summary
- ✅ Key bullet points
- ✅ Timestamp highlights
- ✅ Key takeaways
- ✅ Twitter/X thread hooks
- ✅ Blog draft (500 words)
- ✅ Download as TXT

## Tech Stack (100% Free)

- **Backend:** Python 3.11 + Flask
- **AI:** Google Gemini 1.5 Flash (1,500 free requests/day)
- **Transcripts:** youtube-transcript-api
- **Hosting:** Railway (free tier)

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/videonotes-ai.git
cd videonotes-ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Run locally
python app.py
```

Open http://localhost:5000

## Get Your Free Gemini API Key

1. Go to https://aistudio.google.com
2. Sign in with Google
3. Click "Get API Key"
4. Copy and paste into your `.env` file

No credit card required. 1,500 free requests/day.

## Deploy to Railway

1. Push to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Add `GEMINI_API_KEY` in Railway environment variables
4. Done — live URL provided automatically

## Legal

This tool extracts publicly available transcripts for educational and productivity purposes.
We do not host or distribute copyrighted video content.
