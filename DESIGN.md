# Design

## Source of truth
- Status: Draft
- Last refreshed: 2026-06-11
- Primary product surfaces: `cloudflare/index.html` mobile web app, result/share card export, GitHub README landing copy
- Evidence reviewed: `AGENTS.md`, `README.md`, `cloudflare/index.html`, `cloudflare/_worker.js`, `screenshots/config.jpeg`, `screenshots/input.jpeg`, `screenshots/output.png`

## Brand
- Personality: dry, self-aware, lightly cursed, AI-native
- Trust signals: browser-only key handling, direct provider calls, obvious privacy copy, predictable camera flow
- Avoid: meme-chaos UI, faux-enterprise jargon, crypto aesthetics, over-explaining the joke before the user gets a result

## Product goals
- Goals:
  - Turn a price into a fast, legible AI-token comparison.
  - Land one good joke after the math is understood.
  - Feel safe enough to try without signup anxiety.
  - Produce a result that is worth screenshotting or sharing.
- Non-goals:
  - Full financial accuracy tooling
  - Deep provider benchmarking console
  - Serious budgeting or procurement workflow
- Success signals:
  - First-time users understand how to run a scan without trial and error.
  - Users see the primary token result without parsing dense settings first.
  - Shared artifacts look intentional and understandable out of context.

## Personas and jobs
- Primary personas:
  - AI-native builders who already think in model tokens and API spend
  - Curious internet users who enjoy “what does this cost in X?” joke tools
- User jobs:
  - Scan a thing and get a funny but legible token conversion.
  - Compare a purchase against familiar AI models.
  - Share a result that signals taste or humor.
- Key contexts of use:
  - Mobile phone, one-handed use, quick scans
  - Social posting and private chat sharing
  - Demoing to friends, coworkers, or AI communities

## Information architecture
- Primary navigation: single-screen app with progressive disclosure for setup, privacy, advanced options, and full model table
- Core routes/screens:
  - Main scan surface
  - Setup drawer
  - Privacy drawer
  - Results panel
  - Share card export
- Content hierarchy:
  - 1. Understand what the app does
  - 2. Add the minimum required credentials
  - 3. Capture or upload an image
  - 4. Read the main token result
  - 5. Enjoy joke, facts, comparisons, and sharing

## Design principles
- Principle 1: The joke lives in the output, not in the controls.
- Principle 2: One obvious next action at a time. Do not present dead-end primary actions.
- Principle 3: Default path first, advanced knobs later.
- Tradeoffs:
  - Keep model/provider flexibility, but demote it behind calmer wording and progressive disclosure.
  - Preserve playful tone, but avoid making the setup flow feel unserious or confusing.

## Visual language
- Color: dark field with warm amber highlights and cyan support accents; use amber for primary action and selected state, not for every decorative element
- Typography: sharp uppercase branding, readable body copy, monospace reserved for price/token figures
- Spacing/layout rhythm: tight, card-based, mobile-first, with enough breathing room around the primary action and result hero
- Shape/radius/elevation: soft radii, restrained outlines, subtle glow rather than heavy glassmorphism
- Motion: minimal; scanning and count-up animations should support feedback, not compete with the result
- Imagery/iconography: camera-first product imagery; logo and share card can carry more of the joke than the settings UI

## Components
- Existing components to reuse:
  - Header buttons
  - Drawer panels
  - Pill selectors
  - Viewfinder and dock
  - Result hero and chip system
  - Share card export
- New/changed components:
  - Compact onboarding/intro copy block in setup
  - Cleaner credential-ready analyze button state
  - Simplified settings labels for casual users
- Variants and states:
  - Setup open/closed
  - Own-key vs shared-key mode
  - Image missing vs credentials missing vs ready-to-scan
  - Joke on vs joke off
- Token/component ownership: keep styling in `cloudflare/index.html`; avoid introducing a separate design system layer for this static app

## Accessibility
- Target standard: pragmatic WCAG AA where feasible for contrast and touch targets
- Keyboard/focus behavior: all buttons, pills, drawers, and toggles need visible focus states
- Contrast/readability: primary labels and button states must remain legible without relying on subtle color differences
- Screen-reader semantics: onboarding and settings labels should use plain language; avoid unexplained jargon
- Reduced motion and sensory considerations: scanning animation is acceptable, but decorative motion should remain limited

## Responsive behavior
- Supported breakpoints/devices: mobile portrait first, desktop sidebar secondary
- Layout adaptations:
  - Mobile keeps setup as a drawer and scan as the main task
  - Desktop keeps setup persistent in the sidebar
- Touch/hover differences:
  - Tooltip content must still work on tap
  - Share/save and scan actions must remain large enough for touch

## Interaction states
- Loading: scanning overlay and status text
- Empty: no image yet, no credentials yet, camera unavailable fallback
- Error: clear credential and network errors with obvious recovery text
- Success: token hero first, supporting facts and joke second
- Disabled: primary action must explain what is missing
- Offline/slow network, if applicable: preserve local UI state and explain that provider calls require network access

## Content voice
- Tone: concise, dry, lightly funny
- Terminology: prefer plain words like “provider,” “API key,” “shared password,” and “quips” over abstract labels
- Microcopy rules:
  - Setup copy should be sober and direct.
  - Joke copy should appear after the result, not before it.
  - Avoid labels that sound like enterprise settings panels unless they are truly advanced.

## Implementation constraints
- Framework/styling system: single-file static HTML/CSS/JS in `cloudflare/index.html`
- Design-token constraints: existing CSS custom properties should remain the primary styling surface
- Performance constraints: no build step, no heavy libraries, keep first-load light for mobile
- Compatibility constraints: Cloudflare Pages static deployment, browser camera APIs, direct third-party API calls
- Test/screenshot expectations: manual mobile and desktop smoke check; verify primary button states and settings wording after edits

## Open questions
- [ ] Should the product keep the `TokenEyes` name given external brand collision, or should naming change before stronger promotion?
- [ ] Should shared-key mode be framed as “demo mode” for casual users, or remain a deployer-only feature?
- [ ] Should result sharing eventually support permalink/result-state URLs instead of image-only export?
