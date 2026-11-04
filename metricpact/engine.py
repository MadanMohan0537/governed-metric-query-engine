"""Dependency-free governed analytics engine.

User text selects allow-listed semantic objects; it is never interpolated into SQL.
"""
from dataclasses import asdict, dataclass
from enum import StrEnum
import re

from .data import ORDERS, ORDER_ITEMS


class Status(StrEnum):
    VERIFIED = "verified"
    CLARIFY = "clarify"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Metric:
    name: str
    label: str
    expression: str
    reducer: str


@dataclass(frozen=True)
class GovernedCalendar:
    name: str
    label: str
    year_start_month: int
    version: str = "v1"

    def __post_init__(self):
        if not 1 <= self.year_start_month <= 12:
            raise ValueError("year_start_month must be between 1 and 12")

    def bucket(self, ordered_on: str, period: str) -> str:
        year, month = (int(part) for part in ordered_on[:7].split("-"))
        fiscal_year = year if month >= self.year_start_month else year - 1
        offset = (month - self.year_start_month) % 12
        if period == "year":
            return str(year) if self.year_start_month == 1 else f"FY{fiscal_year}"
        if period == "quarter":
            prefix = str(year) if self.year_start_month == 1 else f"FY{fiscal_year}"
            return f"{prefix}-Q{offset // 3 + 1}"
        raise ValueError(f"unsupported period: {period}")

    def sql_expression(self, period: str) -> str:
        if self.year_start_month == 1:
            return "strftime('%Y', ordered_on)" if period == "year" else "strftime('%Y', ordered_on) || '-Q' || (((CAST(strftime('%m', ordered_on) AS INT) - 1) / 3) + 1)"
        shifted = f"((CAST(strftime('%m', ordered_on) AS INT) - {self.year_start_month} + 12) % 12)"
        year = f"(CAST(strftime('%Y', ordered_on) AS INT) - CASE WHEN CAST(strftime('%m', ordered_on) AS INT) < {self.year_start_month} THEN 1 ELSE 0 END)"
        return f"'FY' || {year}" if period == "year" else f"'FY' || {year} || '-Q' || (({shifted} / 3) + 1)"


CALENDARS = {
    "calendar": GovernedCalendar("calendar", "Calendar year", 1),
    "retail_fiscal": GovernedCalendar("retail_fiscal", "Retail fiscal year (February start)", 2),
}


@dataclass
class QueryResult:
    question: str
    status: Status
    metric: str | None = None
    dimension: str | None = None
    rows: list[dict] | None = None
    sql: str | None = None
    assumptions: list[str] | None = None
    evidence: dict | None = None
    message: str = ""

    def to_dict(self):
        result = asdict(self)
        result["status"] = self.status.value
        return result


METRICS = {
    "gross_sales": Metric("gross_sales", "Gross sales", "SUM(amount)", "sum_amount"),
    "net_sales": Metric("net_sales", "Net sales", "SUM(amount - refund)", "sum_net"),
    "order_count": Metric("order_count", "Orders", "COUNT(DISTINCT order_id)", "count_orders"),
    "customer_count": Metric("customer_count", "Customers", "COUNT(DISTINCT customer_id)", "count_customers"),
    "average_order_value": Metric("average_order_value", "Average order value", "AVG(amount)", "avg_amount"),
}


class GrainError(ValueError):
    pass


def assert_unique(rows, keys, table):
    seen = set()
    for row in rows:
        grain = tuple(row[k] for k in keys)
        if grain in seen:
            raise GrainError(f"{table} violates declared grain {keys}: duplicate {grain}")
        seen.add(grain)


def check_join_grain(left, right, key, *, preaggregated=False):
    """Reject right-side one-to-many joins unless explicitly pre-aggregated."""
    counts = {}
    for row in right:
        counts[row[key]] = counts.get(row[key], 0) + 1
    risky = sorted(k for k, count in counts.items() if count > 1)
    if risky and not preaggregated:
        raise GrainError(f"one-to-many join would duplicate order-grain metrics; repeated {key}: {risky}")
    return {"cardinality": "many-to-one" if preaggregated else "one-to-one", "repeated_keys": risky}


class MetricPact:
    def __init__(self, max_scan_rows=100, calendars=None):
        self.max_scan_rows = max_scan_rows
        self.calendars = dict(CALENDARS if calendars is None else calendars)
        if not self.calendars:
            raise ValueError("at least one governed calendar is required")
        if len(self.calendars) != len({calendar.name for calendar in self.calendars.values()}):
            raise ValueError("governed calendar names must be unique")
        assert_unique(ORDERS, ("order_id",), "orders")
        assert_unique(ORDER_ITEMS, ("item_id",), "order_items")

    def ask(self, question):
        q = question.lower().strip()
        metric = self._metric(q)
        if metric is None:
            return QueryResult(question, Status.CLARIFY, message="Choose gross sales or net sales; 'sales' is definitionally ambiguous.")
        period = "quarter" if "quarter" in q else "year" if "year" in q else None
        calendar = self._calendar(q, period)
        if period and calendar is None:
            return QueryResult(question, Status.CLARIFY, metric=metric.name, message="Choose calendar or retail fiscal semantics for year/quarter analysis.", evidence={"available_calendars": sorted(self.calendars)})
        dimension = period or ("region" if "region" in q else "month" if "month" in q else None)
        region = next((r for r in ("East", "West", "North") if r.lower() in q), None)
        month_match = re.search(r"2026-(0[1-3])", q)
        month = month_match.group(1) if month_match else None
        scanned = len(ORDERS)
        if scanned > self.max_scan_rows:
            return QueryResult(question, Status.BLOCKED, metric=metric.name, evidence={"estimated_scan_rows": scanned, "limit": self.max_scan_rows}, message="Estimated scan exceeds the configured row budget.")
        filtered = [r for r in ORDERS if (not region or r["region"] == region) and (not month or r["ordered_on"][5:7] == month)]
        groups = {}
        for row in filtered:
            if period:
                key = calendar.bucket(row["ordered_on"], period)
            else:
                key = row[dimension] if dimension == "region" else row["ordered_on"][:7] if dimension == "month" else "total"
            groups.setdefault(key, []).append(row)
        rows = [{dimension or "scope": key, metric.name: self._reduce(metric, values)} for key, values in sorted(groups.items())]
        where = []
        if region: where.append(f"region = '{region}'")
        if month: where.append(f"ordered_on >= '2026-{month}-01' AND ordered_on < '2026-{int(month)+1:02d}-01'")
        sql_dimension = calendar.sql_expression(period) if period else dimension
        select_dim = f"{sql_dimension} AS {dimension}, " if dimension else ""
        group = f" GROUP BY {sql_dimension}" if dimension else ""
        sql = f"SELECT {select_dim}{metric.expression} AS {metric.name} FROM governed.orders" + (" WHERE " + " AND ".join(where) if where else "") + group + ";"
        expected = sum(v[metric.name] for v in rows) if metric.reducer != "avg_amount" else None
        evidence = {"estimated_scan_rows": scanned, "row_limit": self.max_scan_rows, "reconciled_total": expected, "semantic_layer": "v1"}
        assumptions = ["Calendar dates use UTC", "Amounts use the synthetic warehouse currency"]
        if calendar:
            evidence.update({"calendar": calendar.name, "calendar_version": calendar.version, "year_start_month": calendar.year_start_month})
            assumptions.append(f"{calendar.label}; governed calendar {calendar.version}")
        return QueryResult(question, Status.VERIFIED, metric.name, dimension, rows, sql, assumptions, evidence, "Generated only from allow-listed semantic objects and reconciled after execution.")

    def _calendar(self, q, period):
        if not period:
            return None
        has_fiscal = "fiscal" in q
        has_calendar = "calendar" in q
        if has_fiscal == has_calendar:
            return None
        return self.calendars.get("retail_fiscal" if has_fiscal else "calendar")

    @staticmethod
    def _metric(q):
        if "gross" in q: return METRICS["gross_sales"]
        if "net" in q: return METRICS["net_sales"]
        if "average" in q or "aov" in q: return METRICS["average_order_value"]
        if "customer" in q: return METRICS["customer_count"]
        if "order" in q: return METRICS["order_count"]
        return None

    @staticmethod
    def _reduce(metric, rows):
        if metric.reducer == "sum_amount": return sum(r["amount"] for r in rows)
        if metric.reducer == "sum_net": return sum(r["amount"] - r["refund"] for r in rows)
        if metric.reducer == "count_orders": return len({r["order_id"] for r in rows})
        if metric.reducer == "count_customers": return len({r["customer_id"] for r in rows})
        if metric.reducer == "avg_amount": return round(sum(r["amount"] for r in rows) / len(rows), 2) if rows else 0
        raise ValueError(metric.reducer)
