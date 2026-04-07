"""CLI entry point for TokenEyes."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console

from . import __version__
from .display import render
from .pricing import convert_all, list_models, MODELS
from .vision import OPENROUTER_FREE_MODELS, OPENROUTER_DEFAULT_MODEL

console = Console(stderr=True)

# Load .env: cwd → project source root → ~/.tokeneyes.env → ~/tokeneyes/.env
load_dotenv()
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path.home() / ".tokeneyes.env")
load_dotenv(Path.home() / "tokeneyes" / ".env")


@click.command()
@click.argument("source", required=False)
@click.option("--price", "-p", type=float, help="Skip OCR, just convert this USD amount.")
@click.option("--guess", "-g", is_flag=True, help="Guess the price instead of reading it.")
@click.option("--model", "-m", multiple=True, help="Show only specific model(s).")
@click.option("--no-quip", is_flag=True, help="Skip the AI-generated quip.")
@click.option("--list-models", "show_models", is_flag=True, help="List available pricing models.")
@click.option(
    "--backend", "-b",
    type=click.Choice(["auto", "gemini", "openrouter"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Vision backend to use.",
)
@click.option(
    "--or-model",
    default=OPENROUTER_DEFAULT_MODEL,
    show_default=True,
    metavar="MODEL",
    help=f"OpenAI-compatible model for vision. Free options: {', '.join(OPENROUTER_FREE_MODELS)}",
)
@click.version_option(__version__)
def main(
    source: str | None,
    price: float | None,
    guess: bool,
    model: tuple[str, ...],
    no_quip: bool,
    show_models: bool,
    backend: str,
    or_model: str,
) -> None:
    """See the world in AI tokens.

    Point at anything with a price tag (or let AI guess the price),
    and find out how many AI tokens it costs.

    \b
    Examples:
      tokeneyes photo.jpg                          # read price (auto backend)
      tokeneyes shoe.jpg --guess                   # AI guesses the price
      tokeneyes --price 5.99                       # just convert $5.99
      tokeneyes photo.jpg --backend openrouter     # use OpenRouter free models
      tokeneyes photo.jpg --or-model qwen/qwen3.6-plus:free
      tokeneyes receipt.jpg -m claude-sonnet-4-6
    """
    if show_models:
        for m in list_models():
            prices = MODELS[m]
            parts = [f"in=${prices['input']:.2f}"]
            parts.append(f"out=${prices['output']:.2f}")
            if "reasoning" in prices:
                parts.append(f"reason=${prices['reasoning']:.2f}")
            console.print(f"  {m:25s} {', '.join(parts)} /1M tokens")
        return

    item = "item"
    confidence = "manual"
    price_usd = price
    used_backend = None

    if price is not None:
        item = "custom amount"
        confidence = "manual"
        price_usd = price
    elif source is not None:
        from .vision import read_price, guess_price, generate_quip

        console.print(f"[dim]Analyzing image (backend: {backend})...[/dim]")
        if guess:
            result = guess_price(source, backend=backend, or_model=or_model)
        else:
            result = read_price(source, backend=backend, or_model=or_model)

        item = result.item
        price_usd = result.price_usd
        confidence = result.confidence
        used_backend = result.backend

        if price_usd is None:
            console.print("[red]Could not determine a price from the image.[/red]")
            console.print("Try --guess to estimate, or --price to enter manually.")
            sys.exit(1)

        console.print(f"[dim]via {used_backend}[/dim]")
    else:
        console.print("[red]Provide an image or use --price.[/red]")
        console.print("Run [bold]tokeneyes --help[/bold] for usage.")
        sys.exit(1)

    # Convert
    selected = list(model) if model else None
    breakdowns = convert_all(price_usd, selected)

    if not breakdowns:
        console.print("[red]No matching models found.[/red]")
        sys.exit(1)

    # Generate quip
    quip = None
    if not no_quip and source is not None:
        try:
            from .vision import generate_quip
            best = breakdowns[0]
            quip = generate_quip(
                item, price_usd, best.total_tokens, best.display_name,
                backend=backend, or_model=or_model,
            )
        except Exception:
            pass

    render(item, price_usd, confidence, breakdowns, quip)
