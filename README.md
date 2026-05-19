<p align="center">
  <img src="assets/header-final.png" alt="skill-tree" width="100%">
</p>

# skill-tree

Manage Claude Code, Codex, and Gemini CLI skills from one place.

Skills accumulate. After ~150 of them my prelude got noisy enough that Claude Code kept offering a flight-rewards skill while I was writing iOS code. `skill-tree` scans what's installed, narrows it to a small project-specific set, and audits the install registries for the usual breakage (stale symlinks, lock-file drift, parallel registries).

Early. Mostly used by me. Tested on macOS, not Linux. Issues and PRs welcome.

## Commands

| Command | What it does |
|---|---|
| `/skill-tree:provision` | Pick a small set of skills that fit the current project. Copy them into `<project>/.claude/skills/`. |
| `/skill-tree:audit` | Walk every skill registry on this machine. Report what's broken and the fix command per installer. |
| `/skill-tree:catalog <topic>` | Look up `docs/ecosystem-map.md` for a stated need ("anything for Stripe webhooks?"). Surfaces skills already documented in the ecosystem; doesn't analyze your project. |
| `/skill-tree:diagnose <symptom>` | "My new skill isn't appearing." "I get 'skill not found' for X." Walks failure-mode signatures and points at the fix. |
| `/skill-tree:install <ref>` | Cross-installer dispatcher: `name@marketplace`, `user/repo`, GitHub URL, bare name, local path → the right install command. |
| `/skill-tree:sync` | Reconcile project skill copies after upstream library changes. |
| `/skill-tree:fetch <url>` | Download a skill from GitHub with security checks. New skills are sandboxed (`disable-model-invocation: true`) until you add them to a cluster. |
| `/skill-tree:check` | Health check on the manifest graph. |
| `/skill-tree:refresh-ecosystem-map` | Monthly survey to keep `docs/ecosystem-map.md` current. |

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

**Claude Code**
```
claude plugin marketplace add danielbrodie/skill-tree
claude plugin install skill-tree@skill-tree
```

**Gemini CLI**
```
gemini extensions install https://github.com/danielbrodie/skill-tree
```

**Codex CLI**
```
git clone https://github.com/danielbrodie/skill-tree ~/.codex/marketplaces/skill-tree
codex plugin marketplace add ~/.codex/marketplaces/skill-tree/.codex-plugin
codex plugin install skill-tree@danielbrodie
```

See `docs/codex.md` for Codex caveats (no SessionStart hook surface, `${CLAUDE_PLUGIN_ROOT}` is Claude-specific).

**OpenClaw**
```
openclaw plugins install ./openclaw
```

## Per-project manifest

`<project>/.claude/.skilltree.json` records which skills got copied in and why:

```json
{
  "version": "1.0",
  "sourceLibrary": "/Users/you/.claude/skills",
  "syncedAt": "...",
  "skills": {
    "tdd": {
      "source": "/Users/you/.claude/skills/tdd",
      "reason": "Python+pytest repo",
      "syncedAt": "..."
    }
  },
  "auditLog": [...]
}
```

Skills are copied, not symlinked, so your project edits won't fight upstream library changes. `/skill-tree:sync` reconciles drift when you want it.

## The ecosystem docs

`docs/ecosystem-map.md` lists the agent platforms, skill packagers, installers, and failure modes I've actually run into. `docs/registry-map.md` covers where skills live on disk per platform. The catalog / diagnose / install skills read these docs at runtime, so the docs are part of the tool, not just references sitting next to it.

PRs to either doc welcome. That's how the lists stay current.

## License

Apache 2.0
