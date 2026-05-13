# BOOKVERSE AI

Premium full-stack bookstore and book management platform built with Flask, HTML, CSS, and JavaScript.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`

## Netlify + Render split

This repository now includes a static frontend in [frontend](C:/Users/mamta/Documents/Codex/2026-04-27/now-build-a-full-stack-premium/frontend) for Netlify and a Flask API backend for Render.

### Local split run

Backend:

```bash
python app.py
```

Frontend:

```bash
cd frontend
python -m http.server 5500
```

Open:

- Frontend: `http://127.0.0.1:5500`
- Backend API: `http://127.0.0.1:5000`

## Deploy

### Render backend

This repository is ready for Python hosting platforms such as Render.

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable: `CROSS_SITE_SESSION=1`
- Environment variable: `FRONTEND_ORIGINS=https://your-netlify-site.netlify.app`

### Netlify frontend

- Publish directory: `frontend`
- Build command: leave empty
- The repo already includes [netlify.toml](C:/Users/mamta/Documents/Codex/2026-04-27/now-build-a-full-stack-premium/netlify.toml) and [frontend/_redirects](C:/Users/mamta/Documents/Codex/2026-04-27/now-build-a-full-stack-premium/frontend/_redirects)
- Update [frontend/config.js](C:/Users/mamta/Documents/Codex/2026-04-27/now-build-a-full-stack-premium/frontend/config.js) so `apiBaseUrl` points to your Render backend URL

Netlify alone is still not suitable for the original Flask backend. This split works because:

1. Netlify serves the static SPA from `frontend/`
2. Render serves the Flask API and data layer
