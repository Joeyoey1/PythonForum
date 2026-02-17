# PythonForum

A lightweight Flask-based forum/blog experiment with user accounts, profiles, post publishing, replies, and search.

## Features

- User signup + login
- Create/edit posts (draft or published)
- Reply to posts
- Basic profile + follower/following pages
- Full-text search (SQLite FTS)

## Quick start

```bash
git clone git@github.com:Joeyoey1/PythonForum.git
cd PythonForum
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

## Configuration notes

The app currently uses in-file defaults in `app.py` (admin credentials, secret key, database path). For production use, move secrets to environment variables.

## Development

Quick syntax check:

```bash
python -m py_compile app.py
```

## Status

This was originally a learning project and is still evolving. PRs are welcome for incremental improvements.
