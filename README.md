# MetricPact

[![CI](https://github.com/MadanMohan0537/governed-metric-query-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/MadanMohan0537/governed-metric-query-engine/actions/workflows/ci.yml)

**Ask governed business questions without turning natural language into unaudited SQL.**

MetricPact is a dependency-free Python MVP that maps questions onto a semantic metrics layer, shows generated SQL and assumptions, enforces scan budgets, detects grain-unsafe joins, and returns reconciliation evidence with every verified answer.

> AI PM Project Lab traceability: project 16, originally “Ask the Warehouse.”

## Why this exists

Natural-language analytics can produce plausible but wrong numbers when “sales” has multiple definitions, a one-to-many join duplicates facts, or “year” silently means the wrong business calendar. MetricPact treats clarification, governance, and verification as product behavior—not post-hoc warnings.

## Shipped MVP

- Five allow-listed metrics: gross sales, net sales, order count, customer count and AOV.
- Region/month grouping and deterministic filters over reproducible synthetic data.
- Ambiguity gate: bare “sales” and “revenue” are not guessed.
- SQL and assumptions shown for every verified query; user text is never interpolated into SQL.
- Scan-row budget with a blocked outcome before execution.
- Post-execution reconciliation evidence.
- Declared grains plus cardinality preflight reject unsafe order-to-item joins.
- **Governed fiscal-calendar semantics:** year/quarter questions require calendar or retail-fiscal selection.
- Calendar identifier, version and year-start month in every period answer’s evidence.
- 24-question benchmark, 24 unit tests and Python 3.11–3.13 CI.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m metricpact.cli --output evidence.json
python -m unittest discover -s tests -v
```

No service, credential, network connection or paid API is required.

## Fiscal-boundary experiment

The synthetic snapshot contains six orders across January–March 2026. Calendar-year gross sales produce one `2026` bucket totaling $700. Under the governed retail calendar, whose year begins in February, January’s two orders and $200 belong to `FY2025`; the remaining $500 belongs to `FY2026`. The CLI reports two boundary records and zero expected-bucket errors. Asking only for “gross sales by year” returns `clarify` with the available calendars.

## Architecture

```mermaid
flowchart LR
  A[Question] --> B[Semantic planner]
  B --> C[Metric, calendar and grain gates]
  C --> D[Deterministic executor]
  D --> E[Answer plus evidence]
```

## Evidence and honest scope

The expected local benchmark is 24/24, the unsafe order-to-item join must be blocked, and the fiscal-boundary fixture must have zero expected-bucket errors. These results establish deterministic fixture behavior only—not production accuracy on arbitrary language, SQL dialects, time zones or warehouse schemas. See [method and limitations](docs/METHOD.md), the [rigorous feature backlog](docs/BACKLOG.md), and the [progress record](docs/PROGRESS.md).

## Repository map

```text
metricpact/      engine, governed fixture, benchmark and CLI
tests/           behavioral and safety tests
docs/            method, limitations, backlog and progress
.github/         reproducible CI and evidence artifact
```

## License

MIT
