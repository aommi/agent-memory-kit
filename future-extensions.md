# Future Extensions — Known Options

Decisions we made deliberately to keep the system minimal. Each item below is a real upgrade path for a specific pain point. Don't implement preemptively — wait until you actually hit the problem.

---

## 1. Agent agnosticism — switching tools without losing memory

**The problem it solves:** Right now the system is Claude Code-native (`CLAUDE.md`, `.claude/settings.json` hooks). If you switch to Codex, Cursor, Gemini CLI, or another agent, the memory files are portable but the entry-point file and hook registration need to change per tool.

**The solution:** agentic-stack's adapter pattern — a portable `.agent/` folder with thin per-tool adapters that generate the right entry-point file and hook config for each harness.

- Claude Code → `CLAUDE.md` + `.claude/settings.json` hooks
- Codex → `AGENTS.md` + limited hook support
- Cursor → `.cursor/rules/*.mdc` + native auto-attach rules
- Gemini CLI → `GEMINI.md` + sub-directory files
- Windsurf → `.windsurfrules`

**Reference:** https://github.com/codejunkie99/agentic-stack

**When to implement:** When you find yourself switching agents regularly and manually re-configuring each time.

---

## 2. Team projects — PR-based memory updates

**The problem it solves:** On a solo project, stop-hook-on-every-response is the right cadence. On a team project, multiple people committing means the agent's memory updates could conflict or lag behind. Tying memory compression to PR merge ensures updates happen at a stable, agreed-upon checkpoint.

**The solution:** Replace the stop hook with a PR merge hook (GitHub Actions or a git post-merge hook). On merge: the agent inspects the diff, proposes semantic.md and DECISIONS.md updates, a human approves, then it commits to `main`.

**Trade-off:** Memory lags behind reality by hours or days (the PR cycle). Acceptable for teams; too slow for solo work.

**When to implement:** When the project grows to multi-contributor and concurrent memory writes become a problem.

---

## 3. Slash commands — named workflow shortcuts

**The problem it solves:** The manual workflows (start task, switch task, end session) require typing multi-sentence prompts. Once you've used the system for a few weeks and know exactly which transitions feel heavy, you can encode them as slash commands.

**The solution:** Three Claude Code slash commands stored in `.claude/commands/`:

- `/start [task-name]` — creates dev/[task]/ folder, updates working.md, runs plan mode
- `/switch [new-task]` — archives current working.md, loads new task
- `/end` — proposes final memory updates, archives completed task, cleans working.md

**When to implement:** After 2–4 weeks of real use. You'll know which transitions feel heavy. Don't guess upfront.

**Reference:** Diet-Coder's slash command pattern — https://dev.to/diet-code103/claude-code-is-a-beast-tips-from-6-months-of-hardcore-use-572n

---

## 4. Memory confidence filter — reducing long-term noise

**The problem it solves:** Over months, the propose-then-approve gate still accumulates entries that seemed important at the time but turn out not to be. semantic.md slowly fills with low-value entries even with the 500-token cap forcing compression.

**The solution:** Add a confidence rule to the stop hook: "Only propose updates to semantic.md if you are confident the insight will remain relevant across future sessions — not just this week." This reduces proposal frequency and improves long-term signal quality.

**When to implement:** When you notice you're approving proposals that feel marginal, or when semantic.md compaction starts losing things that mattered. Real signal, not theoretical.

---

## 5. Four-layer memory — episodic and personal layers

**The problem it solves:** The current system has two memory layers (semantic = distilled knowledge, working = current state). As projects grow longer, two gaps emerge: (1) no record of *what happened* over time (episodic — useful for retrospectives and debugging recurring issues), (2) no record of your personal conventions and preferences that apply across all projects (personal — not project-specific).

**The solution:** agentic-stack's four-layer model:

- `working/` — live task state (our working.md)
- `episodic/` — what happened, timestamped event log
- `semantic/` — distilled lessons (our semantic.md)
- `personal/` — your conventions, preferences, patterns across all projects

**When to implement:** When you find yourself re-establishing the same personal preferences in every new project, or when you want a retrospective log of how a long project evolved.

**Reference:** https://github.com/codejunkie99/agentic-stack/blob/master/README.md

---

## 6. Nightly compression with human review — auto_dream pattern

**The problem it solves:** The current stop hook proposes updates synchronously after each response, which requires your attention during work. On heavy coding days you may defer or skip approvals, letting the queue build up.

**The solution:** A nightly scheduled job (cron) that batches the day's candidate memory updates, presents them for review the next morning, and writes only the approved ones. agentic-stack calls this `auto_dream.py`. You review over coffee, not mid-flow.

**Trade-off:** Memory lags by up to 24 hours. For solo projects this is usually fine. For fast-moving work, the synchronous approach is better.

**When to implement:** When you find mid-session approval prompts breaking your flow consistently.

**Reference:** https://github.com/codejunkie99/agentic-stack/releases

---

## 7. Skills system — pattern enforcement across sessions

**The problem it solves:** As the project grows, coding patterns (React component conventions, backend service structure, error handling) drift because the agent reverts to its defaults between sessions. semantic.md mentions patterns but doesn't enforce them at the prompt level.

**The solution:** A Skills directory (`.claude/skills/` or `.agent/skills/`) where each skill is a focused guideline file. A UserPromptSubmit hook detects which skill is relevant to the current prompt (based on keywords or file paths) and injects it before the agent reads your message.

**When to implement:** When you find yourself correcting the same pattern drift repeatedly across sessions — not before. The skill you need to write will be obvious from the correction you keep making.

**Reference:** Diet-Coder's skills system — https://dev.to/diet-code103/claude-code-is-a-beast-tips-from-6-months-of-hardcore-use-572n

---

## 8. Vector DB / RAG — semantic search over project history

**The problem it solves:** semantic.md is capped at 500 tokens. On very large or very long-running projects, that's not enough to hold everything worth knowing. You start losing older but still-relevant knowledge on every compaction.

**The solution:** Replace or supplement semantic.md with a local vector database (Chroma, LanceDB, or SQLite with FTS5). The agent queries it semantically rather than reading a flat file. Relevant knowledge is retrieved by similarity, not loaded wholesale.

**Trade-off:** Significant setup complexity. Requires embedding infrastructure. Almost certainly overkill for anything under 12 months of active development.

**When to implement:** When semantic.md compactions start consistently losing things you needed later. This is a late-stage problem.

---

## 9. Multi-model review — second model as quality gate

**The problem it solves:** The main agent both writes code and proposes memory updates. A second model with fresh context can catch things the primary agent missed or compressed incorrectly — especially useful for architectural decisions.

**The solution:** At defined checkpoints (end of task, before archiving, weekly maintenance), paste the proposed semantic.md update or DECISIONS.md entry into a second model and ask: "Does this contradict anything in the existing entries? Is anything missing?" Manual, on-demand — not automated.

**When to implement:** For high-stakes architectural decisions. Not for routine memory updates. The cost is negligible (a paste and a read) but the value is specific to complex decisions.

---

## 10. OpenClaw / Hermes integration — ambient access

**The problem it solves:** The current system requires you to be at your terminal and in Claude Code. When you're away from your desk, the agent is unreachable. Working memory and session state sit idle.

**The solution:** Run Hermes or OpenClaw as a persistent server alongside the project. They can read the same `memory/` and `dev/` files. Ask about project state from Telegram or WhatsApp. Hermes can also run scheduled checks (CI status, open PRs) and push briefings to you.

**Trade-off:** Adds server infrastructure (Mac Mini, Railway, fly.io). The memory files are the integration point — no format changes needed.

**When to implement:** When you find yourself wanting project context while away from the desk, or when you want automated monitoring of CI/PR status.

**References:**
- https://hermes-agent.nousresearch.com
- https://github.com/openclaw/openclaw
