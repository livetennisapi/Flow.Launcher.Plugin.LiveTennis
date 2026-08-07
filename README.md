# Live Tennis — Flow Launcher plugin

Live tennis scores at a keystroke — live matches, player search and
head-to-head records across ATP, WTA, Challenger, ITF and juniors, powered
by the [Live Tennis API](https://livetennisapi.com).

[![CI](https://github.com/livetennisapi/Flow.Launcher.Plugin.LiveTennis/actions/workflows/ci.yml/badge.svg)](https://github.com/livetennisapi/Flow.Launcher.Plugin.LiveTennis/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/livetennisapi/Flow.Launcher.Plugin.LiveTennis)](https://github.com/livetennisapi/Flow.Launcher.Plugin.LiveTennis/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Install

- **Plugin store:** `pm install Live Tennis` (or the plugin store UI). The
  plugin is in the official
  [Flow.Launcher.PluginsManifest](https://github.com/Flow-Launcher/Flow.Launcher.PluginsManifest);
  new versions can take a few hours to reach every manifest CDN.
- **Manual:** in Flow, run
  `pm install https://github.com/livetennisapi/Flow.Launcher.Plugin.LiveTennis/releases/download/v1.1.0/Flow.Launcher.Plugin.LiveTennis.zip`
  — or download that zip and extract it into
  `%APPDATA%\FlowLauncher\Plugins\`, then restart Flow.

## Quickstart

1. Get a **free API key** (no card, 100 requests/day, 30/min) at
   <https://livetennisapi.com/subscribe/free> — it looks like `twjp_...`.
2. Paste it in **Flow settings → Plugins → Live Tennis → API key**.
3. Type away:

| Query | Result | Plan |
|---|---|---|
| `tennis` | Every live match: `Player1 6-4 3-2 Player2`, tournament + round, who is serving and the current point score (tiebreaks flagged `TB`) | FREE |
| `tennis <name>` | Player search: ranking, tour, country, ranking points, ranking movement | FREE |
| `tennis h2h <p1> vs <p2>` | Head-to-head record — total wins, undecided meetings, per-surface split, and the 10 most recent meetings (results archive 1968–2022 + live-era matches 2023→now) | BASIC, or any History plan |

Enter copies the score/player/record line to the clipboard. The context menu
(Shift+Enter) also opens livetennisapi.com.

Without a key the plugin shows a friendly pointer to the signup page. Errors
come back as readable result rows, never crashes: 401 (bad key), 403 (plan
upgrade needed — Enter opens the upgrade page), per-minute and daily 429s
(the daily row shows the exact reset time), and the API's 24-hour
`abuse_throttled` block (shown with the resume time).

## Quotas

| Plan | Requests/min | Requests/day | Price |
|---|---|---|---|
| FREE | 30 | 100 | $0 |
| BASIC | 60 | 1,000 | $9.99/mo |
| PRO | 300 | 10,000 | $29.99/mo |
| ULTRA | 600 | 500,000 | $99.99/mo |

The plugin only calls the API when you type, so a free key's 100/day goes a
long way. If you build something always-on around the same key, poll no
faster than every 15 minutes on FREE — BASIC recommended.

## Auth

The plugin sends your key as the `X-API-Key` header. Calling the API
yourself? `Authorization: Bearer twjp_...` is the preferred form; `X-API-Key`
and `?token=` (for WebSockets) also work. Full reference:
[docs.livetennisapi.com](https://docs.livetennisapi.com).

## Notes

- Doubles matches show team names; the API reports the same score structure.
- The plugin uses only the Python standard library at runtime plus the
  `flowlauncher` JSON-RPC base (vendored in `lib/` by the release workflow).

## Links

- Docs: <https://docs.livetennisapi.com>
- Free API key: <https://livetennisapi.com/subscribe/free>
- Upgrade: <https://livetennisapi.com/subscribe/upgrade>
- Discord: <https://discord.gg/f8WUZHgDm6>
- GitHub org: <https://github.com/livetennisapi>

## License

MIT — see [LICENSE](LICENSE).

## Affiliate program

Know developers who need tennis data? The [affiliate program](https://affiliates.livetennisapi.com/program) pays 51% recurring commission for the life of every referred subscription — 30-day cookie, and the people you refer get 10% off.
