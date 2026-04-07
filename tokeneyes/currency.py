"""Currency normalization and hardcoded FX conversion helpers."""

from __future__ import annotations

from typing import Any

FX_RATE_SOURCE = "ECB euro reference rates"
FX_RATE_DATE = "2026-04-07"

# ECB publishes these as units of foreign currency per 1 EUR.
# USD conversion is derived from the EUR/USD reference rate.
ECB_EUR_RATES: dict[str, float] = {
    "USD": 1.1557,
    "JPY": 184.73,
    "CZK": 24.531,
    "DKK": 7.4725,
    "GBP": 0.87258,
    "HUF": 382.30,
    "PLN": 4.2753,
    "RON": 5.0954,
    "SEK": 10.9900,
    "CHF": 0.9242,
    "ISK": 143.80,
    "NOK": 11.1830,
    "TRY": 51.5551,
    "AUD": 1.6665,
    "BRL": 5.9506,
    "CAD": 1.6078,
    "CNY": 7.9251,
    "HKD": 9.0564,
    "IDR": 19727.97,
    "ILS": 3.6361,
    "INR": 107.4895,
    "KRW": 1730.56,
    "MXN": 20.5167,
    "MYR": 4.6586,
    "NZD": 2.0267,
    "PHP": 69.628,
    "SGD": 1.4847,
    "THB": 37.687,
    "ZAR": 19.5192,
}

_CURRENCY_ALIASES: dict[str, str] = {
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "US DOLLAR": "USD",
    "US DOLLARS": "USD",
    "DOLLAR": "USD",
    "DOLLARS": "USD",
    "EUR": "EUR",
    "EURO": "EUR",
    "EUROS": "EUR",
    "GBP": "GBP",
    "POUND": "GBP",
    "POUNDS": "GBP",
    "POUND STERLING": "GBP",
    "STERLING": "GBP",
    "JPY": "JPY",
    "YEN": "JPY",
    "JAPANESE YEN": "JPY",
    "CNY": "CNY",
    "YUAN": "CNY",
    "RENMINBI": "CNY",
    "RMB": "CNY",
    "INR": "INR",
    "RUPEE": "INR",
    "RUPEES": "INR",
    "INDIAN RUPEE": "INR",
    "CHF": "CHF",
    "SWISS FRANC": "CHF",
    "AUD": "AUD",
    "A$": "AUD",
    "AUSTRALIAN DOLLAR": "AUD",
    "CAD": "CAD",
    "C$": "CAD",
    "CA$": "CAD",
    "CANADIAN DOLLAR": "CAD",
    "HKD": "HKD",
    "HK$": "HKD",
    "NZD": "NZD",
    "NZ$": "NZD",
    "SGD": "SGD",
    "S$": "SGD",
    "KRW": "KRW",
    "WON": "KRW",
    "ILS": "ILS",
    "SHEKEL": "ILS",
    "MXN": "MXN",
    "MEXICAN PESO": "MXN",
    "BRL": "BRL",
    "R$": "BRL",
    "BRAZILIAN REAL": "BRL",
    "TRY": "TRY",
    "TURKISH LIRA": "TRY",
    "THB": "THB",
    "BAHT": "THB",
    "PHP": "PHP",
    "PHILIPPINE PESO": "PHP",
}


def coerce_number(value: Any) -> float | None:
    """Return a float when the value looks numeric."""
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def canonicalize_currency(value: Any) -> str | None:
    """Normalize a code, symbol, or common name to a 3-letter currency code."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if text == "€":
        return "EUR"
    if text == "£":
        return "GBP"
    if text == "¥":
        return "JPY"
    if text == "₹":
        return "INR"
    if text == "₩":
        return "KRW"
    if text == "₪":
        return "ILS"
    if text == "₱":
        return "PHP"
    if text == "฿":
        return "THB"

    cleaned = " ".join(text.upper().replace("_", " ").replace("-", " ").split())
    if cleaned in ("EUR", "USD") or cleaned in ECB_EUR_RATES:
        return cleaned
    return _CURRENCY_ALIASES.get(cleaned)


def usd_per_unit(currency: str | None) -> float | None:
    """Return USD value for one unit of the given currency."""
    code = canonicalize_currency(currency)
    if code is None:
        return None
    if code == "USD":
        return 1.0
    eur_to_usd = ECB_EUR_RATES["USD"]
    if code == "EUR":
        return eur_to_usd
    eur_to_code = ECB_EUR_RATES.get(code)
    if eur_to_code is None:
        return None
    return eur_to_usd / eur_to_code


def convert_price_to_usd(
    price: Any,
    currency: Any,
    fallback_price_usd: Any = None,
) -> tuple[float | None, float | None]:
    """Convert a local price to USD using the hardcoded ECB reference table."""
    amount = coerce_number(price)
    code = canonicalize_currency(currency)
    fallback_usd = coerce_number(fallback_price_usd)

    if amount is not None and code is not None:
        rate = usd_per_unit(code)
        if rate is not None:
            return round(amount * rate, 2), rate

    return fallback_usd, None


def format_currency(amount: Any, currency: Any) -> str | None:
    """Format a money amount for terminal/UI text without locale dependencies."""
    value = coerce_number(amount)
    code = canonicalize_currency(currency)
    if value is None or code is None:
        return None
    decimals = 0 if code in {"JPY", "KRW", "IDR"} else 2
    number = f"{value:,.{decimals}f}"
    return f"${number}" if code == "USD" else f"{code} {number}"
