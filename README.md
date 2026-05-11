# BOOKVERSE AI

Premium full-stack bookstore and book management platform built with Flask, HTML, CSS, and JavaScript.

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`

## Deploy

This repository is ready for Python hosting platforms such as Render.

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Netlify is best suited to static sites and supported function runtimes. This Flask app will need either:

1. A Python host such as Render or Railway, or
2. A backend refactor into Netlify-compatible serverless functions
