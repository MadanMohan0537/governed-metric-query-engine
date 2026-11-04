import unittest

from metricpact.benchmark import run_benchmark
from metricpact.data import ORDERS, ORDER_ITEMS
from metricpact.engine import GovernedCalendar, GrainError, MetricPact, Status, assert_unique, check_join_grain


class EngineTests(unittest.TestCase):
    def setUp(self): self.engine = MetricPact()
    def test_gross_total(self): self.assertEqual(self.engine.ask("gross sales").rows[0]["gross_sales"], 700)
    def test_net_total(self): self.assertEqual(self.engine.ask("net sales").rows[0]["net_sales"], 620)
    def test_orders(self): self.assertEqual(self.engine.ask("orders").rows[0]["order_count"], 6)
    def test_customers(self): self.assertEqual(self.engine.ask("customers").rows[0]["customer_count"], 4)
    def test_aov(self): self.assertEqual(self.engine.ask("average order value").rows[0]["average_order_value"], 116.67)
    def test_ambiguous_sales(self): self.assertEqual(self.engine.ask("sales").status, Status.CLARIFY)
    def test_region_group(self): self.assertEqual(len(self.engine.ask("gross sales by region").rows), 3)
    def test_region_filter(self): self.assertEqual(self.engine.ask("net sales in West").rows[0]["net_sales"], 150)
    def test_month_filter(self): self.assertEqual(self.engine.ask("orders 2026-02").rows[0]["order_count"], 2)
    def test_sql_is_transparent(self): self.assertIn("SUM(amount - refund)", self.engine.ask("net sales").sql)
    def test_assumptions_exposed(self): self.assertIn("Calendar dates use UTC", self.engine.ask("orders").assumptions)
    def test_cost_block(self): self.assertEqual(MetricPact(max_scan_rows=2).ask("orders").status, Status.BLOCKED)
    def test_grain_mismatch_blocked(self):
        with self.assertRaises(GrainError): check_join_grain(ORDERS, ORDER_ITEMS, "order_id")
    def test_preaggregation_allowed(self): self.assertEqual(check_join_grain(ORDERS, ORDER_ITEMS, "order_id", preaggregated=True)["cardinality"], "many-to-one")
    def test_duplicate_declared_grain(self):
        with self.assertRaises(GrainError): assert_unique([{"id": 1}, {"id": 1}], ("id",), "bad")
    def test_benchmark(self): self.assertEqual(run_benchmark()["accuracy"], 1.0)
    def test_unspecified_year_requires_calendar(self):
        result = self.engine.ask("gross sales by year")
        self.assertEqual(Status.CLARIFY, result.status)
        self.assertEqual(["calendar", "retail_fiscal"], result.evidence["available_calendars"])
    def test_calendar_year_keeps_one_bucket(self):
        result = self.engine.ask("gross sales by calendar year")
        self.assertEqual([{"year": "2026", "gross_sales": 700.0}], result.rows)
    def test_fiscal_year_moves_january_to_prior_year(self):
        result = self.engine.ask("gross sales by fiscal year")
        self.assertEqual([{"year": "FY2025", "gross_sales": 200.0}, {"year": "FY2026", "gross_sales": 500.0}], result.rows)
    def test_fiscal_quarter_boundaries(self):
        result = self.engine.ask("orders by fiscal quarter")
        self.assertEqual([{"quarter": "FY2025-Q4", "order_count": 2}, {"quarter": "FY2026-Q1", "order_count": 4}], result.rows)
    def test_calendar_evidence_and_sql(self):
        result = self.engine.ask("net sales by fiscal year")
        self.assertEqual("retail_fiscal", result.evidence["calendar"])
        self.assertEqual(2, result.evidence["year_start_month"])
        self.assertIn("CASE WHEN", result.sql)
    def test_conflicting_calendar_terms_require_clarification(self):
        self.assertEqual(Status.CLARIFY, self.engine.ask("gross sales by calendar fiscal year").status)
    def test_invalid_calendar_rejected(self):
        with self.assertRaises(ValueError): GovernedCalendar("bad", "Bad", 13)
    def test_empty_calendar_registry_rejected(self):
        with self.assertRaises(ValueError): MetricPact(calendars={})


if __name__ == "__main__": unittest.main()
