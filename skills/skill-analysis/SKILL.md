---
name: skill-analysis
description: Reference for what skill-tree's other skills do and how to compose them. Loads when the user asks "how do I use skill-tree", "which skill-tree command does X", or wants help orienting around the management/diagnosis surface. NOT a discovery tool for finding new skills to install.
---

# What skill-tree's skills do

skill-tree exists to manage skills you already have installed across Claude Code, Codex CLI, and Gemini CLI — not to recommend new ones to install. For new-skill discovery, see [`anthropics/claude-plugins-official/claude-code-setup`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup) or [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills).

## When to suggest each skill

| User says... | Use |
|---|---|
| "my prelude is too noisy" / "I want a smaller skill set for this project" | `/skill-tree:provision` |
| "what's broken with my skills" / "clean up my skill installs" / "I'm confused where skills live" | `/skill-tree:audit` |
| A specific symptom: "my skill X isn't appearing" / "I get 'skill not found' for Y" / "I shipped a new version but my agents don't see it" | `/skill-tree:diagnose` |
| "my project skills are out of date" / "the upstream library changed" | `/skill-tree:sync` |
| Hands you a GitHub URL to a SKILL.md and wants it added safely | `/skill-tree:fetch` |
| "is the manifest OK" / "are there any orphans" | `/skill-tree:check` |
| "I have ~150+ skills and the prelude is overflowing" — wants cluster routing set up | `/skill-tree:setup` (optional; most users won't need this) |

## What's in the docs

- `docs/ecosystem-map.md` — how skills work across Claude Code, Codex CLI, and Gemini CLI. Load paths per platform, frontmatter that controls progressive disclosure, plugin cache lifecycle, recognized failure modes. Every claim cites the corresponding platform's official documentation.
- `docs/registry-map.md` — where skills end up on disk per installer on macOS, and the safe-removal command per installer.
- `docs/measurement.md` — the Reach@catalog metric the provisioner is measured against.

The audit and diagnose skills read these docs at runtime, so the docs are part of the tool.
