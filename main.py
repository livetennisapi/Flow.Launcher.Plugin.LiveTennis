# -*- coding: utf-8 -*-
"""Live Tennis — Flow Launcher plugin.

`tennis`                  -> live matches with set-by-set score and serving hint
`tennis <player>`         -> player search (ranking, country, tour)
`tennis h2h <p1> vs <p2>` -> head-to-head record (BASIC key or any History plan)

Data: Live Tennis API (https://livetennisapi.com), free tier 100 req/day.
"""

import sys
from pathlib import Path

plugindir = Path.absolute(Path(__file__).parent)
paths = (".", "lib", "plugin")
sys.path = [str(plugindir / p) for p in paths] + sys.path

import codecs
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from flowlauncher import FlowLauncher

VERSION = "1.1.0"
API_BASE = "https://api.livetennisapi.com/api/public/v1"
SITE = "https://livetennisapi.com"
FREE_KEY_URL = "https://livetennisapi.com/subscribe/free"
UPGRADE_URL = "https://livetennisapi.com/subscribe/upgrade"
ICON = "Images/icon.png"
TIMEOUT_S = 8


class LiveTennis(FlowLauncher):
    # ------------------------------------------------------------------ http
    def _api_key(self):
        return (self.rpc_request.get("settings", {}) or {}).get("api_key", "").strip()

    def _get(self, path, params, upgrade_hint=None):
        """GET an API endpoint. Returns (payload, error_result_row)."""
        key = self._api_key()
        if not key:
            return None, self._row(
                "Set your Live Tennis API key first",
                "Free key (no card, 100 req/day) at livetennisapi.com/subscribe/free "
                "— then paste it in this plugin's settings. Enter opens the signup page.",
                action=("open_url", [FREE_KEY_URL]),
            )
        url = "{}{}?{}".format(API_BASE, path, urllib.parse.urlencode(params))
        req = urllib.request.Request(
            url,
            headers={
                "X-API-Key": key,
                "User-Agent": "Flow.Launcher.Plugin.LiveTennis/{}".format(VERSION),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            return None, self._http_error_row(e.code, self._error_body(e), upgrade_hint)
        except Exception:
            return None, self._row(
                "Can't reach the Live Tennis API",
                "Check your internet connection, then try again.",
            )

    @staticmethod
    def _error_body(e):
        """Parse the API's JSON error body; {} when there is none."""
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _epoch_utc(epoch):
        """'2026-08-08 02:50' from a Unix epoch; '' when unusable."""
        try:
            return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(epoch)))
        except (TypeError, ValueError, OverflowError, OSError):
            return ""

    def _http_error_row(self, status, body, upgrade_hint=None):
        """One readable result row for any API error response."""
        code = body.get("error") or ""
        if status == 401:
            return self._row(
                "API key rejected (401)",
                "Check the key in Flow settings → Plugins → Live Tennis. "
                "Need one? livetennisapi.com/subscribe/free — Enter opens it.",
                action=("open_url", [FREE_KEY_URL]),
            )
        if status == 403:
            return self._row(
                "{} (403)".format(upgrade_hint or "Your plan does not cover this lookup"),
                "Enter opens the upgrade page — livetennisapi.com/subscribe/upgrade.",
                action=("open_url", [body.get("upgrade_url") or UPGRADE_URL]),
            )
        if status == 429:
            if code == "abuse_throttled":
                when = self._epoch_utc(body.get("retry_at_epoch"))
                return self._row(
                    "Temporarily blocked for repeated over-quota requests (429)",
                    "The API blocks clients that keep retrying past their limit for 24 hours"
                    + (" — access resumes {} UTC.".format(when) if when else ".")
                    + " Fix any script or retry loop hammering this key, then wait it out.",
                )
            if body.get("scope") == "day":
                resets = body.get("resets_at")
                return self._row(
                    "Daily quota used up (429)",
                    ("Resets at {}. ".format(resets) if resets else "")
                    + "A free key covers 100 requests/day — upgrading raises the "
                    "daily quota. Enter opens the upgrade page.",
                    action=("open_url", [body.get("upgrade_url") or UPGRADE_URL]),
                )
            return self._row(
                "Rate limit reached (429)",
                "The free tier allows 30 requests/min and 100/day — try again in a minute.",
            )
        if status == 400 and code == "ambiguous_name":
            candidates = body.get("candidates") or []
            names = ", ".join(
                (c.get("name") if isinstance(c, dict) else str(c)) for c in candidates[:6]
            )
            return self._row(
                "Name matches more than one player",
                "Be more specific — candidates: {}".format(names)
                if names
                else (body.get("detail") or "Add more letters to the name and retry."),
            )
        return self._row(
            "Live Tennis API error (HTTP {})".format(status),
            body.get("detail") or "The API answered but not with data — try again shortly.",
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
        if q.lower() == "h2h" or q.lower().startswith("h2h "):
            return self.head_to_head(q[3:])
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

    @staticmethod
    def _h2h_names(spec):
        """('sinner', 'alcaraz') from 'sinner vs alcaraz'; None when unusable.
        Accepts 'vs', 'vs.', 'v' and 'v.' as the separator; the API wants at
        least 3 characters per name fragment."""
        parts = re.split(r"\s+vs?\.?\s+", spec.strip(), maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            return None
        p1, p2 = parts[0].strip(), parts[1].strip()
        if len(p1) < 3 or len(p2) < 3:
            return None
        return p1, p2

    def head_to_head(self, spec):
        names = self._h2h_names(spec)
        if not names:
            return [
                self._row(
                    "Head-to-head: tennis h2h <player> vs <player>",
                    "Example: tennis h2h sinner vs alcaraz — at least 3 letters per "
                    "name. Needs a BASIC key or any History plan.",
                )
            ]
        p1, p2 = names
        payload, err = self._get(
            "/h2h",
            {"p1": p1, "p2": p2},
            upgrade_hint="Head-to-head needs BASIC ($9.99/mo) or any History plan",
        )
        if err:
            return [err]
        players = payload.get("players")
        if not players:
            return [
                self._row(
                    "No head-to-head for '{}' vs '{}'".format(p1, p2),
                    "No player matched one of the names — try fuller spellings.",
                )
            ]
        n1 = (players.get("p1") or {}).get("name") or p1
        n2 = (players.get("p2") or {}).get("name") or p2
        totals = payload.get("totals") or {}
        title = "{} {}-{} {}".format(
            n1, totals.get("p1_wins") or 0, totals.get("p2_wins") or 0, n2
        )
        bits = ["{} meetings".format(totals.get("meetings") or 0)]
        if totals.get("undecided"):
            bits.append("{} undecided".format(totals["undecided"]))
        for surface, split in sorted((payload.get("by_surface") or {}).items()):
            bits.append(
                "{} {}-{}".format(surface, split.get("p1") or 0, split.get("p2") or 0)
            )
        subtitle = " · ".join(bits)
        copy_text = "{} ({})".format(title, subtitle)
        results = [
            self._row(title, subtitle, action=("copy_text", [copy_text]), context=[copy_text])
        ]
        for m in (payload.get("meetings") or [])[:10]:
            winner = m.get("winner")
            won = (
                "{} won".format(n1 if winner == 1 else n2)
                if winner in (1, 2)
                else "no result"
            )
            event = self._dedupe_event(m.get("tournament"), m.get("round"))
            mtitle = " · ".join(str(x) for x in (m.get("date"), event) if x) or "Meeting"
            outcome = m.get("outcome")
            sub_bits = [m.get("surface"), m.get("score"), won]
            if outcome and outcome != "completed":
                sub_bits.append(outcome)
            msub = " · ".join(str(x) for x in sub_bits if x)
            mcopy = " · ".join(x for x in (mtitle, msub) if x)
            results.append(
                self._row(mtitle, msub, action=("copy_text", [mcopy]), context=[mcopy])
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
                "Live scores and free API keys (docs at docs.livetennisapi.com)",
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
