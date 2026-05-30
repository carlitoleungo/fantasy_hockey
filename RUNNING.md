# Running Locally

## First-time setup (new machine)

### 1. Python environment

The codebase uses Python 3.10+ syntax (`str | None`). macOS ships Python 3.9, so you need a newer version. Use `uv`:

```bash
uv python install 3.11
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements-web.txt
```

The `.venv` directory is local to this project and won't affect other projects.

### 2. Environment variables

Create a `.env` file in the project root (gitignored):

```bash
YAHOO_CLIENT_ID=your_client_id_here
YAHOO_CLIENT_SECRET=your_client_secret_here
YAHOO_REDIRECT_URI=https://your-ngrok-subdomain.ngrok-free.dev/auth/callback
```

Get your `client_id` and `client_secret` from the Yahoo Developer Console.

### 3. ngrok (HTTPS tunnel)

Yahoo OAuth requires an HTTPS redirect URI. ngrok provides this for local development.

Install: https://ngrok.com/download (or `brew install ngrok`)

Start a tunnel:
```bash
ngrok http 8000
```

ngrok gives you a stable subdomain on the free plan (e.g. `https://blatancy-grill-garage.ngrok-free.dev`). Add `https://your-subdomain.ngrok-free.dev/auth/callback` as a redirect URI in the Yahoo Developer Console, and set it as `YAHOO_REDIRECT_URI` in your `.env`.

**Access the app via the ngrok URL**, not `localhost:8000` — OAuth callbacks must land on the registered HTTPS host.

---

## Subsequent runs

```bash
# Terminal 1 — activate venv and start the server
source .venv/bin/activate
python -m uvicorn web.main:app --reload

# Terminal 2 — start the HTTPS tunnel
ngrok http 8000
```

Then open `https://your-ngrok-subdomain.ngrok-free.dev` in your browser.
