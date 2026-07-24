# -*- coding: utf-8 -*-
"""Live Tennis — Flow Launcher plugin.

`tennis`          -> live matches with set-by-set score and serving hint
`tennis <player>` -> player search (ranking, country, tour)

Data: Live Tennis API (https://livetennisapi.com), free tier 1000 req/day.
"""

import sys
from pathlib import Path

plugindir = Path.absolute(Path(__file__).parent)
paths = (".", "lib", "plugin")
sys.path = [str(plugindir / p) for p in paths] + sys.path

import codecs
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from flowlauncher import FlowLauncher

API_BASE = "https://api.livetennisapi.com/api/public/v1"
SITE = "https://livetennisapi.com"
FREE_KEY_URL = "https://livetennisapi.com/subscribe/free"
ICON = "Images/icon.png"
TIMEOUT_S = 8


class LiveTennis(FlowLauncher):
    # ------------------------------------------------------------------ http
    def _api_key(self):
        return (self.rpc_request.get("settings", {}) or {}).get("api_key", "").strip()

    def _get(self, path, params):
        """GET an API endpoint. Returns (payload, error_result_row)."""
        key = self._api_key()
        if not key:
            return None, self._row(
                "Set your Live Tennis API key first",
                "Free key (no card, 1000 req/day) at livetennisapi.com/subscribe/free "
                "— then paste it in this plugin's settings. Enter opens the signup page.",
                action=("open_url", [FREE_KEY_URL]),
            )
        url = "{}{}?{}".format(API_BASE, path, urllib.parse.urlencode(params))
        req = urllib.request.Request(
            url,
            headers={
                "X-API-Key": key,
                "User-Agent": "Flow.Launcher.Plugin.LiveTennis/1.0.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return None, self._row(
                    "API key rejected (401)",
                    "Check the key in Flow settings → Plugins → Live Tennis. "
                    "Need one? livetennisapi.com/subscribe/free — Enter opens it.",
                    action=("open_url", [FREE_KEY_URL]),
                )
            if e.code == 429:
                return None, self._row(
                    "Rate limit reached (429)",
                    "The free tier allows 30 requests/min and 1000/day — try again in a minute.",
                )
            return None, self._row(
                "Live Tennis API error (HTTP {})".format(e.code),
                "The API answered but not with data — try again shortly.",
            )
        except Exception:
            return None, self._row(
                "Can't reach the Live Tennis API",
                "Check your internet connection, then try again.",
            )

    # ------------------------------------------------------------- formatting
    @staticmethod
    def _dedupe_event(tournament, round_):
        """`round` often restates `tournament` (e.g. 'M15 Bali' / 'M15 Bali -
        Quarter-finals') — keep each piece of information exactly once."""
        t = (tournament or "").strip()
        r = (round_ or "").strip()
        if not r:
            return t
        if not t:
            return r
        tl, rl = t.lower(), r.lower()
        if rl == tl or rl in tl:
            return t
        if rl.startswith(tl):
            suffix = r[len(t):].lstrip(" -–—·:,")
            return "{} · {}".format(t, suffix) if suffix else t
        if " - " in r:
            head, tail = r.split(" - ", 1)
            if head.strip().lower() in tl:
                tail = tail.strip()
                return "{} · {}".format(t, tail) if tail else t
        return "{} · {}".format(t, r)

    @staticmethod
    def _set_score(score):
        """'6-4 3-2' from games = [[p1 per-set...], [p2 per-set...]]."""
        if not score:
            return "vs"
        games = score.get("games") or []
        if len(games) == 2 and games[0]:
            return " ".join("{}-{}".format(a, b) for a, b in zip(games[0], games[1]))
        return "vs"

    @staticmethod
    def _serving_hint(score, p1, p2):
        """'Alcaraz serving · 30-15' — server is nullable, points are strings."""
        if not score:
            return ""
        parts = []
        server = score.get("server")
        if server == 1:
            parts.append("{} serving".format(p1))
        elif server == 2:
            parts.append("{} serving".format(p2))
        points = score.get("points") or []
        if len(points) == 2:
            pts = "{}-{}".format(points[0], points[1])
            parts.append("TB {}".format(pts) if score.get("is_tiebreak") else pts)
        return " · ".join(parts)

    def _row(self, title, subtitle, action=None, context=None):
        row = {"Title": title, "SubTitle": subtitle, "IcoPath": ICON}
        if action:
            row["JsonRPCAction"] = {"method": action[0], "parameters": action[1]}
        if context is not None:
            row["ContextData"] = context
        return row

    # ------------------------------------------------------------------ query
    def query(self, query):
        q = (query or "").strip()
        if q:
            return self.search_players(q)
        return self.live_matches()

    def live_matches(self):
        payload, err = self._get("/matches", {"status": "live", "limit": 30})
        if err:
            return [err]
        matches = payload.get("data") or []
        if not matches:
            return [
                self._row(
                    "No live matches right now",
                    "Type a name to search players, or Enter to open livetennisapi.com",
                    action=("open_url", [SITE]),
                )
            ]
        results = []
        for m in matches:
            players = m.get("players") or {}
            p1 = (players.get("p1") or {}).get("name") or "Player 1"
            p2 = (players.get("p2") or {}).get("name") or "Player 2"
            title = "{} {} {}".format(p1, self._set_score(m.get("score")), p2)
            event = self._dedupe_event(m.get("tournament"), m.get("round"))
            hint = self._serving_hint(m.get("score"), p1, p2)
            subtitle = " · ".join(x for x in (event, hint) if x) or "Live match"
            copy_text = "{} — {}".format(title, event) if event else title
            results.append(
                self._row(
                    title,
                    subtitle,
                    action=("copy_text", [copy_text]),
                    context=[copy_text],
                )
            )
        return results

    def search_players(self, name):
        payload, err = self._get("/players", {"search": name, "limit": 10})
        if err:
            return [err]
        players = payload.get("data") or []
        if not players:
            return [
                self._row(
                    "No players match '{}'".format(name),
                    "Try a shorter spelling — the search matches partial names.",
                )
            ]
        results = []
        for p in players:
            pname = p.get("name") or "Unknown"
            bits = []
            if p.get("ranking") is not None:
                bits.append("#{}".format(p["ranking"]))
            if p.get("tour"):
                bits.append(str(p["tour"]).upper())
            if p.get("country"):
                bits.append(str(p["country"]).upper())
            if p.get("ranking_points") is not None:
                bits.append("{} pts".format(p["ranking_points"]))
            movement = p.get("ranking_movement")
            if movement in ("up", "down"):
                bits.append("ranking {}".format(movement))
            subtitle = " · ".join(bits) or "Player"
            copy_text = "{} ({})".format(pname, subtitle) if bits else pname
            results.append(
                self._row(
                    pname,
                    subtitle,
                    action=("copy_text", [copy_text]),
                    context=[copy_text],
                )
            )
        return results

    # ---------------------------------------------------------------- actions
    def context_menu(self, data):
        text = data[0] if data else ""
        return [
            self._row("Copy to clipboard", text, action=("copy_text", [text])),
            self._row(
                "Open livetennisapi.com",
                "Live scores, docs and free API keys",
                action=("open_url", [SITE]),
            ),
        ]

    def copy_text(self, text):
        # Flow Launcher runs on Windows; `clip` is always present there.
        # The UTF-16LE BOM makes `clip` treat the input as Unicode.
        payload = codecs.BOM_UTF16_LE + text.encode("utf-16-le")
        subprocess.run("clip", input=payload, check=False)

    def open_url(self, url):
        webbrowser.open(url)


if __name__ == "__main__":
    LiveTennis()
