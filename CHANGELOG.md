# Changelog

All notable changes to this plugin. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-08-07

### Added
- `tennis h2h <player> vs <player>` — head-to-head record (total wins,
  undecided meetings, per-surface split, 10 most recent meetings) from the
  API's `/h2h` endpoint. Needs BASIC or any History plan; free keys get a
  graceful upgrade row that opens the upgrade page.
- Distinct handling for every 429 shape: per-minute, daily (shows the exact
  reset instant from `resets_at`), and the 24-hour `abuse_throttled` block
  (shows the resume time and advises fixing retry loops).
- 403 `upgrade_required` handling with a one-keystroke path to the upgrade
  page; `ambiguous_name` responses list the candidate players.
- CI workflow: syntax check, unit tests, and a truth-pin script
  (`scripts/truthcheck.sh`) that fails the build on stale product facts.
- Unit tests for the formatting, parsing, and error-row helpers.
- `.gitignore` (bytecode, zip artifacts).

### Changed
- Quota copy tracks the 2026-08-06 grid: FREE 100 requests/day, BASIC
  1,000/day, PRO 10,000/day, ULTRA 500,000/day.
- README rebuilt: store install is live (manifest PR #714 merged
  2026-08-06), tier-gated query table, quota table, auth and links.
- Release workflow now skips publishing when the version's tag already
  exists, so a later push can never overwrite a released asset; the release
  zip no longer bundles tests or scripts.

### Fixed
- The v1.0.0 release asset had been overwritten by a 2026-08-06 rebuild
  while the `v1.0.0` tag still pointed at the original commit; v1.1.0
  restores tag/release/asset consistency and the workflow guard prevents a
  recurrence.

## [1.0.0] - 2026-07-24

### Added
- Initial release: live matches with set-by-set score, serving indicator and
  point score (`tennis`), and player search with ranking, tour, country,
  points and ranking movement (`tennis <name>`).
