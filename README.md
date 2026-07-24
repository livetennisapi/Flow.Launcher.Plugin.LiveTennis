# Live Tennis — Flow Launcher plugin

Live tennis scores at a keystroke, powered by the
[Live Tennis API](https://livetennisapi.com).

| Query | Result |
|---|---|
| `tennis` | Every live match: `Player1 6-4 3-2 Player2`, tournament + round, who is serving and the current point score (tiebreaks flagged `TB`) |
| `tennis <name>` | Player search: ranking, tour, country, ranking points, ranking movement |

Enter copies the score/player line to the clipboard. The context menu
(Shift+Enter) also opens livetennisapi.com.

## Setup

1. Install the plugin: `pm install Live Tennis` (or from the plugin store).
2. Get a **free API key** (no card, 1000 requests/day, 30/min) at
   <https://livetennisapi.com/subscribe/free>.
3. Paste the key in **Flow settings → Plugins → Live Tennis → API key**.

Without a key the plugin shows a friendly pointer to the signup page; 401
and 429 responses are shown as readable result rows, never crashes.

## Notes

- Doubles matches show team names; the API reports the same score structure.
- The plugin uses only the Python standard library at runtime plus the
  `flowlauncher` JSON-RPC base (vendored in `lib/` by the release workflow).

## License

MIT
