# Overview Design QA

final result: passed

## Evidence

- Source visual truth: `docs/reference.png` (first displayed selected design, Precision Passport).
- Implemented screen: `docs/overview-1440.png`; full scroll: `docs/overview-full.png`.
- Source pixels: 1487 × 1058. Requested browser CSS viewport: 1440 × 1024. Browser screenshot export: 1425 × 1013; the tool's exported image has a slight proportional reduction. Both images were normalized to 1440 × 1024 for comparison; this is density/export normalization, not claimed pixel-exact capture.
- State: Overview, dark theme, default used EV scenario, no modal, top of page.
- Full-view comparison: `docs/comparison.png` (source left, implementation right, 2880 × 1024).
- Focused comparison: `docs/comparison-detail.png` (hero, controls and passport region from both normalized images).
- Additional evidence: `docs/used-1280.png`, `docs/used-1920.png`, `docs/retired-1440.png`, `docs/lower-1440.png`.

## Comparison history

1. Initial capture: `docs/initial-1440.png`, combined evidence `docs/comparison-initial.png`.
   - [P2, fixed] Excess vertical chrome above the hero pushed the main composition and lifecycle flow down relative to the selected reference. Removed the redundant context strip at desktop widths and reduced passport interior height.
   - [P2, fixed] Passport and metric labels were too small compared with reference. Increased desktop label, metric and heading sizes while keeping 1280px breakpoint-specific sizing.
   - [P2, fixed] Battery asset appeared too small within the passport. Increased its displayed scale without stretching; product remains visibly within the passport composition.
2. Post-fix capture and comparison: `docs/overview-1440.png`, `docs/comparison.png`, `docs/comparison-detail.png`.
   - No remaining actionable P0/P1/P2 findings. The initial fixes preserve the selected left hero / right passport hierarchy and bring the headline and first-row rhythm closer to the reference.
   - The lower half is grounded in the user's new written scope, not judged against nonexistent lower-half reference pixels.

## Five required fidelity surfaces

- Typography: three-line headline with large sans-serif display weight; system sans fallback rather than network font dependency. Formulas use a serif mathematical face. Small data captions remain secondary; essential metrics and action labels are readable at the required desktop widths. Residual P3: exact typeface cannot be recovered from a raster mock.
- Spacing/layout: persistent rounded sidebar, thin header, dual-column hero/passport, four parallel metric cards and a horizontal six-stage lifecycle section match the main structural language. Lower content uses the same card system, no distinct third-design style. Intentional user-requested additions extend the page vertically.
- Colors/tokens: near-black graphite, restrained mint/cyan highlights, subtle white borders and approximately 23px radii. The updated risk metric uses amber only in the retired scenario. No neon or dense BI-screen treatment.
- Asset quality: matching graphite battery-pack raster recreated as a separate asset; sharp and undistorted, with a contained dark backdrop. Lucide leaf is the closest library icon for the brand mark rather than a hand-drawn approximation. Residual P3: generated pack differs in detailed casing geometry/marking from the original mock.
- Copy/content: user-requested passport specifications and Risk metric replace the original image's less detailed passport and Decision metric. Recommendation is shown in the Insight section. Added explicit simulated data, model assumptions and unavailable subpage notes. These are intentional scope changes, not unexplained visual drift.

## Functional and responsive evidence

- 1280px: document scroll width equals client width 1265px (15px browser scrollbar). Four metrics and six flow nodes remain visible; generated image overflow is clipped within its own passport and does not cause page overflow.
- 1440px: document scroll width equals client width (1425px with normal scrollbar; export may temporarily suppress scrollbar); chart container measured 333px and adapts to its card.
- 1920px: document scroll width equals client width 1905px. Layout remains balanced and vertically scrollable.
- Used scenario confirmed: 82.4%, 920 cycles, 8.72 tCO₂e, LOW, Continue Vehicle Use.
- Retired scenario confirmed after count-up settles: 68.7%, 310 cycles, 9.72 tCO₂e, MEDIUM, Second-Life Utilization; all three insights and the 60% reference line change.
- Start Assessment loading and five analysis steps observed, then completed result checked. Close works and scenario controls are disabled while processing.
- Insight collapse/expand checked through aria-expanded. Native dialog focus behavior and named close controls used. Each of five sidebar module entries opens a scope-aware dialog; no fabricated working subpages.
- Carbon provenance and RUL explanation dialogs checked. Return-to-preview scroll checked.
- Hover/active/transition and focus styles present; primary action, tabs and icon controls tested through pointer interaction. Reduced-motion CSS disables transitions and count-up respects the preference. No separate screen-reader or OS reduced-motion session was performed.
- Browser console captured via `bt.dev.logs` with error/warn levels returned `[]` after interaction checks.
- TypeScript and production build passed; math checks passed. Chart is split into a separate lazy-loaded bundle to avoid the initial oversized-chunk warning.

## Follow-up polish

- P3 only: exact typeface and generated battery casing details can be refined later if original brand assets become available.
- Do not implement remaining pages during this stage. Await user instruction.
