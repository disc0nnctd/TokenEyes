// Cloudflare Pages Function — returns the visitor's country code for free.
// Cloudflare injects request.cf.country (ISO 3166-1 alpha-2) on every request.
// No bindings required. Used by Normal mode to make quips culturally relevant.

export async function onRequestGet(context) {
  const country = context.request.cf?.country ?? null;
  return new Response(JSON.stringify({ country }), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}
