# TokenEyes — Cloudflare Deployment

## Security model (important for self-hosters)

- **User API keys** — entered in-browser, memory only, never sent to any TokenEyes server.
  All vision calls go directly from the user's browser to Gemini / OpenRouter / CF Workers AI.
- **Your Workers AI binding** — used only by the `/advisor` and `/country` Pages Functions.
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

1. Push `tokeneyes/` to GitHub
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
wrangler pages deploy cloudflare/ --project-name tokeneyes
```

---

## Custom domain

Cloudflare Pages → your project → **Custom domains** → Add domain.
Free SSL included.

---

## Free advisor quips via Pages Functions + Workers AI

The `functions/advisor.js` Pages Function generates the funny quip text using
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

> **Model:** `@hf/google/gemma-3-12b-it` — update `ADVISOR_MODEL` in
> `functions/advisor.js` once Gemma 4 appears in the [Workers AI catalog](https://developers.cloudflare.com/workers-ai/models/).

> **Only the quip text is generated here.** Vision (price extraction from the image)
> always uses the user's own API key client-side — it never touches this function.

---

## No backend for vision

All vision/price calls go **directly from the user's browser** to:
- `https://generativelanguage.googleapis.com` (Gemini)
- `https://openrouter.ai` (OpenRouter)
- `https://api.cloudflare.com` (Cloudflare Workers AI — user's own key)

API keys are **never sent to any TokenEyes server**.

---

## Security headers

The `_headers` file sets:
- `Content-Security-Policy` — allowlist only Gemini + OpenRouter API domains
- `Permissions-Policy` — camera enabled, everything else locked
- `X-Frame-Options` — no embedding in iframes
- `Referrer-Policy` — strict origin, so no key leaks in Referer headers

---

## API keys for users

| Provider | Free tier | Get key |
|---|---|---|
| Gemini | Yes (Gemini 2.0 Flash free) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| OpenRouter | Yes (several free models) | [openrouter.ai/keys](https://openrouter.ai/keys) |

Recommend telling users to generate a **restricted key** (Gemini lets you restrict by HTTP referrer or IP).
