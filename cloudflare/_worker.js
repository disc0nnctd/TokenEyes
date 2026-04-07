// _worker.js — handles all dynamic routes; falls back to static assets
// Routes: POST /proxy, POST /advisor, GET /country
// Bindings (set in Pages → Settings → Variables & Secrets):
//   AI           — Workers AI (for Gemma quips in /advisor)
//   QUIPS_KV     — KV namespace (quip pool cache)
//   PROXY_PASSWORD, GEMINI_API_KEY, OPENROUTER_API_KEY, NVIDIA_API_KEY — for /proxy
//   CF_ACCOUNT_ID, CF_API_TOKEN — optional 4th fallback in /proxy
//   QUIP_COUNT   — number of quips to generate per scan (default: 3)

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/proxy')   return handleProxy(request, env);
    if (url.pathname === '/advisor') return handleAdvisor(request, env);
    if (url.pathname === '/country') return handleCountry(request);
    if (url.pathname === '/config')  return handleConfig(env);

    return env.ASSETS.fetch(request);
  },
};

// ══ /config ═══════════════════════════════════════════════════════════════════
function handleConfig(env) {
  const quip_count = Math.min(10, Math.max(1, parseInt(env.QUIP_COUNT) || 3));
  return json({ quip_count });
}

// ══ /country ══════════════════════════════════════════════════════════════════
function handleCountry(request) {
  const country = request.cf?.country ?? null;
  return json({ country });
}

// ══ /advisor ══════════════════════════════════════════════════════════════════
const ADVISOR_MODEL = '@cf/google/gemma-4-26b-a4b-it';
const MAX_PROMPT_LEN = 500;
const POOL_KEY = 'quip_pool';
const POOL_MAX = 300;
const STATIC_POOL = [
  "Your inbox could've been empty. Instead, you bought this.",
  "This price tag just ate a perfectly good proposal sprint.",
  "A support backlog somewhere would love this budget.",
  "That could've been a lot of spreadsheet cleanup and closure.",
  "You didn't buy a thing. You cancelled some future productivity.",
  "This is why the ops team can't have nice automation.",
  "A stack of first drafts died for this purchase.",
  "That spend had serious meeting-summary potential.",
  "Your admin queue just watched this happen in silence.",
  "This item is wearing a follow-up email budget.",
  "Congrats on converting workflow budget into an object.",
  "A research brief factory could've eaten on this.",
  "This could've been a cleaner CRM and a nicer afternoon.",
  "That's at least one tragic spreadsheet before-and-after.",
  "Your proposal pipeline just took emotional damage.",
  "This is basically anti-automation merchandise.",
  "A lot of tedious work could've quietly disappeared for that.",
  "That spend belongs in a before/after productivity meme.",
  "The ops budget is judging this purchase from a distance.",
  "You bought this with money that had admin-killing potential.",
  "That price is one very preventable backlog.",
  "Some poor workflow just lost its upgrade budget.",
  "This could've been support replies with suspiciously good grammar.",
  "That spend was one dashboard cleanup away from greatness.",
  "The spreadsheet won zero games here today.",
];

async function handleAdvisor(request, env) {
  if (request.method !== 'POST') return json({ error: 'POST only' }, 405);
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON body' }, 400); }
  const { prompt } = body;
  if (!prompt || typeof prompt !== 'string' || prompt.length > MAX_PROMPT_LEN)
    return json({ error: 'prompt must be a non-empty string under 500 chars' }, 400);

  if (env.AI) {
    try {
      const result = await env.AI.run(ADVISOR_MODEL, {
        messages: [{ role: 'user', content: prompt }], max_tokens: 150,
      });
      const text = (result?.response ?? '').trim();
      if (text) {
        if (env.QUIPS_KV) saveToPool(env.QUIPS_KV, text);
        return json({ text, source: 'ai' });
      }
    } catch { /* quota or error — fall through */ }
  }

  if (env.QUIPS_KV) {
    const pooled = await getFromPool(env.QUIPS_KV);
    if (pooled) return json({ text: pooled, source: 'pool' });
  }

  const text = STATIC_POOL[Math.floor(Math.random() * STATIC_POOL.length)];
  return json({ text, source: 'static' });
}

async function saveToPool(kv, quip) {
  try {
    const raw = await kv.get(POOL_KEY);
    const pool = raw ? JSON.parse(raw) : [];
    if (!pool.includes(quip)) {
      pool.push(quip);
      if (pool.length > POOL_MAX) pool.splice(0, pool.length - POOL_MAX);
      await kv.put(POOL_KEY, JSON.stringify(pool));
    }
  } catch {}
}
async function getFromPool(kv) {
  try {
    const raw = await kv.get(POOL_KEY);
    if (!raw) return null;
    const pool = JSON.parse(raw);
    return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
  } catch { return null; }
}

// ══ /proxy ════════════════════════════════════════════════════════════════════
const GEMINI_BASE = 'https://generativelanguage.googleapis.com/v1beta/models';
const GEMINI_MODEL = 'gemini-2.5-flash';
const OR_BASE = 'https://openrouter.ai/api/v1';
const OR_VISION_MODEL = 'openrouter/auto';
const OR_TEXT_MODEL = 'openrouter/auto';
const NVIDIA_BASE = 'https://integrate.api.nvidia.com/v1';
const NVIDIA_VISION_MODEL = 'google/gemma-3-27b-it';
const NVIDIA_TEXT_MODEL = 'deepseek-ai/deepseek-v3.2';
const CF_VISION_MODEL = '@cf/meta/llama-3.2-11b-vision-instruct';
const CF_TEXT_MODEL = '@cf/meta/llama-3.1-8b-instruct';

async function handleProxy(request, env) {
  if (request.method !== 'POST') return json({ error: 'POST only' }, 405);
  let body;
  try { body = await request.json(); } catch { return json({ error: 'Invalid JSON' }, 400); }

  const { password, image_b64, mime, prompt, is_text } = body;
  if (!password || typeof password !== 'string') return json({ error: 'Missing password' }, 400);
  if (!prompt   || typeof prompt   !== 'string') return json({ error: 'Missing prompt'   }, 400);
  if (!is_text && (!image_b64 || !mime))         return json({ error: 'Missing image'     }, 400);

  if (!env.PROXY_PASSWORD) return json({ error: 'Proxy not configured' }, 503);
  if (!timingSafeEqual(password, env.PROXY_PASSWORD)) return json({ error: 'Invalid password' }, 401);

  const referer =
    request.headers.get('Origin') ||
    request.headers.get('Referer') ||
    'https://token-eyes.pages.dev';
  const attempts = [];

  if (env.GEMINI_API_KEY) {
    try {
      const text = is_text
        ? await geminiText(env.GEMINI_API_KEY, prompt)
        : await geminiVision(env.GEMINI_API_KEY, image_b64, mime, prompt);
      if (text) return json({ text, provider: 'gemini' });
      attempts.push('gemini:empty');
    } catch (e) {
      attempts.push(`gemini:${e?.message || String(e)}`);
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
      attempts.push(`openrouter:${e?.message || String(e)}`);
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
      attempts.push(`nvidia:${e?.message || String(e)}`);
    }
  } else {
    attempts.push('nvidia:not_configured');
  }
  if (env.CF_ACCOUNT_ID && env.CF_API_TOKEN) {
    try {
      const cfUrl = (model) =>
        `https://api.cloudflare.com/client/v4/accounts/${env.CF_ACCOUNT_ID}/ai/run/${encodeURIComponent(model)}`;
      const text = is_text
        ? await cfText(env.CF_API_TOKEN, cfUrl(CF_TEXT_MODEL), prompt)
        : await cfVision(env.CF_API_TOKEN, cfUrl(CF_VISION_MODEL), image_b64, mime, prompt);
      if (text) return json({ text, provider: 'cloudflare' });
      attempts.push('cloudflare:empty');
    } catch (e) {
      attempts.push(`cloudflare:${e?.message || String(e)}`);
    }
  } else {
    attempts.push('cloudflare:not_configured');
  }

  const detail = attempts.join('; ');
  console.log('proxy: all providers unavailable', detail);
  return json({ error: `All providers unavailable (${detail})` }, 503);
}

function timingSafeEqual(a, b) {
  const ea = new TextEncoder().encode(a);
  const eb = new TextEncoder().encode(b);
  const len = Math.max(ea.length, eb.length);
  let diff = ea.length ^ eb.length;
  for (let i = 0; i < len; i++) diff |= (ea[i] ?? 0) ^ (eb[i] ?? 0);
  return diff === 0;
}

async function geminiVision(key, b64, mime, prompt) {
  const r = await fetch(`${GEMINI_BASE}/${GEMINI_MODEL}:generateContent?key=${encodeURIComponent(key)}`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ inline_data: { mime_type: mime, data: b64 } }, { text: prompt }] }], generationConfig: { temperature: 0.1, maxOutputTokens: 1024 } }) });
  if (!r.ok) throw new Error(`Gemini ${r.status}`);
  const d = await r.json();
  return (d?.candidates?.[0]?.content?.parts?.[0]?.text ?? '').trim() || null;
}
async function geminiText(key, prompt) {
  const r = await fetch(`${GEMINI_BASE}/${GEMINI_MODEL}:generateContent?key=${encodeURIComponent(key)}`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.9, maxOutputTokens: 256 } }) });
  if (!r.ok) throw new Error(`Gemini text ${r.status}`);
  const d = await r.json();
  return (d?.candidates?.[0]?.content?.parts?.[0]?.text ?? '').trim() || null;
}

async function orVision(key, model, b64, mime, prompt, referer) {
  const r = await fetch(`${OR_BASE}/chat/completions`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}`, 'HTTP-Referer': referer, 'X-Title': 'TokenEyes' },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: [{ type: 'image_url', image_url: { url: `data:${mime};base64,${b64}` } }, { type: 'text', text: prompt }] }], max_tokens: 1024, temperature: 0.1 }) });
  if (!r.ok) throw new Error(`OR ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}
async function orText(key, model, prompt, referer) {
  const r = await fetch(`${OR_BASE}/chat/completions`,
    { method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}`, 'HTTP-Referer': referer, 'X-Title': 'TokenEyes' },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 256, temperature: 0.9 }) });
  if (!r.ok) throw new Error(`OR text ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}

async function nvidiaVision(key, model, b64, mime, prompt) {
  const r = await fetch(`${NVIDIA_BASE}/chat/completions`,
    { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: [{ type: 'image_url', image_url: { url: `data:${mime};base64,${b64}` } }, { type: 'text', text: prompt }] }], max_tokens: 1024, temperature: 0.1 }) });
  if (!r.ok) throw new Error(`NVIDIA ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}
async function nvidiaText(key, model, prompt) {
  const r = await fetch(`${NVIDIA_BASE}/chat/completions`,
    { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${key}` },
      body: JSON.stringify({ model, messages: [{ role: 'user', content: prompt }], max_tokens: 256, temperature: 0.9 }) });
  if (!r.ok) throw new Error(`NVIDIA text ${r.status}`);
  const d = await r.json();
  return (d?.choices?.[0]?.message?.content ?? '').trim() || null;
}

async function cfVision(token, url, b64, mime, prompt) {
  const r = await fetch(url,
    { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ messages: [{ role: 'user', content: [{ type: 'image_url', image_url: { url: `data:${mime};base64,${b64}` } }, { type: 'text', text: prompt }] }], max_tokens: 1024 }) });
  if (!r.ok) throw new Error(`CF ${r.status}`);
  const d = await r.json();
  return (d?.result?.response ?? '').trim() || null;
}
async function cfText(token, url, prompt) {
  const r = await fetch(url,
    { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ messages: [{ role: 'user', content: prompt }], max_tokens: 256 }) });
  if (!r.ok) throw new Error(`CF text ${r.status}`);
  const d = await r.json();
  return (d?.result?.response ?? '').trim() || null;
}

// ── helpers ────────────────────────────────────────────────────────────────────
function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}
