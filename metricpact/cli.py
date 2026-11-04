import argparse
import json
from pathlib import Path

from .benchmark import run_benchmark
from .data import ORDERS, ORDER_ITEMS
from .engine import GrainError, MetricPact, check_join_grain


def build_report():
    engine = MetricPact()
    examples = [engine.ask(q).to_dict() for q in ("gross sales by region", "net sales by month", "sales")]
    calendar = engine.ask("gross sales by calendar year")
    fiscal = engine.ask("gross sales by fiscal year")
    ambiguous = engine.ask("gross sales by year")
    try:
        check_join_grain(ORDERS, ORDER_ITEMS, "order_id")
        grain = {"unsafe_join_blocked": False}
    except GrainError as exc:
        grain = {"unsafe_join_blocked": True, "reason": str(exc), "safe_alternative": "Aggregate order_items to order_id before joining."}
    return {
        "product": "MetricPact",
        "benchmark": run_benchmark(),
        "grain_experiment": grain,
        "calendar_experiment": {
            "calendar_year": calendar.to_dict(),
            "retail_fiscal_year": fiscal.to_dict(),
            "ambiguous_year": ambiguous.to_dict(),
            "boundary_orders": sum(row["ordered_on"].startswith("2026-01") for row in ORDERS),
            "boundary_errors": 0 if calendar.rows == [{"year": "2026", "gross_sales": 700.0}] and fiscal.rows == [{"year": "FY2025", "gross_sales": 200.0}, {"year": "FY2026", "gross_sales": 500.0}] else 1,
        },
        "examples": examples,
    }


def main():
    parser = argparse.ArgumentParser(description="Run the MetricPact evidence demo")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(build_report(), indent=2)
    if args.output:
        args.output.write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
