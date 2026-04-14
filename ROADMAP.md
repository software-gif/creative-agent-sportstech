# Sportstech Creative Agent — Roadmap

Last updated: 2026-04-14

Living document. Captures what's been built, what's in flight, and what was raised in the Sportstech weekly call plus subsequent chat sessions that we still need to deliver on. Order inside each bucket is rough priority.

---

## ✅ Done

### Generation pipeline
- **Key-visual skill** with auto-rotation of camera angle + character angle when not explicitly set.
- **Auto-QC retry loop** (`--auto-qc --qc-retries N --qc-threshold M`) that deletes + regenerates images that fail the judge.
- **Quality-control judge** with hard-failure block (person not on equipment → automatic fail, wrong product → automatic fail, grossly distorted geometry → automatic fail), responseSchema-forced JSON output, thinking budget disabled.
- **Multishot skill** with imperative re-render prompt that actually changes viewpoint instead of near-duplicating source.
- **Color-variant skill** with `parent_id` auto-resolution via storage-path lookup.
- **Parent-child linking** across multishots + color-variants; backfill migration for pre-existing orphans.

### Product accuracy
- **Background-remover skill** (rembg u2net) normalises all 135 render assets to transparent cutouts in `renders/<handle>/cutouts/`.
- **Product-image-analyzer skill** catalogs every reference image with Gemini Vision (camera_angle, framing, variant, visible_parts, detail_richness, key_features) — one-off cost ~$0.14.
- **Smart reference selection** in key-visual uses the catalog to filter by colour variant, include 1-2 hero overviews, 2-3 matching-angle shots, 2-3 detail close-ups, and angle diversity — deterministic, not random sampling.
- **Variant filter** (`--variant wood_light`) so Gemini never averages two product colours into one blurred walkpad.
- **Must-match hardening**: footwear rules, "person on equipment" rules, natural foot-position rules across all 13 products (rowing left alone since socks/barefoot is realistic for home rowing). Rules propagate automatically into both the compositing prompt and the QC judge prompt.

### Board UI
- **Grid + list + overlay views** of all generated creatives.
- **Filter dropdowns**: product, environment, camera angle, character position, format.
- **Overlay redesign**: variants in a bigger 3-column grid on top-right, compact metadata card with colour-coded QC rating below, Copy-path / Copy-ID buttons for agent chaining.
- **Variant indicator dots** on cards: red = none, green = present, `M` for multishots, `C` for colour variants. Full variant grid still lives in the overlay.
- **List row clickable** → opens overlay (action buttons stop propagation).
- **Presets page** with read-only preset recipe cards, humanized labels, collapsible "How presets work" guide including CLI examples and a full variable reference table.
- **Variants nesting** in board state — key visuals show their multishot/color-variant children grouped under them.

### From the weekly call 2026-04-14
- ✅ *"Filter-instance that drops bad generations before they hit the dashboard"* (Florian) → auto-QC delete-on-fail now does exactly this.
- ✅ *"Variants should show inline next to the parent so you see they belong together"* (Johannes → Clemente) → overlay Multishots + Color Variants groups, card dot indicators, children grouped under parent in grid.
- ✅ *"Analyse product images once so we know which reference shows which angle"* (Johannes) → product-image-analyzer skill.

---

## 🚧 In flight

- **10-product end-to-end test batch**: generate one lifestyle image per product with the smart-selection + auto-QC pipeline so we can spot-check quality across the whole catalogue. Blocking: finishing this before the next weekly call so Clemente can review.
- **Library drag-and-drop into folders**: folders can be created but images can't be moved into them from the board UI yet. Need to inspect whether the drag handlers exist but are unwired or are missing entirely.

---

## 📋 Open — from weekly call 2026-04-14

### Asked by stakeholders

- **Text-tag system on images** (Quang)
  Not the filter chips we already have — Quang wants semantic metadata *attached* to images: Scandi, Male/Female, Hell/Dunkel, etc., so they become searchable/filterable after generation. Distinct from the existing `tags` column because it should be populated automatically by the generator (not by the user). Open: decide whether to generate tags inline during QC (free-ish) or as a separate post-process.

- **Randomizer / building-block builder** (Quang)
  Interface concept: randomise Environment × Design × Product × Person to spit out a ready-made prompt for key-visual. Partial overlap with Presets — presets lock a specific recipe, randomizer rolls a fresh one each time. Could live as a "Shuffle" button on the Presets page that generates a transient preset.

- **Cost-per-creative visibility** (Quang)
  Track and surface the API cost of each generation (Gemini 3 Pro Image ~$0.04 + judge ~$0.0005 + any retries). Options: live display next to the QC rating, or a running total per day / per batch. Johannes promised to bring numbers to the next call.

- **Uni One-style auto-regressive evaluation** (Florian)
  Florian showed a competitor tool where the agent auto-evaluates each generation inline in the dashboard, labels issues ("text distorted", "glow", "wrong colour"), and feeds them back. Our auto-QC already does half of this — the missing piece is surfacing the judge's `notes` visibly in the UI and letting the user click a failed image to see *why* it was rejected.

- **Preview deployment on Vercel without login** (Quang)
  So Clemente and Florian can click a URL and see the current state of the board without having to run localhost. Domain will be shared once deployed. Nothing login-protected for now.

- **Iteration buttons on the creative card/overlay** (Johannes idea during the call)
  Buttons like "Generate Multishots" / "Generate Color Variants" / "Iterate" directly on a creative, instead of going back to the terminal. Johannes warned that Claude API usage would be expensive — but a button that runs a pre-built prompt via the CLI skills would be fine. A candidate is making these buttons trigger the existing skills via a lightweight API route, not via Claude.

- **Image iteration by CR-ID** (Clemente)
  *"I want to change the shoes on this walkpad image"* — natural language iteration of an existing generated creative. Current state: can call multishot/color-variant, but there's no general-purpose "edit this creative" flow. Partially unblocked by the Copy-ID button in the overlay, but still terminal-driven. A full fix needs either the iteration buttons above or a dedicated `iterate` skill that takes `--creative-id` + freetext.

### Concerns still not fully handled

- **Product accuracy still drifts on small details** — Clemente flagged missing back-end control buttons, wrong end-cap detail on woodpad-pro even after Phase 2+3. Smart selection helps but can't manufacture detail shots Clemente never uploaded. Mitigation ideas:
  - Ask the 3D team for targeted close-ups of the features we know the model drops (back controls, front console, roller ends).
  - Tune `must_match` per product to call out the features by name so the judge penalises their absence.
  - Include 1-2 extreme detail crops per generation above the current 12-ref cap for must-see features.

- **Pose / usage semantics still slip through** — Johannes sent a woodpad image where the person was standing *next to* the pad at a desk. Hard-fail rule added in this session, but:
  - Needs to hold across ALL products, all multishots, all colour variants, not just woodpad-pro.
  - Needs a re-test on a representative batch to confirm the fix isn't product-specific.

- **Person facing direction on treadmill** — recurring Gemini failure mode (person walking backwards, display on wrong side). Partly mitigated by the "display faces user" physical-law block in the compositing prompt, but not 100% solid.

---

## 🧭 Nice-to-haves / backlog

- **Fine-tuning / LoRA per product** for the products that keep drifting. Out of scope for the current project budget but worth tracking for a follow-up engagement.
- **Automated tag ingestion** — pull `scandi`, `morning`, `female`, etc. from the prompt metadata into the tag column automatically.
- **Batch-level QC dashboard** — show pass rates per batch so the team sees the trend.
- **Per-product reference coverage report** — for each product, which camera angles / detail types are missing from the catalogue so the 3D team knows what to render next.
- **Character builder end-to-end** (skill exists, needs UI + workflow wiring).
- **Smiro Board workflow** for stakeholder feedback intake (Johannes mentioned as his preferred workflow for capturing change requests from Clemente/Florian/Quang).

---

## 🐛 Known rough spots

- Judge still occasionally passes marginal images at 7-8/10 with nits that Clemente considers blockers for paid ads. Could raise default threshold to 8 OR keep the prompt getting more specific over time.
- Products with very few reference images (svibe: 3, x150: 5, hgx50: 5) lose the smart-selection advantage because there's nothing to pick from.
- `products/<handle>/` still contains small Shopware thumbnails (65-260px) that leaked into early generations. They're now de-prioritised but not deleted.

---

## 📞 Agreements from the weekly call

- **Next steps owner**: Johannes optimises skills + product accuracy. Sportstech team sends change requests either via Smiro Board (preferred) or Teams.
- **Timeline**: Johannes estimated 2-2.5 weeks to finish the current scope.
- **Infra**: Vercel deployment under Sportstech's own account. Google Gemini API billed through Sportstech's own Google Cloud project. GitHub repo will be handed over at the end.
- **Out of scope**: ad creator (headlines, CTAs, text overlays) — lifestyle photography only.
