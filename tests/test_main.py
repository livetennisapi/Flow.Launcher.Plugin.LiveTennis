# -*- coding: utf-8 -*-
"""Unit tests for the pure helpers in main.py (no Flow runtime, no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import LiveTennis  # noqa: E402


def plugin():
    """An instance without running FlowLauncher's JSON-RPC __init__."""
    return object.__new__(LiveTennis)


class DedupeEventTest(unittest.TestCase):
    def test_round_restates_tournament(self):
        self.assertEqual(
            LiveTennis._dedupe_event("M15 Bali", "M15 Bali - Quarter-finals"),
            "M15 Bali · Quarter-finals",
        )

    def test_round_equals_tournament(self):
        self.assertEqual(LiveTennis._dedupe_event("M15 Bali", "m15 bali"), "M15 Bali")

    def test_distinct_pieces_joined(self):
        self.assertEqual(LiveTennis._dedupe_event("Wimbledon", "Final"), "Wimbledon · Final")

    def test_missing_pieces(self):
        self.assertEqual(LiveTennis._dedupe_event("", "Final"), "Final")
        self.assertEqual(LiveTennis._dedupe_event("Wimbledon", None), "Wimbledon")


class SetScoreTest(unittest.TestCase):
    def test_two_sets(self):
        score = {"games": [[6, 3], [4, 2]]}
        self.assertEqual(LiveTennis._set_score(score), "6-4 3-2")

    def test_no_score(self):
        self.assertEqual(LiveTennis._set_score(None), "vs")
        self.assertEqual(LiveTennis._set_score({"games": []}), "vs")


class ServingHintTest(unittest.TestCase):
    def test_server_and_points(self):
        score = {"server": 2, "points": ["30", "15"]}
        self.assertEqual(LiveTennis._serving_hint(score, "A", "B"), "B serving · 30-15")

    def test_tiebreak_flagged(self):
        score = {"server": 1, "points": ["6", "5"], "is_tiebreak": True}
        self.assertEqual(LiveTennis._serving_hint(score, "A", "B"), "A serving · TB 6-5")

    def test_empty(self):
        self.assertEqual(LiveTennis._serving_hint(None, "A", "B"), "")


class H2hNamesTest(unittest.TestCase):
    def test_plain_vs(self):
        self.assertEqual(LiveTennis._h2h_names("sinner vs alcaraz"), ("sinner", "alcaraz"))

    def test_separator_variants(self):
        for sep in ("VS", "vs.", "v", "V."):
            self.assertEqual(
                LiveTennis._h2h_names("sinner {} alcaraz".format(sep)),
                ("sinner", "alcaraz"),
                sep,
            )

    def test_multiword_names(self):
        self.assertEqual(
            LiveTennis._h2h_names("de minaur vs van assche"),
            ("de minaur", "van assche"),
        )

    def test_unusable(self):
        self.assertIsNone(LiveTennis._h2h_names("sinner"))
        self.assertIsNone(LiveTennis._h2h_names("ab vs alcaraz"))
        self.assertIsNone(LiveTennis._h2h_names("sinner vs al"))
        self.assertIsNone(LiveTennis._h2h_names(""))


class EpochUtcTest(unittest.TestCase):
    def test_known_epoch(self):
        self.assertEqual(LiveTennis._epoch_utc(0), "1970-01-01 00:00")

    def test_unusable(self):
        self.assertEqual(LiveTennis._epoch_utc(None), "")
        self.assertEqual(LiveTennis._epoch_utc("soon"), "")


class HttpErrorRowTest(unittest.TestCase):
    def test_401(self):
        row = plugin()._http_error_row(401, {})
        self.assertIn("401", row["Title"])
        self.assertEqual(row["JsonRPCAction"]["method"], "open_url")

    def test_403_uses_hint_and_body_url(self):
        row = plugin()._http_error_row(
            403,
            {"error": "upgrade_required", "upgrade_url": "https://example.test/up"},
            upgrade_hint="Head-to-head needs BASIC ($9.99/mo) or any History plan",
        )
        self.assertIn("Head-to-head needs BASIC", row["Title"])
        self.assertEqual(row["JsonRPCAction"]["parameters"], ["https://example.test/up"])

    def test_429_minute(self):
        row = plugin()._http_error_row(429, {"error": "rate_limited"})
        self.assertIn("Rate limit", row["Title"])
        self.assertIn("30 requests/min", row["SubTitle"])

    def test_429_daily_shows_reset(self):
        row = plugin()._http_error_row(
            429,
            {
                "error": "rate_limited",
                "scope": "day",
                "limit_per_day": 100,
                "resets_at": "2026-08-07T21:00:00Z",
            },
        )
        self.assertIn("Daily quota", row["Title"])
        self.assertIn("2026-08-07T21:00:00Z", row["SubTitle"])
        self.assertEqual(row["JsonRPCAction"]["method"], "open_url")

    def test_429_abuse_throttled(self):
        row = plugin()._http_error_row(
            429, {"error": "abuse_throttled", "retry_at_epoch": 0}
        )
        self.assertIn("Temporarily blocked", row["Title"])
        self.assertIn("1970-01-01 00:00 UTC", row["SubTitle"])
        self.assertIn("retry loop", row["SubTitle"])

    def test_400_ambiguous_name(self):
        row = plugin()._http_error_row(
            400,
            {"error": "ambiguous_name", "candidates": [{"name": "A. Zverev"}, "M. Zverev"]},
        )
        self.assertIn("more than one player", row["Title"])
        self.assertIn("A. Zverev", row["SubTitle"])
        self.assertIn("M. Zverev", row["SubTitle"])

    def test_generic_uses_detail(self):
        row = plugin()._http_error_row(502, {"detail": "upstream sad"})
        self.assertIn("502", row["Title"])
        self.assertEqual(row["SubTitle"], "upstream sad")


if __name__ == "__main__":
    unittest.main()
