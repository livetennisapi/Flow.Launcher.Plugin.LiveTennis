#!/bin/sh
# Truth-pin: fail CI when stale Live Tennis API product facts creep back in.
# POSIX sh; needs only git.
set -u

cd "$(dirname "$0")/.."

# Tracked text files; CHANGELOG may describe history, lib/ is vendored,
# and this script's own patterns must not trip themselves.
PATHS="*.md *.py *.yaml *.yml *.json :(exclude)CHANGELOG.md :(exclude)lib :(exclude)scripts"

fail=0

forbid() {
    # shellcheck disable=SC2086
    hits=$(git grep -inE "$1" -- $PATHS 2>/dev/null)
    if [ -n "$hits" ]; then
        echo "FORBIDDEN ($2):"
        printf '%s\n' "$hits"
        fail=1
    fi
}

# Stale quota copy: the old 100k/day free quota, in any spelling.
forbid '100[,.]?000[^0-9]*(requests?)?[^0-9]*(per[- ])?day|100k[^a-z0-9]*/?[^a-z0-9]*day' 'stale 100,000/day quota'
# Free tier must never be paired with 1,000/day (that is BASIC).
forbid 'free[^|]*(1,000|1k)[^0-9]*(per[- ])?day|free tier[^.]*(1,000|1k)' 'free tier paired with 1,000/day'
# Docs live at docs.livetennisapi.com, never livetennisapi.com/docs.
forbid 'livetennisapi\.com/docs' 'wrong docs URL — use docs.livetennisapi.com'
# Org identity only; no personal account in repo copy or metadata.
forbid 'bensynapse' 'personal account reference'
# Daily reset is a resets_at instant, not midnight UTC.
forbid 'midnight UTC' 'daily reset is not midnight UTC'

# Required current facts (this repo states quotas, so both must be present).
# shellcheck disable=SC2086
if ! git grep -qE '100 ?(requests?)? ?(/|per) ?day' -- $PATHS 2>/dev/null; then
    echo "MISSING: FREE quota copy ('100/day' or '100 requests/day')"
    fail=1
fi
# shellcheck disable=SC2086
if ! git grep -q 'docs\.livetennisapi\.com' -- $PATHS 2>/dev/null; then
    echo "MISSING: docs.livetennisapi.com link"
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "truthcheck OK"
fi
exit "$fail"
