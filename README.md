# Agent Memory Kit

A file-based memory system for solo developers who switch between AI coding agents. Works across any repository. Supports Claude Code, Hermes, OpenClaw, Codex, Cursor, Gemini CLI, Windsurf, and Antigravity.

---

## What problem this solves

You work on multiple repos. You use multiple agents (Claude Code for deep work, Hermes for quick questions, OpenClaw for Telegram, etc.). Each session, you re-explain the same context. Token costs climb. Context drifts. Decisions get re-made.

This kit gives you:
- **One file structure** that lives in every repo (`memory/semantic.md`, `memory/working.example.md`, `DECISIONS.md`, `dev/[task]/`; `memory/working.md` is local session state)
- **One generator** that produces the right entry-point file for each agent
- **Hook-based enforcement** where supported (Claude Code), instruction-driven where not (everyone else)

---

## Architecture

### Two-layer design

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: MEMORY-KIT (generic, copyable)                    │
│                                                             │
│  - templates/preprompt.txt    (per-turn instructions)       │
│  - templates/stop.sh          (post-response reminder)      │
│  - templates/memory_protocol.md (memory system rules)       │
│  - adapters/                   (one per agent)              │
│  - generate.py                 (CLI entry point)            │
└─────────────────────────────────────────────────────────────┘
                              ↓ reads
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: PROJECT CONFIG (per repo)                         │
│                                                             │
│  - .agent/project.yaml         (name, description, arch)    │
│  - vision.md      (project-specific knowledge) │
│  - memory/semantic.md          (tracked: distilled facts)    │
│  - memory/working.example.md   (tracked: template)           │
│  - memory/working.md           (gitignored: current task)    │
│  - DECISIONS.md                (runtime: decisions log)     │
│  - dev/[task]/                 (runtime: active tasks)      │
└─────────────────────────────────────────────────────────────┘
```

**The rule:** Layer 1 never contains project-specific text. Layer 2 never contains agent-specific logic. You can copy `memory-kit/` into any repo, write a `project.yaml`, and generate configs for all your agents.

---

## Setup in a new repo

### Step 1: Copy the kit

From your source repo (e.g., applycling):

```bash
cd ~/projects/my-new-project
cp -r ~/projects/applycling/.agent/memory-kit .agent-memory-kit
# Or copy into .agent/ if you want it hidden:
cp -r ~/projects/applycling/.agent/memory-kit .agent/
```

### Step 2: Scaffold project config

Run the interactive init command — it creates `.agent/project.yaml`, seeds `memory/semantic.md`, creates `memory/working.example.md` (a tracked template), and bootstraps `memory/working.md` (local, gitignored) from it:

```bash
python .agent/memory-kit/generate.py init
```

You'll be prompted for project name, description, architecture file path, and which agents to enable. Sensible defaults are provided for everything.

If you prefer to write the YAML by hand, see `templates/ARCHITECTURE_EXAMPLE.md` for a full reference.

### Step 3: Create your architecture doc

```bash
cat > ARCHITECTURE.md << 'EOF'
# Architecture — my-new-project

## Core Systems

- **API:** FastAPI in `api/`
- **DB:** SQLAlchemy + asyncpg

## Key Conventions

- `pytest --asyncio-mode=auto`
- Never commit `.env`
EOF
```

### Step 4: Generate agent configs

```bash
python .agent/memory-kit/generate.py all
```

This generates configs for **only the agents you enabled** in `project.yaml`:

| Agent | Files created |
|---|---|
| Claude Code | `CLAUDE.md` + `.claude/settings.json` + `hooks/` |
| Hermes + Codex | `AGENTS.md` |
| OpenClaw | `.openclaw-system.md` |
| Cursor | `.cursor/rules/memory.mdc` |
| Windsurf | `.windsurfrules` |
| Gemini CLI | `GEMINI.md` + `.gemini/context.md` |
| Antigravity | `.agents/rules/` + `.agents/workflows/` |

To generate **all** agents regardless of config:

```bash
python .agent/memory-kit/generate.py all --force
```

To generate a single agent on demand:

```bash
python .agent/memory-kit/generate.py claude-code
```

### Step 5: Create runtime memory files

If you used `generate.py init`, everything is already in place. `memory/working.md` was bootstrapped from the tracked template and is gitignored automatically.

If setting up manually (without `init`):

```bash
mkdir -p memory dev
touch memory/semantic.md DECISIONS.md
# Create the tracked working memory template (working.md is bootstrapped from this)
cat > memory/working.example.md << 'EOF'
# Working Memory

## Current Focus

(none)

## In Progress

(none)

## Blocked

(none)

## Next Steps

(none)
EOF
# Add working.md to .gitignore — it's local session state
echo "memory/working.md" >> .gitignore
# Bootstrap working.md from the example
cp memory/working.example.md memory/working.md
```

---

## Daily Use by Agent

### Claude Code (HIGH confidence — hooks enforced)

**Files:** `CLAUDE.md`, `.claude/settings.json`, `hooks/preprompt.txt`, `hooks/stop.sh`

**How it works:**
- On session start, Claude Code reads `CLAUDE.md` automatically
- Before every user message, `hooks/preprompt.txt` is injected → agent reads `memory/working.md`
- After every response, `hooks/stop.sh` runs → agent inspects diff, proposes memory updates

**Your workflow:**
1. Open terminal, run `claude`
2. Agent reads `semantic.md` + `working.md` automatically
3. Work normally. After code changes, the stop hook fires
4. Agent asks about intent if unclear, then proposes `semantic.md` / `DECISIONS.md` updates
5. Approve or correct. `working.md` updates automatically

#### Memory capture levels (`memory.capture_at`)

Controls when the Claude Code stop hook fires. Set this in `.agent/project.yaml`:

```yaml
memory:
  capture_at:
    - response   # every response with tracked changes (default, current behavior)
    - commit     # when a non-merge commit is detected since last hook run
    - merge      # when a merge commit is detected since last hook run
```

| Level | Fires when | Default |
|---|---|---|
| `response` | Tracked changes relative to HEAD exist after a response | Yes |
| `commit` | A non-merge commit appears in the range since the last hook run | No |
| `merge` | A merge commit (2+ parents) appears in the range since the last hook run | Yes |

If `memory.capture_at` is missing, the adapter uses the backward-compatible default: `response` and `merge`.

How commit/merge detection works: the hook caches HEAD in `.agent/.last_checked_commit` after each run. On the next run, it scans all commits in the `PREV_HEAD..CURRENT_HEAD` range and classifies each by parent count. If `PREV_HEAD` is no longer an ancestor because of a rebase/reset, the hook inspects current HEAD instead.

GitHub merge styles:
- "Create a merge commit" → caught by `merge`
- "Squash and merge" / "Rebase and merge" → single-parent commits, caught by `commit`
- Enable both `commit` and `merge` if your repos use mixed merge styles.

`capture_at: []` is valid and generates a warning-only hook instead of silently doing nothing.

`.agent/.last_checked_commit` is runtime state and is gitignored automatically by `init` and by `generate.py claude-code`.

**Updating existing repos that already use this system:**

1. Update the vendored kit files in that repo's `.agent/memory-kit/` from this version.
2. Add your desired `memory.capture_at` to `.agent/project.yaml`, or omit it to use the default `response + merge` behavior.
3. Re-run only the generated agent config, e.g. `python .agent/memory-kit/generate.py claude-code` or `python .agent/memory-kit/generate.py all`.
4. Existing memory content is preserved. `memory/semantic.md`, `memory/working.md`, and `DECISIONS.md` are not overwritten by generation. `CLAUDE.md` is sentinel-managed: only the block between `<!-- amk:start -->` and `<!-- amk:end -->` is updated; custom content outside that block remains intact.
5. Check `git diff` before committing if you want to verify exactly what changed.

**If something breaks:**
- Hooks not firing? Check `.claude/settings.json` exists and `hooks/stop.sh` is executable (`chmod +x`)
- Agent forgetting context? Say "re-read semantic.md"
- Agent skipping hook output in long sessions? Say "check the diff and propose memory updates"

**Regenerating CLAUDE.md safely:**

`CLAUDE.md` uses a sentinel-based update system. The adapter manages only the block between `<!-- amk:start -->` and `<!-- amk:end -->`. Anything you write outside that block (above or below) is never touched on regen.

```bash
python .agent/memory-kit/generate.py claude-code
# → "CLAUDE.md (unchanged)"          if config hasn't changed
# → "CLAUDE.md (amk section updated)" + diff  if it changed
# → "CLAUDE.md (amk section appended)" if no sentinels found yet
```

The project header (title + description) is written once above the sentinel on first create and never regenerated — edit it freely.

---

### Hermes (MEDIUM confidence — best effort, no hook mechanism)

**Files:** `AGENTS.md`

**How it works:**
- Hermes reads `AGENTS.md` at project root as workspace context
- No hooks. Per-turn instructions are embedded as static text — relies on LLM instruction-following to reload context
- Hermes also has native `MEMORY.md` / `USER.md` persistence
- **Sentinel preservation:** The adapter uses `<!-- amk:start -->` / `<!-- amk:end -->` blocks. Only the managed section (memory protocol, architecture ref, conventions, memory mirroring footer) is updated on regeneration. Custom content outside those blocks — Hermes profile details, two-layer LLM notes, PM skills sections — is always preserved.

**Limitation:** Medium confidence is a platform constraint, not an implementation bug. Hermes exposes no hook extension points, so context drift in long sessions cannot be solved by better prompting — it's an architecture gap in the agent itself.

**Your workflow:**
1. Open Hermes in the repo
2. Agent reads `AGENTS.md` at session start
3. Manually prompt before each task: "Read memory/working.md before answering"
4. After significant changes, prompt: "Inspect the diff and propose memory updates"

**Synergy with Hermes native memory:**
```bash
ln -s memory/semantic.md MEMORY.md
```
This mirrors your file-based memory into Hermes's built-in persistence. `memory/semantic.md` remains the source of truth. Note: if Hermes only loads `MEMORY.md` at session start, updates made mid-session by other agents won't be visible until the next session.

---

### Codex (LOW-MEDIUM confidence — best effort, no hook mechanism)

**Files:** `AGENTS.md` (Hermes version overwrites this if you run `all`)

**How it works:**
- Same structure as Hermes but without the `agentskills.io` note
- No hooks — same platform-level limitation as Hermes
- Codex's `AGENTS.md` behaviour evolves rapidly and is less documented
- **Sentinel preservation:** Same `<!-- amk:start/end -->` pattern as Hermes. Custom content outside the managed block is preserved. Codex strips superset parts (skills note, memory mirroring) from the managed block; running Hermes restores them.

**Your workflow:**
- Same as Hermes. If Codex drifts, explicitly say: "Read memory/semantic.md and memory/working.md"

---

### Antigravity (HIGH confidence — Rules enforced, Workflows manual)

**Files:** `.agents/rules/memory-system.md`, `.agents/rules/project-context.md`, `.agents/workflows/memory-update.md`, `.agents/workflows/task-switch.md`

**How it works:**
- Antigravity reads workspace Rules from `.agents/rules/` and Workflows from `.agents/workflows/`
- Rules can be set to "Always On" in the Antigravity UI for passive context injection
- Workflows are invoked manually via `/workflow-name` (e.g., `/memory-update`)
- No automatic post-response hooks, but Workflows give you structured manual memory maintenance

**Your workflow:**
1. Generate the Antigravity configs: `python .agent/generate.py antigravity`
2. Open Antigravity's Customizations panel, set both rules to "Always On"
3. Work normally. After significant changes, invoke `/memory-update`
4. To switch tasks mid-session, invoke `/task-switch`

**Note:** Rules are limited to 12,000 characters each (verified against official docs). Activation mode (Always On / Manual / Glob) is set in the UI only — it cannot be set in the file itself. The one-time UI step is unavoidable.

---

## The Memory Files

These are the same across all agents. This is what makes the system portable.

### What each file is for (plain words)

Mental model: **vision = future + axioms; DECISIONS = immutable past; semantic = current state; working = current focus; context = current task.**

| File | What it is | When it changes | Lifespan |
|---|---|---|---|
| `vision.md` (or your `architecture.file`) | The "north star" — principles the project IS committed to, load-bearing assumptions, and capabilities planned but not yet built. **Not a current-state inventory.** | Only on PR merge, when a capability ships or an assumption is invalidated. | Permanent (with explicit supersessions). |
| `memory/semantic.md` | The "what's built today" snapshot. Distilled facts about the current system: which modules exist, where things live, how the pieces fit. | After any change that alters how the system works. Entries get rewritten/replaced. | Long-lived but mutable. |
| `memory/working.md` | The "what I'm doing right now" scratchpad. Current focus, in-progress bullets, half-decided things for *this* sprint/session. | Freely, after each response. Rewritten from scratch when focus shifts. | Ephemeral (days–weeks). |
| `DECISIONS.md` | Append-only history of *why* we chose X on date Y. Never edited; to reverse, append a new entry that supersedes the old one. | When a real architectural choice is made. | Forever (audit trail). |
| `dev/[task]/context.md` | Per-task scratchpad of *confirmed* facts/assumptions for one specific piece of work (e.g. one ticket). | Continuously while the task is active; archived when the task ends. | Lives with the task. |

Operational details (who can write, size limits):

| File | Size limit | Who writes | Approval? |
|---|---|---|---|
| `memory/semantic.md` | ≤500 lines | Agent (proposed) | **Yes** |
| `memory/working.md` | ≤300 lines | Agent (auto) | No |
| `DECISIONS.md` | No limit | Agent (proposed) | **Yes** |
| `dev/[task]/plan.md` | No limit | Agent | No |
| `dev/[task]/context.md` | No limit | Agent | No |
| `dev/[task]/tasks.md` | No limit | Agent | No |

**Approval flow:**
- `semantic.md` and `DECISIONS.md` require your approval before writing
- `working.md` updates freely
- `dev/[task]/` files update freely
- `vision.md` is merge-only (not part of normal-work approval flow)

### Avoiding overlap (promotion paths)

No two files share a responsibility on paper. Where the system can leak is in **moving facts to their long-term home** as work progresses:

- **working → semantic.** When a working.md bullet describes work that has shipped, it's now a stable fact about the system — promote it to `semantic.md` and remove it from `working.md`. The Claude Code stop-hook prompts for this on every response.
- **vision-planned → semantic.** When a planned capability ships, move it OUT of `vision.md`'s planned list and INTO `semantic.md`. Done at PR merge time.
- **context → DECISIONS.** If an architectural choice surfaces mid-task, don't let it die in `dev/[task]/context.md`. Promote it to a `DECISIONS.md` entry before archiving the task.
- **assumption invalidated.** Append a supersession entry to `DECISIONS.md` *first*, then update the assumption in `vision.md`. Order matters — otherwise you lose the audit trail.

If you ever feel two files are saying the same thing, the fix is almost always "promote to the longer-lived home and delete from the shorter-lived one," not "rewrite the contracts."

---

## Task Switching Protocol

When you change topics mid-session, the agent should ask:
> "This looks like a different task — should I archive the current state first?"

Say yes. The agent:
1. Archives `working.md` into `dev/[old-task]/context.md`
2. Creates/loads `dev/[new-task]/`
3. Rewrites `working.md` for the new focus

To resume later:
> "Resume dev/[original-task]/"

---

## Weekly Maintenance (10 minutes)

1. **Skim `semantic.md`** — anything stale? Tell the agent to propose a correction
2. **Check `DECISIONS.md`** — reversed decisions should have "Supersedes" entries
3. **Check `dev/`** — ship tasks to `dev/archive/`
4. **Check agent entry-point files** — delete dead rules (they train the agent to ignore live ones)

---

## Keeping the kit in sync across repos

Since this is a solo workflow, the simplest approach is copy-paste:

1. `applycling/.agent/memory-kit/` is your source of truth
2. When you improve an adapter, copy the improved files to other repos
3. Or use git subtree if you prefer:
   ```bash
   git subtree add --prefix .agent/memory-kit <kit-repo-url> main --squash
   ```

Do not over-engineer this. For 1–5 repos, copy-paste is faster than any automation.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Agent re-explains known context | `semantic.md` not loaded or stale | Check entry-point file references it; say "re-read semantic.md" |
| Answers feel off mid-session | Context drift | Say "re-read semantic.md and try again" |
| `semantic.md` > 500 lines | Bloat | "Compact semantic.md — keep only high-signal entries, propose for approval" |
| Agent stops proposing updates | Context pressure suppressing hook | "Inspect diff since last memory check and propose updates" |
| Agent asks same question across sessions | Assumptions not logged | Check `dev/[task]/context.md` Assumptions section |
| Claude Code hooks not firing | `settings.json` missing or `stop.sh` not executable | `chmod +x hooks/stop.sh`; verify `.claude/settings.json` |
| Stop hook: `No such file or directory` | Hook paths are stale (absolute or relative) | Re-run `generate.py claude-code` — hook commands now use `$CLAUDE_PROJECT_DIR` which Claude Code resolves correctly regardless of cwd |
| `CLAUDE.md` or `AGENTS.md` regen clobbered my content | File had no sentinel block | Content outside `<!-- amk:start/end -->` is always preserved. If your custom content was between the sentinels (inside the managed block), move it outside. If the file had no sentinels at all, the first regeneration appends the managed block — move your custom content below `<!-- amk:end -->` after that. |
| Generated files missing architecture section | `vision.md` (or configured arch file) not found | Create it, or the adapter falls back to `.agent/templates/architecture.md` |

---

## File Reference

```
.agent/
  project.yaml              # Your project config (name, description, conventions)
  generate.py               # Thin wrapper — loads config, calls memory-kit
  adapters/                 # Thin wrappers — load config, call memory-kit adapters
  memory-kit/               # THE REUSABLE CORE
    README.md               # This file
    generate.py             # Standalone generator for any repo
    templates/
      preprompt.txt         # Per-turn instructions (generic)
      stop.sh               # Post-response diff reminder (generic)
      memory_protocol.md    # Memory system rules (generic)
    adapters/
      claude_code.py        # Parameterized Claude Code adapter
      hermes.py             # Parameterized Hermes adapter
      openclaw.py           # Parameterized OpenClaw adapter
      codex.py              # Parameterized Codex adapter
      cursor.py             # Parameterized Cursor adapter
      windsurf.py           # Parameterized Windsurf adapter
      gemini_cli.py         # Parameterized Gemini CLI adapter
      antigravity.py        # Parameterized Antigravity adapter

memory/
  semantic.md               # Distilled knowledge (≤500 lines)
  working.example.md         # Tracked template — commit this
  working.md                 # Current task (≤300 lines) — gitignored, local only
DECISIONS.md                # Append-only decisions log
dev/                        # Active task folders
```
