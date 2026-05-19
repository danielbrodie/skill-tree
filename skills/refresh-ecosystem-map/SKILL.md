---
description: Monthly process for keeping docs/ecosystem-map.md current. Runs the canonical survey query against /last30days, cross-references results with existing entries, drafts additions for new agent platforms / skill packagers / installers / workflow plugins / failure modes, and opens a PR. USE WHEN the user says "refresh the ecosystem map", "monthly survey", "what's new in skills since last month", or it has been ~30 days since the last refresh.
---

You are skill-tree's ecosystem-map refresh skill. `docs/ecosystem-map.md` is the institutional knowledge consumed by every other institutional-knowledge skill (audit, catalog, diagnose, install). If it drifts, every downstream recommendation drifts with it. Your job is to keep it within ~30 days of reality.

## When to run

- **Monthly** is the target cadence per BRO-194.
- **Triggered manually** when the user says any of: "refresh the ecosystem map", "monthly survey", "what's new in the skill ecosystem", "audit ecosystem-map".
- **Auto-scheduled** via `/schedule` (see § "Automating the cadence" at the bottom).

## Step 1 — check freshness

Before doing the work, check whether the doc is genuinely due:

```bash
git log -1 --format="%ai" docs/ecosystem-map.md | python3 -c "
import sys, datetime
line = sys.stdin.read().strip()
last = datetime.datetime.fromisoformat(line.replace(' ', 'T', 1))
days = (datetime.datetime.now(last.tzinfo) - last).days
print(f'Last touched: {line}')
print(f'Days since: {days}')
print('Run a refresh' if days >= 25 else 'Skip — too recent')
"
```

If under ~25 days since the last refresh, skip the run unless the user explicitly wants it. The point of the cadence is signal density, not churn.

## Step 2 — run the canonical survey

Use the `/last30days` skill (installed) or its underlying CLI. Two survey queries to run in parallel — the first catches the wide-net "what shipped" cohort, the second catches the deeper "real-world failure modes" cohort:

```
/last30days "new AI agent skill packagers and multi-agent skill installer"
/last30days "claude code plugin failure modes and skill installation problems"
```

The first is the same query the SessionStart banner uses on this machine, so historical results accumulate in the corpus. Don't rename it without a reason.

If `/last30days` isn't installed in the host agent, fall back to GitHub trending search + Reddit search:

```bash
gh api --paginate -X GET search/repositories \
  -f "q=skill claude-code created:>$(date -v-30d +%Y-%m-%d)" \
  -f "sort=stars" -f "order=desc" 2>/dev/null | head -100
```

## Step 3 — cross-reference against existing entries

Read `docs/ecosystem-map.md` in full. Build a mental map of:

- Agent platforms already listed (table § "Agent platforms that consume skills")
- Skill packagers already listed (table § "Skill packagers")
- Workflow plugins already listed (table § "Claude Code workflow plugins (new category, May 2026)")
- Installers already listed (table § "Installers")
- Aggregators already listed (table § "Awesome-list aggregators")
- Failure-mode signatures already documented (§ "Recognized failure-mode signatures")

For each `/last30days` result, classify:

| Result type | What to do |
|---|---|
| **New skill packager repo** | Add row to § "Skill packagers" with maintainer, focus, install command. Include GitHub link. |
| **New workflow plugin** | Add row to § "Claude Code workflow plugins" with source, focus, install. |
| **New agent platform** | Add row to § "Agent platforms" with skill load path, skill format, notable details. |
| **New installer / CLI** | Add row to § "Installers" with scope, strength, removal command. |
| **New aggregator / awesome-list** | Add row to § "Awesome-list aggregators" with focus. |
| **Reported failure mode** | Add to § "Recognized failure-mode signatures" if it generalizes; cite the source post if it doesn't. |
| **Already covered** | Skip. Note in PR body that it's already covered to avoid double-add on the next run. |
| **Out of scope** | General AI news, single-skill posts without distribution path, etc. Skip with brief note. |

## Step 4 — verify each addition against current state

Before adding a row to the doc, **verify the install command actually works** with the agent CLIs currently installed locally:

```bash
# For Claude Code marketplace claims
claude plugin marketplace list 2>&1 | grep -i <plugin-owner>

# For npx skills/vercel-labs claims
npx skills find <name> 2>&1 | head -20

# For GitHub repos
gh repo view <owner>/<repo> 2>&1 | head -20
```

Don't add a row claiming an install command that fails. If the source post or repo describes an install command that doesn't work, note it as a documented-but-untested entry rather than as a verified-working one.

## Step 5 — draft the PR

Title: `docs(ecosystem-map): YYYY-MM-DD survey adds N entries`

Body:
```
## Summary

Monthly ecosystem-map refresh per BRO-194. /last30days surveys turned up
N new entries to add and M already-covered hits.

## Added

### Skill packagers
- [<owner>/<repo>](url) — <focus>. <install>. <source: Reddit/Tweet/post>.
- ...

### Workflow plugins
- ...

### Installers
- ...

### Failure-mode signatures
- New signature #<N>: <description>. Source: <where seen>.

## Already covered (no action)

- [<owner>/<repo>](url) — listed since YYYY-MM. Mentioned again this month.

## Verification

- [x] Each install command was run against the local CLIs.
- [x] No fabricated URLs — every link traces back to a source post or repo.

## Test plan

- [ ] After merge: audit / catalog / diagnose / install can cite the new entries by reading the updated doc (no code change needed).
```

## Step 6 — update the "Last refreshed" line

Edit the top of `docs/ecosystem-map.md`:

```
Last refreshed: YYYY-MM-DD (post-survey N new entries).
```

This is how downstream readers — and the `/skill-tree:refresh-ecosystem-map` Step 1 freshness check — know when the next refresh is due.

## Notes

- **Don't invent entries.** Every added row should trace to a `/last30days` result, a GitHub repo, or a documented source. Fabrication poisons every downstream recommendation.
- **Be terse.** Each row is one sentence of "focus" plus install command. The doc isn't a review site; it's a dispatch table.
- **Failure-mode signatures are the highest-value adds.** Skills/packagers shift slowly; new failure modes drive immediate downstream value through `/skill-tree:diagnose`.
- **PR title carries the date.** The monthly cadence is visible in `git log docs/ecosystem-map.md` as one PR per month.

## Automating the cadence

Use the host agent's scheduler. For Claude Code, the `schedule` skill (already installed) can register a monthly run:

```
/schedule create
  name: "Monthly skill-tree ecosystem refresh"
  cron: "0 14 1 * *"          # 1st of each month at 14:00
  command: "/skill-tree:refresh-ecosystem-map"
```

The cron schedule should match when the user is actually around to review PRs the scheduled run produces — first-of-month at 14:00 is a default; adjust to taste.

If the host agent doesn't have a scheduler, document the cadence in the user's calendar instead. The doc-update PR is small enough that manual triggering once a month is sustainable.
