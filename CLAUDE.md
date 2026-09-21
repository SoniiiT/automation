# OpenWolf

This project uses OpenWolf for context management. The always-on rules live in `.claude/rules/openwolf.md`; the hooks handle bookkeeping (anatomy index, memory log, read tracking) automatically.

For the full operating protocol (session handoff, memory discipline, bug logging), load the `openwolf` skill, or read `.wolf/OPENWOLF.md`. Regenerate the session handoff with `/handoff`.


# Claude project guidance

The canonical shared project context is `.ai-context/`. Read the relevant map, architecture, conventions, and knowledge entries before changing files. Treat generated summaries as navigation aids only: source code and explicit project rules are authoritative. Do not persist secret values.
