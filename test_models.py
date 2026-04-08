"""
Test different vision models on sampledata images and compare price identification.
Usage: python test_models.py [image_path]
"""
import os, sys, json, base64, time
from pathlib import Path

# Load keys from .env
env = {}
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

GEMINI_KEY    = env.get('GEMINI_API_KEY', '')
OR_KEY        = env.get('OPENROUTER_API_KEY', '')
NVIDIA_KEY    = env.get('NVIDIA_API_KEY', '')

IMAGE_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('sampledata/apple_watch.png')

PROMPT = '''Look at this image carefully.
- If a price tag, label, menu price, or receipt is visible: read it exactly. Set confidence to "read".
- If no price is visible: identify the main object as specifically as possible — include brand, model name, and generation or version if distinguishable. Search for its current retail price in USD. Set confidence to "estimated".
For "resale_usd": estimate secondhand selling price today. Null for consumables.

Return ONLY valid JSON (no markdown):
{"item":"Apple Watch Series 9 GPS 45mm","price":399,"currency":"USD","price_usd":399,"resale_usd":250,"confidence":"estimated"}'''

# ── helpers ───────────────────────────────────────────────────────────────────

def load_image(path: Path):
    mime_map = {'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.webp':'image/webp'}
    mime = mime_map.get(path.suffix.lower(), 'image/jpeg')
    b64 = base64.b64encode(path.read_bytes()).decode()
    return b64, mime

def parse_json(text):
    t = text.strip()
    if t.startswith('```'):
        t = '\n'.join(t.split('\n')[1:])
        t = t.rstrip('`').strip()
    import re
    m = re.search(r'\{[\s\S]*\}', t)
    if m: t = m.group(0)
    try: return json.loads(t)
    except: return None

def print_result(model_label, data, elapsed):
    if not data:
        print(f"  ✗ Failed to parse response")
        return
    item   = data.get('item', '?')
    price  = data.get('price_usd') or data.get('price')
    conf   = data.get('confidence', '?')
    resale = data.get('resale_usd')
    search = data.get('_used_search')
    tag    = ' [search]' if search else (' [fallback]' if search is False else '')
    print(f"  item     : {item}")
    print(f"  price_usd: ${price}  ({conf}){tag}")
    if resale: print(f"  resale   : ${resale}")
    print(f"  time     : {elapsed:.1f}s")

# ── Gemini ────────────────────────────────────────────────────────────────────

def test_gemini(model_id, b64, mime, with_search=True):
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_KEY}"
    def mk_body(search):
        body = {"contents": [{"parts": [{"inline_data": {"mime_type": mime, "data": b64}}, {"text": PROMPT}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}}
        if search: body["tools"] = [{"googleSearch": {}}]
        return json.dumps(body).encode()
    def do_call(search):
        req = urllib.request.Request(url, data=mk_body(search), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read())
        parts = d.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        return ''.join(p.get('text', '') for p in parts)
    try:
        t0 = time.time()
        text = do_call(with_search) if with_search else ''
        used_search = with_search
        if with_search and not text.strip():
            print("  (search returned empty, falling back to no-search)")
            text = do_call(False)
            used_search = False
        elapsed = time.time() - t0
        result = parse_json(text)
        if result: result['_used_search'] = used_search
        return result, elapsed
    except Exception as e:
        print(f"  ERROR: {e}")
        return None, 0

# ── OpenRouter ────────────────────────────────────────────────────────────────

def test_openrouter(model_id, b64, mime):
    import urllib.request
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": PROMPT}
        ]}],
        "max_tokens": 512, "temperature": 0.1
    }).encode()
    try:
        t0 = time.time()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OR_KEY}",
            "HTTP-Referer": "https://token-eyes.pages.dev",
            "X-Title": "TokenEyes"
        }, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        elapsed = time.time() - t0
        text = d.get('choices', [{}])[0].get('message', {}).get('content', '')
        return parse_json(text), elapsed
    except Exception as e:
        return None, 0

# ── NVIDIA NIM ────────────────────────────────────────────────────────────────

def test_nvidia(model_id, b64, mime):
    import urllib.request
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": PROMPT}
        ]}],
        "max_tokens": 512, "temperature": 0.1
    }).encode()
    try:
        t0 = time.time()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {NVIDIA_KEY}"
        }, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        elapsed = time.time() - t0
        text = d.get('choices', [{}])[0].get('message', {}).get('content', '')
        return parse_json(text), elapsed
    except Exception as e:
        return None, 0

# ── Run ───────────────────────────────────────────────────────────────────────

MODELS = [
    ("Gemini 2.5 Flash + search",     "gemini",      "gemini-2.5-flash"),
    ("Gemini 2.5 Pro + search",       "gemini",      "gemini-2.5-pro"),
    ("OpenRouter auto (free)",        "openrouter",  "openrouter/auto"),
    ("Gemma 3 27B (OpenRouter free)", "openrouter",  "google/gemma-3-27b-it:free"),
    ("Llama 4 Scout (NVIDIA free)",   "nvidia",      "meta/llama-4-scout-17b-16e-instruct"),
    ("Gemma 3 27B (NVIDIA free)",     "nvidia",      "google/gemma-3-27b-it"),
    ("Mistral Large 3 (NVIDIA free)", "nvidia",      "mistralai/mistral-large-3-675b-instruct-2512"),
]

print(f"\n{'='*60}")
print(f"Image: {IMAGE_PATH}")
print(f"{'='*60}\n")

b64, mime = load_image(IMAGE_PATH)

for label, provider, model_id in MODELS:
    print(f"▶ {label}")
    print(f"  model: {model_id}")
    if provider == "gemini" and not GEMINI_KEY:
        print("  ✗ No GEMINI_API_KEY"); print(); continue
    if provider == "openrouter" and not OR_KEY:
        print("  ✗ No OPENROUTER_API_KEY"); print(); continue
    if provider == "nvidia" and not NVIDIA_KEY:
        print("  ✗ No NVIDIA_API_KEY"); print(); continue

    if provider == "gemini":
        data, elapsed = test_gemini(model_id, b64, mime, with_search=True)
    elif provider == "openrouter":
        data, elapsed = test_openrouter(model_id, b64, mime)
    elif provider == "nvidia":
        data, elapsed = test_nvidia(model_id, b64, mime)

    print_result(label, data, elapsed)
    print()
