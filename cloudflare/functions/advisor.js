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
// What this generates: ONLY the short productivity-meme line.
// Vision (price extraction) is done client-side with the user's own API key — never touches this function.

const ADVISOR_MODEL = '@cf/google/gemma-4-26b-a4b-it';
const MAX_PROMPT_LEN = 500;
const POOL_KEY = 'quip_pool';
const POOL_MAX = 300; // keep at most this many saved quips

// Static fallback pool — used when AI quota is exhausted AND KV pool is empty.
// These stay grounded in budget/productivity tradeoffs instead of meme jokes.
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
