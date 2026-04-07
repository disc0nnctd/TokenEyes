# CLAUDE.md — TokenEyes (Claude-specific)

Start with [AGENTS.md](./AGENTS.md) for architecture, file map, and common tasks.
This file adds Claude Code-specific guidance on top of that baseline.

---

## Priorities

1. `cloudflare/` is the main product. Changes here have the most impact.
2. `tokeneyes/` Python package is secondary — keep it working but don't over-engineer it.
3. `web/` is local dev only — minimum viable, no new features.

## Style

- No docstrings, comments, or type annotations on code you didn't change.
- No abstractions for one-off operations. Three similar lines > premature helper.
- No backwards-compat shims — just change the code.
- JS in `cloudflare/index.html` is deliberately compact (single file, no build step). Keep it that way.

## Before Editing `cloudflare/index.html`

Always read the file first. It's a single ~850-line file. The structure is:
`<style>` → `<body>` HTML → `<script>` (state → DOM refs → event handlers → API functions → render).

Key state variables to be aware of: `provider`, `geminiVisionModel`, `cfVisionModel`, `orModel`, `simpleMode`, `detectedCountry`, `imageB64`.

## Keeping Prices Current

Pricing data lives in two places — keep them in sync:
- `cloudflare/index.html` → `MODELS` array (JS)
- `tokeneyes/pricing.py` → `MODELS` dict (Python)

When updating, verify against the provider's official pricing page (links in AGENTS.md → Docs Graph).

## Security (Open Source Deployment)

This project will be publicly open-sourced. All API keys are user-supplied in-browser — none are baked into the code. The Pages Functions (`advisor.js`, `country.js`) use the **deployer's** Workers AI binding, not user keys. Never add hardcoded credentials, account IDs, or anything that would expose the deployer's identity. See security note in DEPLOY.md.

## Do Not

- Add `or_base_url` / custom endpoint parameters back — local model support was removed intentionally.
- Modify `cloudflare/_redirects` (must stay empty).
- Add new npm/build dependencies — the Cloudflare app is intentionally zero-build.
- Commit `.env` files.
