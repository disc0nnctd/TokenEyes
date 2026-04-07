# TokenEyes — Cloudflare Deployment

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

## No Cloudflare Worker needed

All LLM calls go **directly from the user's browser** to:
- `https://generativelanguage.googleapis.com` (Gemini)
- `https://openrouter.ai` (OpenRouter)

API keys are **never sent to any TokenEyes server**. There is no backend.

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
