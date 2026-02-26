# ─────────────────────────────────────────────
#  ParlorPal – lightweight production image
#  Accessible at http://127.0.0.1:8080/
# ─────────────────────────────────────────────
FROM python:3.11-slim

# ── Python tuning ──────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── Override the Windows-absolute path that lives in .env ──
# load_dotenv() never overrides an already-set env var, so this wins.
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/image-gen-demo-epsilon-d9e1f100bfc8.json

# ── Point site URL to our exposed port ─────
ENV SITE_URL=http://127.0.0.1:8080

WORKDIR /app

# ── Install Python deps (cached layer) ─────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy EVERYTHING (includes .env, secrets/, db.sqlite3, media/, static/) ──
COPY . .

# ── Pre-build static files ─────────────────
# settings.py calls load_dotenv(), so .env is read here; the ENV above
# already corrects GOOGLE_APPLICATION_CREDENTIALS before this RUN.
RUN python manage.py collectstatic --noinput || true

# ── Expose the target port ─────────────────
EXPOSE 8080

# ── Startup: migrate → serve ───────────────
# migrate connects to Supabase using SUPABASE_DB_CONNECTION_STRING from .env.
# gunicorn runs with 2 workers; timeout=120 handles cold AI calls.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn parlorpal.wsgi:application --bind 0.0.0.0:8080 --workers 2 --timeout 120 --log-level info"]
