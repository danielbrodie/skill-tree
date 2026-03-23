---
title: "feat: OpenClaw plugin integration for skill-tree"
type: feat
status: completed
date: 2026-03-23
origin: docs/brainstorms/2026-03-23-openclaw-integration-brainstorm.md
---

# OpenClaw Plugin Integration

Native OpenClaw plugin so Felix (and any OpenClaw user) gets skill-tree's clustering and routing. Follows the `open-prose` pattern: `openclaw.plugin.json` + empty `index.ts` + skills that invoke the existing Python scripts.

(see brainstorm: docs/brainstorms/2026-03-23-openclaw-integration-brainstorm.md)

## Key Decisions (from brainstorm)

- Cluster routers → `~/.openclaw/skills/` (shared managed path)
- Leaves stay in place, hidden via `disable-model-invocation: true` only
- Manifest at `~/.openclaw/skills/skill-tree/manifest.json`
- Same manifest.json schema, scripts use `--skills-dir ~/.openclaw/skills`
- `/fetch` parallel to ClawHub (both coexist)
- `open-prose` plugin pattern — no TypeScript logic

## Implementation

### Phase 1: Plugin Package

- [x] Create `openclaw/` directory at repo root (the plugin package)
- [x] `openclaw/openclaw.plugin.json` — manifest with `id: "skill-tree"`, `skills: ["./skills"]`, empty configSchema
- [x] `openclaw/package.json` — `name: "skill-tree"`, `type: "module"`, `openclaw.extensions: ["./index.ts"]`
- [x] `openclaw/index.ts` — empty `register()` function
- [x] `openclaw/skills/` — symlinks or copies of the 4 skills (check, setup, fetch, skill-analysis) with OpenClaw-specific `--skills-dir ~/.openclaw/skills` flags in script invocations

### Phase 2: OpenClaw Skills (SKILL.md files)

Each skill calls the same Python scripts but with OpenClaw paths:

- [x] `openclaw/skills/check/SKILL.md` — calls `uv run {baseDir}/../../scripts/status.py --skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills`
- [x] `openclaw/skills/setup/SKILL.md` — orchestrates init → scan → sync → status with `--skills-dir ~/.openclaw/skills --library-dir ~/.openclaw/skills`
- [x] `openclaw/skills/fetch/SKILL.md` — calls `uv run {baseDir}/../../scripts/add.py "<url>" --library-dir ~/.openclaw/skills`
- [x] `openclaw/skills/skill-analysis/SKILL.md` — context skill referencing OpenClaw paths, mentioning `/check`, `/setup`, `/fetch`

Note: `{baseDir}` is OpenClaw's built-in interpolation variable for the skill directory path. Scripts live at `../../scripts/` relative to `openclaw/skills/<name>/`.

### Phase 3: Script Compatibility

The scripts already accept `--skills-dir` and `--library-dir`. But for OpenClaw, both the scan path AND the library path may be the same (`~/.openclaw/skills/`). Verify:

- [x] `init.py` works when `--skills-dir` and `--library-dir` point to the same directory
- [x] `scan.py` works with same-directory setup (scans all skills, clusters are written alongside leaves)
- [x] `sync.py` correctly sets `disable-model-invocation` on leaves in the same directory as routers
- [x] `status.py` / `check.py` handle same-directory validation (orphaned-disabled check, etc.)
- [x] Add tests for same-directory scenarios

### Phase 4: Metadata + Gating

- [x] Add OpenClaw metadata to skills: `metadata: { "openclaw": { "emoji": "🌳", "requires": { "bins": ["uv"] } } }`
- [x] Gate on `uv` being available on PATH

### Phase 5: Tests

- [x] `tests/test_openclaw_plugin.py` — structural validation (mirrors `test_gemini_extension.py`):
  - `openclaw.plugin.json` exists, has required fields
  - `package.json` has `openclaw.extensions`
  - Each skill has a `SKILL.md`
  - Skills reference `--skills-dir ~/.openclaw/skills`
- [x] Same-directory scenario tests in `test_sync.py` and `test_status.py`

### Phase 6: README + Docs

- [x] Add OpenClaw install section to README:
  ```
  openclaw plugins install ./openclaw
  ```
- [x] Or if published to npm: `openclaw plugins install @danielbrodie/skill-tree`

## Acceptance Criteria

- [x] `openclaw plugins install ./openclaw` succeeds from repo root
- [x] `/check` shows token savings in an OpenClaw session
- [x] `/setup` clusters skills from `~/.openclaw/skills/` and writes routers there
- [x] `/fetch` downloads a GitHub skill into `~/.openclaw/skills/` with sandbox
- [x] All existing Claude Code and Gemini tests still pass
- [x] New OpenClaw structural tests pass

## Sources

- **Origin brainstorm:** [docs/brainstorms/2026-03-23-openclaw-integration-brainstorm.md](docs/brainstorms/2026-03-23-openclaw-integration-brainstorm.md)
- OpenClaw plugin docs: `/opt/homebrew/lib/node_modules/openclaw/docs/tools/plugin.md`
- OpenClaw skills docs: `/opt/homebrew/lib/node_modules/openclaw/docs/tools/skills.md`
- Reference plugin: `/opt/homebrew/lib/node_modules/openclaw/extensions/open-prose/`
- Gemini extension precedent: `gemini-extension.json`, `commands/*.toml`, `GEMINI.md`
