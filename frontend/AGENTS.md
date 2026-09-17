# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## Current approved scope (2026-09-13)
- Visual baseline: first displayed design, Precision Passport. Preserve its sidebar/header, hero/passport composition, restrained graphite/mint/cyan palette and large rounded cards.
- The third design only informs technical content, never a separate visual style.
- As of 2026-09-15 the user requested backend integration. Preserve Overview and use the five existing module dialogs for shared API results and a printable report; do not redesign or add unrelated pages.
- Scenario switching must update metrics, insights, recommendation and technical previews together.
- Preserve explicit provenance: local Demo, NASA experimental-cell inference, BMS quality checks, and simulated pack decisions are distinct evidence domains. LIVE denotes a backend response, not vehicle validation.
- Approved bilingual scope: offer Chinese / English in the header, default Chinese, remember the selection locally, and translate navigation, forms, errors, results and printable reports. Preserve entered values, identifiers, API payloads, numerical results and evidence boundaries when switching.
