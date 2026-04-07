"""TokenEyes Web UI — FastAPI backend."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Load env from project root
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path.home() / ".tokeneyes.env")
load_dotenv()

app = FastAPI(title="TokenEyes", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/models")
async def list_models():
    from tokeneyes.pricing import MODELS, DISPLAY_NAMES
    return [
        {
            "id": model_id,
            "name": DISPLAY_NAMES.get(model_id, model_id),
            "input": prices["input"],
            "output": prices["output"],
            "reasoning": prices.get("reasoning"),
        }
        for model_id, prices in MODELS.items()
    ]


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    mode: str = Form("read"),          # "read" or "guess"
    backend: str = Form("auto"),       # "auto", "gemini", "openrouter"
    or_model: str = Form("google/gemini-2.0-flash-exp:free"),
    models: str = Form(""),            # comma-separated model IDs, empty = all
):
    from tokeneyes.vision import read_price, guess_price, generate_quip
    from tokeneyes.pricing import convert_all

    # Save upload to temp file
    suffix = Path(image.filename or "upload.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await image.read())
        tmp_path = tmp.name

    try:
        if mode == "guess":
            result = guess_price(tmp_path, backend=backend, or_model=or_model)
        else:
            result = read_price(tmp_path, backend=backend, or_model=or_model)
    finally:
        os.unlink(tmp_path)

    if result.price_usd is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_price",
                "message": f"Could not find a price in this image (confidence: {result.confidence}). Try 'Guess mode' instead.",
                "item": result.item,
            },
        )

    selected = [m.strip() for m in models.split(",") if m.strip()] or None
    breakdowns = convert_all(result.price_usd, selected)

    # Generate quip
    quip = None
    try:
        if breakdowns:
            quip = generate_quip(
                result.item, result.price_usd,
                breakdowns[0]["total_tokens"] if isinstance(breakdowns[0], dict) else breakdowns[0].total_tokens,
                breakdowns[0]["display_name"] if isinstance(breakdowns[0], dict) else breakdowns[0].display_name,
                backend=backend, or_model=or_model,
            )
    except Exception:
        pass

    return JSONResponse({
        "item": result.item,
        "price_usd": result.price_usd,
        "currency": result.currency,
        "confidence": result.confidence,
        "backend": result.backend,
        "quip": quip,
        "breakdowns": [
            {
                "model": b.model,
                "display_name": b.display_name,
                "input_tokens": b.input_tokens,
                "output_tokens": b.output_tokens,
                "reasoning_tokens": b.reasoning_tokens,
                "total_tokens": b.total_tokens,
                "avg_requests": b.avg_requests,
            }
            for b in breakdowns
        ],
    })


# Mount static files last (catch-all)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
