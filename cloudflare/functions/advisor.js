// Cloudflare Pages Function — generates advisor quips using Workers AI (free, no user key needed)
//
// Bindings needed in Pages project settings (Settings → Functions):
//   AI binding    → variable name: AI          (Workers AI — for Gemma inference)
//   KV binding    → variable name: QUIPS_KV    (KV namespace — for quip pool cache)
//
// Both bindings are optional and degrade gracefully:
//   - No AI binding  → serve from pool / static fallback
//   - No KV binding  → serve from static fallback only, pool not saved
//
// Model: @cf/google/gemma-4-26b-a4b-it (Gemma 4 26B — added to CF catalog April 2026)
// → Update ADVISOR_MODEL if a newer model appears in the CF Workers AI catalog:
//   https://developers.cloudflare.com/workers-ai/models/
//
// What this generates: ONLY the funny one-liner quip/meme text.
// Vision (price extraction) is done client-side with the user's own API key — never touches this function.

const ADVISOR_MODEL = '@cf/google/gemma-4-26b-a4b-it';
const MAX_PROMPT_LEN = 500;
const POOL_KEY = 'quip_pool';
const POOL_MAX = 300; // keep at most this many saved quips

// Static fallback pool — used when AI quota is exhausted AND KV pool is empty.
// These are generic enough to work without knowing the specific item or price.
const STATIC_POOL = [
  "Your wallet called. It's filing for emotional damages.",
  "That's enough tokens to make an AI write your entire personality.",
  "Somewhere, a GPU is crying into its cooling fan.",
  "Bold choice. Have you considered hoarding tokens instead?",
  "That's not a purchase, that's a hostage situation with your bank account.",
  "You could've trained a small language model for that price.",
  "At this point just buy a GPU and become the AI.",
  "The tokens you could've had are watching from the other side.",
  "An AI could've written 10,000 mediocre LinkedIn posts for that.",
  "Technically you could generate an entire TV season instead.",
  "That's enough reasoning tokens to solve a problem that doesn't exist yet.",
  "Some people buy experiences. You bought this.",
  "Your financial advisor has left the chat.",
  "In token terms, this is basically a war crime against your wallet.",
  "An LLM could've talked you out of this for literally $0.003.",
  "Not judging. But also, definitely judging.",
  "That's enough tokens to gaslight an entire chatbot fleet.",
  "Did the AI guilt-trip you into this? Because same.",
  "The opportunity cost is giving me an existential crisis.",
  "An AI could've written every excuse you've ever needed for that.",
  "Cheaper to mine Bitcoin on a potato.",
  "Imagine hiring 1,000 interns instead. You didn't. Here we are.",
  "That's a lot of tokens. Your future self has thoughts.",
  "Token math doesn't lie, but it does judge.",
  "This is why we can't have nice compute.",
];

export async function onRequestPost(context) {
  const { request, env } = context;

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'Invalid JSON body' }, 400);
  }

  const { prompt } = body;
  if (!prompt || typeof prompt !== 'string' || prompt.length > MAX_PROMPT_LEN) {
    return json({ error: 'prompt must be a non-empty string under 500 chars' }, 400);
  }

  // 1. Try Gemma via Workers AI
  if (env.AI) {
    try {
      const result = await env.AI.run(ADVISOR_MODEL, {
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 150,
      });
      const text = (result?.response ?? '').trim();
      if (text) {
        // Save to KV pool (fire-and-forget — don't block the response)
        if (env.QUIPS_KV) saveToPool(env.QUIPS_KV, text);
        return json({ text, source: 'ai' });
      }
    } catch {
      // Quota exhausted or model error — fall through to pool
    }
  }

  // 2. AI unavailable or quota hit — serve a random saved quip from KV pool
  if (env.QUIPS_KV) {
    const pooled = await getFromPool(env.QUIPS_KV);
    if (pooled) return json({ text: pooled, source: 'pool' });
  }

  // 3. Last resort — static hardcoded pool (always works, no bindings needed)
  const text = STATIC_POOL[Math.floor(Math.random() * STATIC_POOL.length)];
  return json({ text, source: 'static' });
}

// Reject non-POST verbs cleanly
export function onRequestGet() {
  return json({ error: 'POST only' }, 405);
}

// ── KV pool helpers ──────────────────────────────────────────────────────────

async function saveToPool(kv, quip) {
  try {
    const raw = await kv.get(POOL_KEY);
    const pool = raw ? JSON.parse(raw) : [];
    if (!pool.includes(quip)) {
      pool.push(quip);
      // Trim oldest entries if over cap
      if (pool.length > POOL_MAX) pool.splice(0, pool.length - POOL_MAX);
      // Use waitUntil if available, else just fire
      await kv.put(POOL_KEY, JSON.stringify(pool));
    }
  } catch {}
}

async function getFromPool(kv) {
  try {
    const raw = await kv.get(POOL_KEY);
    if (!raw) return null;
    const pool = JSON.parse(raw);
    if (!pool.length) return null;
    return pool[Math.floor(Math.random() * pool.length)];
  } catch { return null; }
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
