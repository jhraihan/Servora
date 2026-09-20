# ShebaLocal — Documentation

## Files

| File | Purpose |
|---|---|
| `ShebaLocal-PRD.pdf` | The product requirements document (40 pages, 15 sections). This is the deliverable. |
| `prd_content.py` | All PRD prose and tables, as structured data. Edit here to change the document. |
| `build_prd.py` | Renders `prd_content.py` to PDF. Layout only — no content. |
| `verify_trust_math.py` | Reference implementation of the section 7 trust algorithm, with assertions that reproduce every figure in the section 7.4 worked examples. |

## Rebuilding the PDF

```bash
pip install reportlab
python docs/build_prd.py
```

Output: `docs/ShebaLocal-PRD.pdf`

## Verifying the trust algorithm

```bash
python docs/verify_trust_math.py
```

This prints the full factor breakdown for both worked examples and asserts
each figure against the values printed in the PRD. **If you change any weight
or formula in section 7, run this first** — it will tell you exactly which
tables in the PRD have gone stale.

It is also the specification of record for the arithmetic. `apps/trust/factors.py`
should produce identical output, and the same test cases belong in the Django
test suite.

## Editing workflow

Content and layout are deliberately separate:

1. Edit `prd_content.py` — it is a list of `(kind, payload)` tuples. Supported
   kinds are `h1`, `h2`, `h3`, `p`, `bullets`, `numbers`, `table`, `code`,
   `callout`, `spacer`, `pagebreak`.
2. Re-run `build_prd.py`.

The table of contents is generated from the `h1` entries automatically, so
adding a section requires no other change.

Inline markup in `p` and table cells is ReportLab's mini-HTML: `<b>`, `<i>`,
`<font face='Courier'>`, and HTML entities such as `&mdash;` and `&ge;`.

## Stack decisions recorded in the PRD

| Decision | Where | Summary |
|---|---|---|
| JavaScript, not TypeScript | §8.6 | Frozen state constants, an API normaliser layer, JSDoc typedefs and PropTypes on money/state/trust components replace static typing. |
| No Docker | §11 | Native installs on Windows locally; Nginx + Gunicorn + systemd on a VPS. Containers noted as an optional later improvement. |
| No Celery or Redis in Phase 1 | §8.4 | Event-driven work runs synchronously; scheduled work runs as management commands under Task Scheduler / cron. |
| Migration path preserved | §8.5 | Thresholds that trigger adopting a queue, plus the three service-layer rules that keep the switch to one line per call site. |

The three rules in §8.5 are load-bearing — follow them from the first commit:

1. Services take **IDs, not model instances** (queue messages must be JSON-serializable).
2. Services **never touch `request`** (no worker has one).
3. Services are **idempotent** (a retry or double-fired cron must be harmless).
