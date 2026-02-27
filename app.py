import os
import time
import datetime
from flask import Flask, request, jsonify, render_template, Response
from dotenv import load_dotenv

load_dotenv()

# ── Startup validation ──────────────────────────────────────────────────────
if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

from utils.validator import extract_video_id
from utils.transcript import fetch_transcript
from utils.ai_processor import generate_content
from utils.cache import video_cache

app = Flask(__name__)

# ── Rate limiting (in-memory) ───────────────────────────────────────────────
# Structure: { ip: { "minute": [timestamps], "day": [timestamps] } }
rate_store: dict = {}

MAX_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 5))
MAX_PER_DAY    = int(os.getenv("MAX_REQUESTS_PER_DAY", 3))


def check_rate_limit(ip: str) -> tuple[bool, str]:
    """Returns (allowed: bool, error_message: str)."""
    now = time.time()

    if ip not in rate_store:
        rate_store[ip] = {"minute": [], "day": []}

    # Clean old timestamps
    rate_store[ip]["minute"] = [t for t in rate_store[ip]["minute"] if now - t < 60]
    rate_store[ip]["day"]    = [t for t in rate_store[ip]["day"]    if now - t < 86400]

    if len(rate_store[ip]["minute"]) >= MAX_PER_MINUTE:
        return False, "Too many requests. Please wait a minute and try again."

    if len(rate_store[ip]["day"]) >= MAX_PER_DAY:
        return False, "You've used your 3 free videos today. Try again tomorrow."

    # Record this request
    rate_store[ip]["minute"].append(now)
    rate_store[ip]["day"].append(now)
    return True, ""


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/dmca")
def dmca():
    return render_template("dmca.html")


# ── Health check ─────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    """Railway, Docker, and uptime monitors use this."""
    return jsonify({
        "status": "ok",
        "cache_size": video_cache.size(),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }), 200


# ── robots.txt ───────────────────────────────────────────────────────────────
@app.route("/robots.txt")
def robots():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: https://videonotesai.com/sitemap.xml\n"
    )
    return Response(content, mimetype="text/plain")


# ── sitemap.xml ──────────────────────────────────────────────────────────────
@app.route("/sitemap.xml")
def sitemap():
    base = "https://videonotesai.com"
    today = datetime.date.today().isoformat()
    pages = [
        ("", "1.0", "daily"),
        ("/privacy", "0.3", "monthly"),
        ("/terms", "0.3", "monthly"),
        ("/dmca", "0.3", "monthly"),
    ]
    urls = "\n".join(
        f"""  <url>
    <loc>{base}{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
        for path, priority, freq in pages
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""
    return Response(xml, mimetype="application/xml")


# ── 404 handler ──────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.route("/api/process", methods=["POST"])
def process_video():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # 1. Rate limit check
    allowed, rate_error = check_rate_limit(ip)
    if not allowed:
        return jsonify({"success": False, "error": rate_error}), 429

    # 2. Parse request
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"success": False, "error": "Please provide a YouTube URL."}), 400

    url = data["url"].strip()

    # 3. Validate URL & extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"success": False, "error": "Please paste a valid YouTube URL."}), 400

    # 4. Check cache (saves Gemini API calls)
    cached = video_cache.get(video_id)
    if cached:
        return jsonify({"success": True, "cached": True, **cached})

    # 5. Fetch transcript
    transcript_result = fetch_transcript(video_id)
    if not transcript_result["success"]:
        return jsonify({"success": False, "error": transcript_result["error"]}), 422

    # 6. Generate AI content
    ai_result = generate_content(transcript_result["text"])
    if not ai_result["success"]:
        return jsonify({"success": False, "error": ai_result["error"]}), 503

    # 7. Build final response
    result = {
        "video_id": video_id,
        **ai_result["data"],
    }

    # 8. Store in cache
    video_cache.set(video_id, result)

    return jsonify({"success": True, "cached": False, **result})


@app.route("/api/export/txt")
def export_txt():
    """Generate and stream a plain-text file of all content for a video."""
    video_id = request.args.get("video_id", "").strip()
    if not video_id:
        return jsonify({"success": False, "error": "Missing video_id"}), 400

    cached = video_cache.get(video_id)
    if not cached:
        return jsonify({"success": False, "error": "Content not found. Please process the video first."}), 404

    lines = []
    lines.append("=" * 60)
    lines.append("VIDEONOTES AI — EXPORT")
    lines.append("=" * 60)
    lines.append("")

    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(cached.get("summary", ""))
    lines.append("")

    lines.append("KEY POINTS")
    lines.append("-" * 40)
    for point in cached.get("key_points", []):
        lines.append(f"• {point}")
    lines.append("")

    lines.append("TIMESTAMPS")
    lines.append("-" * 40)
    for ts in cached.get("timestamps", []):
        lines.append(f"{ts.get('time', '')} — {ts.get('note', '')}")
    lines.append("")

    lines.append("KEY TAKEAWAYS")
    lines.append("-" * 40)
    for i, t in enumerate(cached.get("takeaways", []), 1):
        lines.append(f"{i}. {t}")
    lines.append("")

    lines.append("TWITTER/X HOOKS")
    lines.append("-" * 40)
    for hook in cached.get("hooks", []):
        lines.append(f"• {hook}")
    lines.append("")

    lines.append("BLOG DRAFT")
    lines.append("-" * 40)
    lines.append(cached.get("blog_draft", ""))
    lines.append("")
    lines.append("=" * 60)
    lines.append("Generated by VideoNotes AI")
    lines.append("=" * 60)

    content = "\n".join(lines)

    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=videonotes_{video_id}.txt"}
    )


@app.route("/api/export/pdf")
def export_pdf():
    """Generate a styled HTML page and serve it for browser print-to-PDF."""
    video_id = request.args.get("video_id", "").strip()
    if not video_id:
        return jsonify({"success": False, "error": "Missing video_id"}), 400

    cached = video_cache.get(video_id)
    if not cached:
        return jsonify({"success": False, "error": "Content not found. Please process the video first."}), 404

    key_points_html = "".join(f"<li>{p}</li>" for p in cached.get("key_points", []))
    timestamps_html = "".join(
        f'<li><span class="ts-badge">{ts.get("time","")}</span> {ts.get("note","")}</li>'
        for ts in cached.get("timestamps", [])
    )
    takeaways_html = "".join(f"<li>{t}</li>" for t in cached.get("takeaways", []))
    hooks_html = "".join(f"<li>{h}</li>" for h in cached.get("hooks", []))
    blog_text = cached.get("blog_draft", "").replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>VideoNotes AI — Export</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 780px; margin: 40px auto; padding: 0 24px; color: #1a1a2e; line-height: 1.7; }}
  h1 {{ font-size: 22px; border-bottom: 2px solid #6366f1; padding-bottom: 8px; color: #6366f1; }}
  h2 {{ font-size: 16px; margin-top: 28px; margin-bottom: 6px; color: #3b3b6b; text-transform: uppercase; letter-spacing: .05em; }}
  ul {{ padding-left: 20px; }}
  li {{ margin-bottom: 6px; }}
  .ts-badge {{ background:#6366f1; color:#fff; border-radius:4px; padding:1px 6px; font-size:12px; font-family:monospace; margin-right:8px; }}
  .blog {{ white-space: pre-wrap; background: #f8f8ff; border-left: 3px solid #6366f1; padding: 16px; border-radius: 4px; font-size: 14px; }}
  .footer {{ margin-top: 48px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 12px; }}
  @media print {{ body {{ margin: 20px; }} }}
</style>
</head>
<body>
<h1>VideoNotes AI — Content Export</h1>
<p style="color:#888;font-size:13px;">Generated on {datetime.date.today().strftime("%B %d, %Y")} &nbsp;|&nbsp; videonotesai.com</p>

<h2>📝 Summary</h2>
<p>{cached.get("summary","")}</p>

<h2>🎯 Key Points</h2>
<ul>{key_points_html}</ul>

<h2>⏱️ Timestamps</h2>
<ul style="list-style:none;padding-left:0;">{timestamps_html}</ul>

<h2>💡 Key Takeaways</h2>
<ol>{takeaways_html}</ol>

<h2>🐦 Twitter / X Hooks</h2>
<ul>{hooks_html}</ul>

<h2>📄 Blog Draft</h2>
<div class="blog">{blog_text}</div>

<div class="footer">Generated by VideoNotes AI &mdash; videonotesai.com</div>
<script>window.onload = function() {{ window.print(); }}</script>
</body>
</html>"""

    return Response(html, mimetype="text/html")


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_ENV") != "production", host="0.0.0.0", port=5000)
