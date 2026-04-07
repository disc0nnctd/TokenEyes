# TokenEyes — Cloudflare Deployment

## Security model (important for self-hosters)

- **User API keys** — entered in-browser, memory only, never sent to any TokenEyes server.
  All vision calls go directly from the user's browser to Gemini / OpenRouter / CF Workers AI.
- **Your Workers AI binding** — used only by the `/advisor` and `/country` routes handled by `_worker.js`.
  `/advisor` generates quip text (no image data, no user keys). `/country` returns an ISO country code.
  Neither function receives user API keys or image data.
- **KV namespace** — stores generated quip text strings only. No user data, no images, no keys.
- **Rate limiting** — the `/advisor` function is naturally rate-limited by Workers AI free tier
  (100k requests/day). If you want additional protection, add a Cloudflare Rate Limiting rule
  on `POST /advisor` in your Pages project settings.
- **No account ID or credentials in code** — your CF Account ID is a dashboard-only binding,
  never committed to the repo. The repo is safe to open-source as-is.

---

## Local preview

No build step needed. Just open `index.html` directly:

```bash
# Option A: Python simple server
cd cloudflare/
python3 -m http.server 3000
# → http://localhost:3000

# Option B: npx serve (auto HTTPS for camera on LAN)
npx serve . -p 3000
```

> **Note:** `getUserMedia` (camera) requires HTTPS or `localhost`. On local network,
> use `https://` or tunnel via [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

---

## Deploy to Cloudflare Pages

### Option A: Drag & drop (fastest)

1. Go to [pages.cloudflare.com](https://pages.cloudflare.com)
2. Click **Create application → Pages → Upload assets**
3. Drag the `cloudflare/` folder (or zip its contents)
4. Done — you get a `*.pages.dev` URL with HTTPS automatically

### Option B: Git-connected (auto-deploy on push)

1. Push this repo to GitHub
2. Cloudflare Pages → **Create application → Connect to Git**
3. Select your repo
4. Settings:
   - **Build command:** *(leave empty — no build needed)*
   - **Build output directory:** `cloudflare`
5. Save & deploy

This folder is a plain static site. Do not add an SPA fallback redirect
(`/* /index.html 200`), because Cloudflare Pages validates it as a redirect
loop for this deployment setup.

Every push to `main` auto-deploys.

### Option C: Wrangler CLI

```bash
npm install -g wrangler
wrangler login
wrangler pages deploy cloudflare/ --project-name token-eyes --branch main
```

`wrangler` always prints a unique deployment URL (for example
`https://<hash>.token-eyes.pages.dev`). That is normal. Your stable production URL stays
`https://token-eyes.pages.dev` when the deploy branch matches your configured production
branch (typically `main`).

### Option D: GitHub Actions (Wrangler in CI)

Use the included workflow to deploy from GitHub instead of local `wrangler`:

- Workflow file: `.github/workflows/deploy-cloudflare-pages.yml`
- Trigger: pushes to `main` that touch `cloudflare/**` (or manual run via `workflow_dispatch`)

Set these GitHub repository secrets first:

| Secret | Description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | API token with Cloudflare Pages deploy permissions |
| `CLOUDFLARE_ACCOUNT_ID` | Your Cloudflare account ID |
| `CF_PAGES_PROJECT_NAME` | Existing Cloudflare Pages project name |

After secrets are set, each qualifying push runs:

```bash
wrangler pages deploy cloudflare --project-name "$CF_PAGES_PROJECT_NAME" --branch "$GITHUB_REF_NAME"
```

This keeps deployment inside GitHub CI and avoids local `wrangler login`.

---

## Custom domain

Cloudflare Pages → your project → **Custom domains** → Add domain.
Free SSL included.

---

## Free advisor quips via `_worker.js` + Workers AI

The `_worker.js` runtime generates the funny quip text using
**Gemma 3 12B** on Workers AI — completely free, no user key consumed.

**Setup (Settings → Functions in your Pages project):**

1. **AI binding** — Variable name: `AI` (Workers AI — runs Gemma inference)
2. **KV binding** — Create a KV namespace (e.g. `tokeneyes-quips`), then bind it with variable name: `QUIPS_KV`

Both are optional and degrade gracefully:

| AI binding | KV binding | Behaviour |
|---|---|---|
| ✅ | ✅ | Gemma generates quip → saves to pool → reuses pool when quota hits |
| ✅ | ❌ | Gemma generates quip, pool not saved |
| ❌ | ✅ | Serves from saved pool only |
| ❌ | ❌ | Falls back to 25 hardcoded static quips (always works) |

The `/advisor` endpoint is tried first by the browser; if it fails at any point the UI silently falls back to the user's chosen vision provider. No downtime either way.

> **Model:** `@cf/google/gemma-4-26b-a4b-it` — update `ADVISOR_MODEL` in
> `_worker.js` if you want to switch models from the [Workers AI catalog](https://developers.cloudflare.com/workers-ai/models/).

> **Only the quip text is generated here.** Vision (price extraction from the image)
> always uses the user's own API key client-side — it never touches this function.

---

## Password-protected shared key proxy (`/proxy`)

The `_worker.js` `/proxy` route lets the deployer share API access with trusted
people via a single password — no user account required.

**How it works:**
1. User selects **Shared key** in the Access mode pills and types the password
2. All vision and quip calls are routed through `POST /proxy` instead of going to APIs directly
3. The proxy validates the password (timing-safe) and calls providers in order:
   **Gemini → OpenRouter → NVIDIA → Cloudflare Workers AI REST** — first success wins

**Setup (Pages → Settings → Environment Variables, mark each as Encrypted):**

| Secret name | Description |
|---|---|
| `PROXY_PASSWORD` | Shared password — tell your friends this value |
| `GEMINI_API_KEY` | Your Gemini API key (primary) |
| `OPENROUTER_API_KEY` | Your OpenRouter API key (fallback) |
| `NVIDIA_API_KEY` | Your NVIDIA NIM API key (fallback) |
| `CF_ACCOUNT_ID` | Your Cloudflare account ID (optional 4th fallback) |
| `CF_API_TOKEN` | Your Cloudflare API token (optional 4th fallback) |

All secrets are optional individually — at least one provider secret plus `PROXY_PASSWORD` must be set.
If a provider is not configured its step is skipped silently.

**Security notes:**
- `PROXY_PASSWORD` is compared with a constant-time XOR loop — immune to timing attacks
- Image data and prompts are processed server-side; nothing is logged beyond normal CF access logs
- Rate limit `POST /proxy` with a Cloudflare Rate Limiting rule if you're worried about abuse

---

## No backend for vision (own key mode)

All vision/price calls go **directly from the user's browser** to:
- `https://generativelanguage.googleapis.com` (Gemini)
- `https://openrouter.ai` (OpenRouter)
- `https://api.cloudflare.com` (Cloudflare Workers AI — user's own `ACCOUNT_ID:TOKEN`)

API keys are **never sent to any TokenEyes server** in own-key mode.

---

## Security headers

The `_headers` file sets:
- `Content-Security-Policy` — allowlist Gemini + OpenRouter + Cloudflare AI endpoints
- `Permissions-Policy` — camera enabled, everything else locked
- `X-Frame-Options` — no embedding in iframes
- `Referrer-Policy` — strict origin, so no key leaks in Referer headers

---

## API keys for users

| Provider | Free tier | Get key |
|---|---|---|
| Gemini | Yes (Gemini 2.0 Flash free) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| OpenRouter | Yes (several free models) | [openrouter.ai/keys](https://openrouter.ai/keys) |
| NVIDIA NIM | Yes (API trial/free endpoints) | [build.nvidia.com](https://build.nvidia.com/) |

Recommend telling users to generate a **restricted key** (Gemini lets you restrict by HTTP referrer or IP).
