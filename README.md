# TokenEyes

**See the world in AI tokens.**

Point your camera at any price tag. Find out what it costs in AI tokens.
That $6 latte? 1.2 million Claude Sonnet tokens.

→ **[Try it live](https://tokeneyes.dev)** — no signup, no backend, keys stay in your browser.

---

## What It Does

1. **Snap or upload** a photo of anything with a price (tag, menu, receipt, screen)
2. **Vision AI reads the price** — or guesses it if there's no visible tag
3. **Instant token breakdown** across 10 AI models with a culturally-aware one-liner

---

## Supported Vision Providers

Bring your own key — all have free tiers:

| Provider | Free tier | Get key |
|---|---|---|
| Google Gemini | Yes (Gemini 2.5 Flash) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| OpenRouter | Yes (Qwen VL, Gemma 3, Llama Vision, more) | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Cloudflare Workers AI | Yes (Llama 4, Gemma 4) | [dash.cloudflare.com](https://dash.cloudflare.com) |

---

## Pricing Models

| Model | Input $/1M | Output $/1M |
|---|---|---|
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| Claude Opus 4.6 | $5.00 | $25.00 |
| Claude Haiku 4.5 | $1.00 | $5.00 |
| Gemini 2.5 Pro | $1.25 | $10.00 |
| Gemini 2.5 Flash | $0.30 | $2.50 |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 |
| GPT-5 | $1.25 | $10.00 |
| GPT-4o | $2.50 | $10.00 |
| o4-mini | $1.10 | $4.40 |
| GPT-4o Mini | $0.15 | $0.60 |

---

## Python CLI

```bash
pip install -e .

tokeneyes photo.jpg              # read price from image
tokeneyes shoe.jpg --guess       # AI guesses the price (no visible tag)
tokeneyes --price 5.99           # skip vision, just convert
tokeneyes --list-models          # show all supported models
tokeneyes-web                    # start local web UI (port 8000)
```

Requires `GEMINI_API_KEY` or `OPENROUTER_API_KEY` in your environment or a `.env` file.

---

## Self-Host the Web App

The web app is a single static HTML file — no build step, no server.

```bash
git clone https://github.com/disc0nnctd/TokenEyes
cd TokenEyes/cloudflare
python3 -m http.server 3000
```

Deploy to Cloudflare Pages by dragging the `cloudflare/` folder to [pages.cloudflare.com](https://pages.cloudflare.com).
See [cloudflare/DEPLOY.md](./cloudflare/DEPLOY.md) for full instructions including optional free quip generation via Workers AI.

---

## Privacy

- Keys are **memory-only** in your browser — gone when you close the tab
- All API calls go **directly from your browser** to the provider — no TokenEyes server in the path
- Nothing is logged or stored by us

---

## License

MIT
