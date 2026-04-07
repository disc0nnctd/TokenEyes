"""Rich terminal output for TokenEyes."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .pricing import TokenBreakdown

console = Console()


def _format_tokens(n: int) -> str:
    """Format token count with commas."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,}"


def render(
    item: str,
    price_usd: float,
    confidence: str,
    breakdowns: list[TokenBreakdown],
    quip: str | None = None,
) -> None:
    """Render the full TokenEyes output to the terminal."""
    # Header
    conf_style = {
        "read": "green",
        "estimated": "yellow",
        "manual": "cyan",
    }.get(confidence, "white")
    conf_text = {
        "read": "read from image",
        "estimated": "estimated",
        "manual": "manual input",
    }.get(confidence, confidence)

    header = Text()
    header.append(" TOKENEYES ", style="bold white on blue")
    header.append(f"  {item} ", style="bold")
    header.append(f"- ${price_usd:.2f} ", style="bold green")
    header.append("(")
    header.append(conf_text, style=conf_style)
    header.append(")")

    console.print()
    console.print(header)
    console.print()

    # Table
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        pad_edge=True,
        expand=False,
    )
    table.add_column("Model", style="bold", min_width=20)
    table.add_column("Input", justify="right", style="green")
    table.add_column("Output", justify="right", style="yellow")
    table.add_column("Reasoning", justify="right", style="magenta")
    table.add_column("Total", justify="right", style="bold white")
    table.add_column("~ Requests", justify="right", style="dim")

    for b in breakdowns:
        reasoning_str = _format_tokens(b.reasoning_tokens) if b.reasoning_tokens is not None else "-"
        table.add_row(
            b.display_name,
            _format_tokens(b.input_tokens),
            _format_tokens(b.output_tokens),
            reasoning_str,
            _format_tokens(b.total_tokens),
            f"{b.avg_requests:,}",
        )

    console.print(table)

    # Quip
    if quip:
        console.print()
        console.print(Panel(
            f"[italic]{quip}[/italic]",
            border_style="bright_blue",
            padding=(0, 2),
        ))

    console.print()
