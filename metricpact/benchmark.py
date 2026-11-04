from dataclasses import dataclass
from .engine import MetricPact, Status


@dataclass(frozen=True)
class Case:
    question: str
    status: Status
    metric: str | None


CASES = [
    Case("gross sales", Status.VERIFIED, "gross_sales"), Case("net sales", Status.VERIFIED, "net_sales"),
    Case("sales", Status.CLARIFY, None), Case("revenue", Status.CLARIFY, None),
    Case("orders", Status.VERIFIED, "order_count"), Case("customers", Status.VERIFIED, "customer_count"),
    Case("average order value", Status.VERIFIED, "average_order_value"), Case("AOV", Status.VERIFIED, "average_order_value"),
    Case("gross sales by region", Status.VERIFIED, "gross_sales"), Case("net sales by month", Status.VERIFIED, "net_sales"),
    Case("orders by region", Status.VERIFIED, "order_count"), Case("customers by region", Status.VERIFIED, "customer_count"),
    Case("gross sales in East", Status.VERIFIED, "gross_sales"), Case("net sales in West", Status.VERIFIED, "net_sales"),
    Case("orders in North", Status.VERIFIED, "order_count"), Case("gross sales 2026-01", Status.VERIFIED, "gross_sales"),
    Case("net sales 2026-02", Status.VERIFIED, "net_sales"), Case("orders 2026-03", Status.VERIFIED, "order_count"),
    Case("sales by month", Status.CLARIFY, None), Case("revenue in East", Status.CLARIFY, None),
    Case("gross sales by year", Status.CLARIFY, "gross_sales"),
    Case("gross sales by calendar year", Status.VERIFIED, "gross_sales"),
    Case("gross sales by fiscal year", Status.VERIFIED, "gross_sales"),
    Case("orders by fiscal quarter", Status.VERIFIED, "order_count"),
]


def run_benchmark():
    engine = MetricPact()
    outcomes = []
    for case in CASES:
        result = engine.ask(case.question)
        passed = result.status == case.status and result.metric == case.metric
        outcomes.append({"question": case.question, "passed": passed, "actual_status": result.status.value})
    passed = sum(x["passed"] for x in outcomes)
    return {"cases": len(CASES), "passed": passed, "accuracy": passed / len(CASES), "outcomes": outcomes}
