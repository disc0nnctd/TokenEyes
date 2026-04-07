// Cloudflare Pages Function — password-protected proxy for deployer's API keys
// POST /proxy  {password, image_b64?, mime?, prompt, is_text}
// Returns {text, provider}
//
// Secrets (Pages → Settings → Environment Variables → mark as Encrypted):
//   PROXY_PASSWORD      — shared password for access (required)
//   GEMINI_API_KEY      — deployer's Gemini API key
//   OPENROUTER_API_KEY  — deployer's OpenRouter API key
//   NVIDIA_API_KEY      — deployer's NVIDIA NIM API key
//   CF_ACCOUNT_ID       — deployer's Cloudflare account ID (optional 4th fallback)
//   CF_API_TOKEN        — deployer's Cloudflare API token  (optional 4th fallback)
//
// Fallback chain: Gemini → OpenRouter → NVIDIA → Cloudflare Workers AI REST
// Missing secrets are skipped silently — at least one must be configured.

const GEMINI_VISION_MODEL = 'gemini-2.5-flash';
const GEMINI_TEXT_MODEL   = 'gemini-2.5-flash';
const OR_VISION_MODEL     = 'openrouter/auto';
const OR_TEXT_MODEL       = 'openrouter/auto';
const NVIDIA_VISION_MODEL = 'google/gemma-3-27b-it';
const NVIDIA_TEXT_MODEL   = 'deepseek-ai/deepseek-v3.2';
const CF_VISION_MODEL     = '@cf/meta/llama-3.2-11b-vision-instruct';
const CF_TEXT_MODEL       = '@cf/meta/llama-3.1-8b-instruct';
const NVIDIA_BASE         = 'https://integrate.api.nvidia.com/v1';
const OR_BASE             = 'https://openrouter.ai/api/v1';
const GEMINI_BASE         = 'https://generativelanguage.googleapis.com/v1beta/models';

export async function onRequestPost(context) {
  const { request, env } = context;
  const referer =
    request.headers.get('Origin') ||
    request.headers.get('Referer') ||
    'https://token-eyes.pages.dev';

  let body;
  try { body = await request.json(); }
  catch { return json({ error: 'Invalid JSON' }, 400); }

  const { password, image_b64, mime, prompt, is_text } = body;

  if (!password || typeof password !== 'string') return json({ error: 'Missing password' }, 400);
  if (!prompt   || typeof prompt   !== 'string') return json({ error: 'Missing prompt'   }, 400);
  if (!is_text && (!image_b64 || !mime))         return json({ error: 'Missing image'     }, 400);

  if (!env.PROXY_PASSWORD) return json({ error: 'Proxy not configured' }, 503);
  if (!timingSafeEqual(password, env.PROXY_PASSWORD)) return json({ error: 'Invalid password' }, 401);

  // ── Fallback chain ────────────────────────────────────────────────────────
  const attempts = [];

  if (env.GEMINI_API_KEY) {
    try {
      const text = is_text
        ? await geminiText(env.GEMINI_API_KEY, prompt)
        : await geminiVision(env.GEMINI_API_KEY, image_b64, mime, prompt);
      if (text) return json({ text, provider: 'gemini' });
      attempts.push('gemini:empty');
    } catch (e) {
      const msg = e?.message || String(e);
      attempts.push(`gemini:${msg}`);
      console.log('proxy: gemini failed', msg);
    }
  } else {
    attempts.push('gemini:not_configured');
  }

  if (env.OPENROUTER_API_KEY) {
    try {
      const text = is_text
        ? await orText(env.OPENROUTER_API_KEY, OR_TEXT_MODEL, prompt, referer)
        : await orVision(env.OPENROUTER_API_KEY, OR_VISION_MODEL, image_b64, mime, prompt, referer);
      if (text) return json({ text, provider: 'openrouter' });
      attempts.push('openrouter:empty');
    } catch (e) {
      const msg = e?.message || String(e);
      attempts.push(`openrouter:${msg}`);
      console.log('proxy: openrouter failed', msg);
    }
  } else {
    attempts.push('openrouter:not_configured');
  }

  if (env.NVIDIA_API_KEY) {
    try {
      const text = is_text
        ? await nvidiaText(env.NVIDIA_API_KEY, NVIDIA_TEXT_MODEL, prompt)
        : await nvidiaVision(env.NVIDIA_API_KEY, NVIDIA_VISION_MODEL, image_b64, mime, prompt);
      if (text) return json({ text, provider: 'nvidia' });
      attempts.push('nvidia:empty');
    } catch (e) {
      const msg = e?.message || String(e);
      attempts.push(`nvidia:${msg}`);
      console.log('proxy: nvidia failed', msg);
    }
  } else {
    attempts.push('nvidia:not_configured');
  }

  if (env.CF_ACCOUNT_ID && env.CF_API_TOKEN) {
    try {
      const text = is_text
        ? await cfText(env.CF_ACCOUNT_ID, env.CF_API_TOKEN, prompt)
        : await cfVision(env.CF_ACCOUNT_ID, env.CF_API_TOKEN, image_b64, mime, prompt);
      if (text) return json({ text, provider: 'cloudflare' });
      attempts.push('cloudflare:empty');
    } catch (e) {
      const msg = e?.message || String(e);
      attempts.push(`cloudflare:${msg}`);
      console.log('proxy: cloudflare failed', msg);
    }
  } else {
    attempts.push('cloudflare:not_configured');
  }

  const detail = attempts.join('; ');
  console.log('proxy: all providers unavailable', detail);
  return json({ error: `All providers unavailable (${detail})` }, 503);
}

export function onRequestGet() { return json({ error: 'POST only' }, 405); }

// ── Timing-safe comparison ────────────────────────────────────────────────────
function timingSafeEqual(a, b) {
  const ea = new TextEncoder().encode(a);
  const eb = new TextEncoder().encode(b);
  // Always iterate over the longer to prevent length-based short-circuit
  const len = Math.max(ea.length, eb.length);
  let diff = ea.length ^ eb.length; // non-zero if lengths differ
  for (let i = 0; i < len; i++) diff |= (ea[i] ?? 0) ^ (eb[i] ?? 0);
  return diff === 0;
}

// ── Gemini ────────────────────────────────────────────────────────────────────
async function geminiVision(key, b64, mime, prompt) {
  const r = await fetch(
    `${GEMINI_BASE}/${GEMINI_VISION_MODEL}:generateContent?key=${encodeURIComponent(key)}`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ inline_data: { mime_type: mime, data: b64 } }, { text: prompt }] }], generationConfig: { temperature: 0.1, maxOutputTokens: 1024 } }) }
  );
  if (!r.ok) throw new Error(`Gemini ${r.status}`);
  const d = await r.json();
  return (d?.candidates?.[0]?.content?.parts?.[0]?.text ?? '').trim() || null;
}

async function geminiText(key, prompt) {
  const r = await fetch(
    `${GEMINI_BASE}/${GEMINI_TEXT_MODEL}:generateContent?key=${encodeURIComponent(key)}`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.9, maxOutputTokens: 256 } }) }
  );
  if (!r.ok) throw new Error(`Gemini text ${r.status}`);
  const d = await r.json();
  return (d?.candidates?.[0]?.content?.parts?.[0]?.text ?? '').trim() || null;
}

// ── OpenRouter ────────────────────────────────────────────────────────────────
async function orVision(key, model, b64, mime, prompt, referer) {
  const r = await fetch(`${OR_BASE}/chat/completions`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}`, 'HTTP-Referer': referer, 'X-Title': 'TokenEyes' },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: [{ type: 'image_url', image_url: { url: `data:${mime};base64,${b64}` } }, { type: 'text', text: prompt }] }], max_tokens: 1024, temperature: 0.1 }) }
  );
  if (!r.ok) throw new Error(`OR ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}

async function orText(key, model, prompt, referer) {
  const r = await fetch(`${OR_BASE}/chat/completions`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}`, 'HTTP-Referer': referer, 'X-Title': 'TokenEyes' },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 256, temperature: 0.9 }) }
  );
  if (!r.ok) throw new Error(`OR text ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}

// ── NVIDIA NIM ────────────────────────────────────────────────────────────────
async function nvidiaVision(key, model, b64, mime, prompt) {
  const r = await fetch(`${NVIDIA_BASE}/chat/completions`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: [{ type: 'image_url', image_url: { url: `data:${mime};base64,${b64}` } }, { type: 'text', text: prompt }] }], max_tokens: 1024, temperature: 0.1 }) }
  );
  if (!r.ok) throw new Error(`NVIDIA ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}

async function nvidiaText(key, model, prompt) {
  const r = await fetch(`${NVIDIA_BASE}/chat/completions`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 256, temperature: 0.9 }) }
  );
  if (!r.ok) throw new Error(`NVIDIA text ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}

// ── Cloudflare Workers AI (REST) ──────────────────────────────────────────────
const cfUrl = (acct, model) =>
  `https://api.cloudflare.com/client/v4/accounts/${acct}/ai/run/${encodeURIComponent(model)}`;

async function cfVision(acct, token, b64, mime, prompt) {
  const r = await fetch(cfUrl(acct, CF_VISION_MODEL),
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ messages: [{ role: 'user', content: [{ type: 'image_url', image_url: { url: `data:${mime};base64,${b64}` } }, { type: 'text', text: prompt }] }], max_tokens: 1024 }) }
  );
  if (!r.ok) throw new Error(`CF ${r.status}`);
  const d = await r.json();
  return (d?.result?.response ?? '').trim() || null;
}

async function cfText(acct, token, prompt) {
  const r = await fetch(cfUrl(acct, CF_TEXT_MODEL),
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ messages: [{ role: 'user', content: prompt }], max_tokens: 256 }) }
  );
  if (!r.ok) throw new Error(`CF text ${r.status}`);
  const d = await r.json();
  return (d?.result?.response ?? '').trim() || null;
}

// ── Response helper ───────────────────────────────────────────────────────────
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
