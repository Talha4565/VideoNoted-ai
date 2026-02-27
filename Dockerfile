# ── Base image ───────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Set working directory ─────────────────────────────────────────────────
WORKDIR /app

# ── Install dependencies first (cached layer) ─────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy project files ────────────────────────────────────────────────────
COPY . .

# ── Expose port ───────────────────────────────────────────────────────────
EXPOSE 5000

# ── Run with Gunicorn (production server) ─────────────────────────────────
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
