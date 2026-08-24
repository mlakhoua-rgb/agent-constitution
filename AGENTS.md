# Agent entry point

Before any work, read and follow [`CLAUDE.md`](CLAUDE.md), the canonical constitution shared by all
agents. For a service task, also read its applicable `services/<service>/CLAUDE.md` before editing.

---

**Why this file is three lines.** Different agent tools look for different filenames
(`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursorrules`). The
temptation is to write real content into each one. Don't — the moment there are two copies, they
drift, and an agent will confidently cite the stale one.

Pick **one** canonical file and make every other entry point a pointer to it. Adding a new agent
vendor should cost you three lines, not a fork of your governance.
