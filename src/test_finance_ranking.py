"""Offline tests for the finance ranking and channel guard configuration."""

import unittest
from unittest.mock import patch

import finance_ranking
from channel_config import active_channel


class FinanceRankingTests(unittest.TestCase):
    def test_content_is_transparent_and_contains_risk_disclaimer(self):
        content = finance_ranking.ranking_to_content({
            "kind": "stocks",
            "period": "5 trading sessions",
            "universe": "configured watchlist (2 symbols)",
            "asOf": "2026-09-09T14:00:00+00:00",
            "source": "test",
            "sourceUrl": "https://example.test/market-data",
            "items": [
                {"rank": 1, "name": "Alpha", "symbol": "ALP", "changePct": 12.34},
                {"rank": 2, "name": "Beta", "symbol": "BET", "changePct": -1.2},
            ],
            "errors": [],
        })
        self.assertEqual(content["language"], "en")
        self.assertIn("not a buy list", content["body"])
        self.assertIn("Alpha", content["body"])
        self.assertIn("risk", content["body"])

    def test_stock_ranking_is_sorted_without_ai(self):
        payloads = {
            "AAA": {
                "chart": {"result": [{
                    "timestamp": [1, 2, 3, 4, 5, 6],
                    "indicators": {"quote": [{"close": [100, 100, 100, 100, 100, 110]}]},
                    "meta": {"currency": "USD", "longName": "A"},
                }]}
            },
            "BBB": {
                "chart": {"result": [{
                    "timestamp": [1, 2, 3, 4, 5, 6],
                    "indicators": {"quote": [{"close": [100, 100, 100, 100, 100, 105]}]},
                    "meta": {"currency": "USD", "longName": "B"},
                }]}
            },
        }

        def fake_get(url, timeout=20):
            return payloads["AAA" if "/AAA?" in url else "BBB"]

        with patch.object(finance_ranking, "_get_json", side_effect=fake_get):
            result = finance_ranking.fetch_stock_ranking(
                top_n=2, lookback_sessions=5,
                watchlist=[{"symbol": "AAA", "name": "A"}, {"symbol": "BBB", "name": "B"}],
            )
        self.assertEqual([x["symbol"] for x in result["items"]], ["AAA", "BBB"])
        self.assertEqual(result["items"][0]["changePct"], 10.0)
        self.assertEqual(result["items"][1]["changePct"], 5.0)

    def test_channel_profiles_are_explicit(self):
        with patch.dict("os.environ", {"CHANNEL_MODE": "difference_money"}, clear=False):
            channel = active_channel()
        self.assertEqual(channel["channelId"], "UC_FrWjKB66YyV9AeKPaEHIA")
        self.assertEqual(channel["language"], "en")


if __name__ == "__main__":
    unittest.main()
