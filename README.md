# TokenPrice

**See the world in AI tokens.**

Point your camera at anything with a price tag, and TokenPrice tells you how many AI tokens it costs. That $6 latte? That's 1.3 million Claude Sonnet input tokens.

## Quick Start

```bash
pip install -e .

# Pure math mode (no API key needed)
tokenprice --price 5.99

# With Gemini vision (free API key)
export GEMINI_API_KEY=your-key-here
tokenprice photo.jpg           # read price from image
tokenprice shoe.jpg --guess    # AI estimates the price
```

## What It Does

1. **Reads** a price from an image (OCR via Gemini Vision), or **guesses** the price of any object
2. **Converts** the dollar amount into token counts for popular AI models
3. **Displays** a fun breakdown showing how many tokens, requests, and AI-generations your purchase is worth

## Usage

```bash
tokenprice photo.jpg                        # read price from image
tokenprice shoe.jpg --guess                 # let AI guess the price
tokenprice --price 49.99                    # just convert a dollar amount
tokenprice receipt.jpg -m claude-sonnet-4-6 # specific model only
tokenprice --list-models                    # see all supported models
```

## Supported Models

| Model | Input $/1M | Output $/1M | Reasoning $/1M |
|-------|-----------|-------------|-----------------|
| Claude Sonnet 4.6 | $3.00 | $15.00 | $3.00 |
| Claude Opus 4.6 | $15.00 | $75.00 | $15.00 |
| Claude Haiku 4.5 | $0.80 | $4.00 | $0.80 |
| Gemini 2.5 Flash | $0.15 | $0.60 | $0.25 |
| Gemini 2.5 Pro | $1.25 | $10.00 | $1.25 |
| GPT-4o | $2.50 | $10.00 | - |
| GPT-4o Mini | $0.15 | $0.60 | - |

## API Key

Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Set it as:

```bash
export GEMINI_API_KEY=your-key-here
# or create a .env file
```

The `--price` flag works without any API key.

## Roadmap

- [ ] Web UI (drag-drop images)
- [ ] Receipt mode (itemize a full receipt)
- [ ] Reverse mode ("I have $5 of API credit, what can I buy IRL?")
- [ ] Browser extension
- [ ] Shareable meme cards
- [ ] Multi-currency support
- [ ] Live pricing from provider APIs

## License

MIT
