---
description: Quick health check on skill-tree's manifest — finds dead references, leaf-not-in-cluster orphans, broken routing tables. Reports validation errors and (if cluster routing is set up) the token savings vs flat-catalog mode. USE WHEN the user says "check my skills", "is anything broken", or sees skill-related errors in a session.
---

Run the status check:

```bash
${CLAUDE_PLUGIN_ROOT}/bin/skill-tree status
```

Present the output. Highlight:
- Validation errors (suggest `/skill-tree:setup` if the manifest needs rebuilding)
- Token savings (only meaningful if the user has cluster routing set up via `/skill-tree:setup`)
- Cluster overview (only relevant in cluster mode)
