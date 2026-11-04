# Method and evidence

MetricPact uses a closed semantic layer rather than free-form SQL generation. The MVP maps phrases to five approved metrics and governed dimensions, constructs SQL from application-owned identifiers, estimates a scan budget, executes against deterministic fixture rows, and returns SQL, assumptions and reconciliation evidence together.

The shipped grain extension declares `orders` at `order_id` and `order_items` at `item_id`. Its preflight cardinality test finds two items for `o1`, so joining an order-level amount to item rows is blocked. Explicit item aggregation to order grain is allowed.

## Fiscal-calendar experiment

Acceptance criteria were fixed before execution:

- A year or quarter request without a calendar must clarify.
- Calendar year 2026 must contain six orders and $700 gross sales.
- A retail fiscal year beginning in February must place the two January orders and $200 in FY2025, with $500 in FY2026.
- Fiscal-quarter grouping must place two orders in FY2025-Q4 and four in FY2026-Q1.
- Every verified period answer must expose calendar name, version and start month.

The 24-case benchmark now covers direct metrics, grouping, filters, metric ambiguity, calendar ambiguity and governed calendar/fiscal paths. It tests deterministic routing and bucketing, not language understanding in the general case. The CLI emits machine-readable evidence.

## Limitations

- This is a portfolio MVP over six synthetic orders, not a database driver or production NL parser.
- Only calendar and one February-start retail calendar exist; there are no 4-4-5 calendars, leap-week rules, holidays or organization-specific overrides.
- Date strings are treated as UTC dates; daylight-saving and event-local timestamps are not modeled.
- Generated SQL is disclosed but not executed by a dialect-specific database in this MVP.
- Cost is represented by rows scanned; warehouses price bytes, slots and cache behavior differently.
- Full-fixture grain checks catch every duplicate here, but production sampling can miss rare keys.
- Reconciliation detects internal inconsistencies; it cannot prove upstream source correctness.
- Access control and differential privacy are not implemented.
