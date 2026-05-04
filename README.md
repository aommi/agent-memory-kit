     1|# Agent Memory Kit
     2|
     3|A file-based memory system for solo developers who switch between AI coding agents. Works across any repository. Supports Claude Code, Hermes, OpenClaw, Codex, Cursor, Gemini CLI, Windsurf, and Antigravity.
     4|
     5|---
     6|
     7|## What problem this solves
     8|
     9|You work on multiple repos. You use multiple agents (Claude Code for deep work, Hermes for quick questions, OpenClaw for Telegram, etc.). Each session, you re-explain the same context. Token costs climb. Context drifts. Decisions get re-made.
    10|
    11|This kit gives you:
    12|- **One file structure** that lives in every repo (`memory/semantic.md`, `memory/working.example.md`, `DECISIONS.md`, `dev/[task]/`; `memory/working.md` is local session state)
    13|- **One generator** that produces the right entry-point file for each agent
    14|- **Hook-based enforcement** where supported (Claude Code), instruction-driven where not (everyone else)
    15|
    16|---
    17|
    18|## Architecture
    19|
    20|### Two-layer design
    21|
    22|```
    23|┌─────────────────────────────────────────────────────────────┐
    24|│  LAYER 1: MEMORY-KIT (generic, copyable)                    │
    25|│                                                             │
    26|│  - templates/preprompt.txt    (per-turn instructions)       │
    27|│  - templates/stop.sh          (post-response reminder)      │
    28|│  - templates/memory_protocol.md (memory system rules)       │
    29|│  - adapters/                   (one per agent)              │
    30|│  - generate.py                 (CLI entry point)            │
    31|└─────────────────────────────────────────────────────────────┘
    32|                              ↓ reads
    33|┌─────────────────────────────────────────────────────────────┐
    34|│  LAYER 2: PROJECT CONFIG (per repo)                         │
    35|│                                                             │
    36|│  - .agent/project.yaml         (name, description, arch)    │
    37|│  - vision.md      (project-specific knowledge) │
    38|│  - memory/semantic.md          (tracked: distilled facts)    │
    39|│  - memory/working.example.md   (tracked: template)           │
    40|│  - memory/working.md           (gitignored: current task)    │
    41|│  - DECISIONS.md                (runtime: decisions log)     │
    42|│  - dev/[task]/                 (runtime: active tasks)      │
    43|└─────────────────────────────────────────────────────────────┘
    44|```
    45|
    46|**The rule:** Layer 1 never contains project-specific text. Layer 2 never contains agent-specific logic. You can copy `memory-kit/` into any repo, write a `project.yaml`, and generate configs for all your agents.
    47|
    48|---
    49|
    50|## Setup in a new repo
    51|
    52|### Step 1: Copy the kit
    53|
    54|From your source repo (e.g., applycling):
    55|
    56|```bash
    57|cd ~/projects/my-new-project
    58|cp -r ~/projects/applycling/.agent/memory-kit .agent-memory-kit
    59|# Or copy into .agent/ if you want it hidden:
    60|cp -r ~/projects/applycling/.agent/memory-kit .agent/
    61|```
    62|
    63|### Step 2: Scaffold project config
    64|
    65|Run the interactive init command — it creates `.agent/project.yaml`, seeds `memory/semantic.md`, creates `memory/working.example.md` (a tracked template), and bootstraps `memory/working.md` (local, gitignored) from it:
    66|
    67|```bash
    68|python .agent/memory-kit/generate.py init
    69|```
    70|
    71|You'll be prompted for project name, description, architecture file path, and which agents to enable. Sensible defaults are provided for everything.
    72|
    73|If you prefer to write the YAML by hand, see `templates/ARCHITECTURE_EXAMPLE.md` for a full reference.
    74|
    75|### Step 3: Create your architecture doc
    76|
    77|```bash
    78|cat > ARCHITECTURE.md << 'EOF'
    79|# Architecture — my-new-project
    80|
    81|## Core Systems
    82|
    83|- **API:** FastAPI in `api/`
    84|- **DB:** SQLAlchemy + asyncpg
    85|
    86|## Key Conventions
    87|
    88|- `pytest --asyncio-mode=auto`
    89|- Never commit `.env`
    90|EOF
    91|```
    92|
    93|### Step 4: Generate agent configs
    94|
    95|```bash
    96|python .agent/memory-kit/generate.py all
    97|```
    98|
    99|This generates configs for **only the agents you enabled** in `project.yaml`:
   100|
   101|| Agent | Files created |
   102||---|---|
   103|| Claude Code | `CLAUDE.md` + `.claude/settings.json` + `hooks/` |
   104|| Hermes + Codex | `AGENTS.md` |
   105|| OpenClaw | `.openclaw-system.md` |
   106|| Cursor | `.cursor/rules/memory.mdc` |
   107|| Windsurf | `.windsurfrules` |
   108|| Gemini CLI | `GEMINI.md` + `.gemini/context.md` |
   109|| Antigravity | `.agents/rules/` + `.agents/workflows/` |
   110|
   111|To generate **all** agents regardless of config:
   112|
   113|```bash
   114|python .agent/memory-kit/generate.py all --force
   115|```
   116|
   117|To generate a single agent on demand:
   118|
   119|```bash
   120|python .agent/memory-kit/generate.py claude-code
   121|```
   122|
   123|### Step 5: Create runtime memory files
   124|
   125|If you used `generate.py init`, everything is already in place. `memory/working.md` was bootstrapped from the tracked template and is gitignored automatically.
   126|
   127|If setting up manually (without `init`):
   128|
   129|```bash
   130|mkdir -p memory dev
   131|touch memory/semantic.md DECISIONS.md
   132|# Create the tracked working memory template (working.md is bootstrapped from this)
   133|cat > memory/working.example.md << 'EOF'
   134|# Working Memory
   135|
   136|## Current Focus
   137|
   138|(none)
   139|
   140|## In Progress
   141|
   142|(none)
   143|
   144|## Blocked
   145|
   146|(none)
   147|
   148|## Next Steps
   149|
   150|(none)
   151|EOF
   152|# Add working.md to .gitignore — it's local session state
   153|echo "memory/working.md" >> .gitignore
   154|# Bootstrap working.md from the example
   155|cp memory/working.example.md memory/working.md
   156|```
   157|
   158|---
   159|
   160|## Daily Use by Agent
   161|
   162|### Claude Code (HIGH confidence — hooks enforced)
   163|
   164|**Files:** `CLAUDE.md`, `.claude/settings.json`, `hooks/preprompt.txt`, `hooks/stop.sh`
   165|
   166|**How it works:**
   167|- On session start, Claude Code reads `CLAUDE.md` automatically
   168|- Before every user message, `hooks/preprompt.txt` is injected → agent reads `memory/working.md`
   169|- After every response, `hooks/stop.sh` runs → agent inspects diff and applies memory updates per the project's approval_mode (auto = write directly, review = propose first)
   170|
   171|**Your workflow:**
   172|1. Open terminal, run `claude`
   173|2. Agent reads `semantic.md` + `working.md` automatically
   174|3. Work normally. After code changes, the stop hook fires
   175|4. Agent asks about intent if unclear, then updates `semantic.md` / `DECISIONS.md` per approval_mode
   176|5. Approve or correct. `working.md` updates automatically
   177|
   178|#### Memory capture levels (`memory.capture_at`)
   179|
   180|Controls when the Claude Code stop hook fires. Set this in `.agent/project.yaml`:
   181|
   182|```yaml
   183|memory:
   184|  capture_at:
   185|    - response   # every response with tracked changes (default, current behavior)
   186|    - commit     # when a non-merge commit is detected since last hook run
   187|    - merge      # when a merge commit is detected since last hook run
   188|```
   189|
   190|| Level | Fires when | Default |
   191||---|---|---|
   192|| `response` | Tracked changes relative to HEAD exist after a response | Yes |
   193|| `commit` | A non-merge commit appears in the range since the last hook run | No |
   194|| `merge` | A merge commit (2+ parents) appears in the range since the last hook run | Yes |
   195|
   196|If `memory.capture_at` is missing, the adapter uses the backward-compatible default: `response` and `merge`.
   197|
   198|How commit/merge detection works: the hook caches HEAD in `.agent/.last_checked_commit` after each run. On the next run, it scans all commits in the `PREV_HEAD..CURRENT_HEAD` range and classifies each by parent count. If `PREV_HEAD` is no longer an ancestor because of a rebase/reset, the hook inspects current HEAD instead.
   199|
   200|GitHub merge styles:
   201|- "Create a merge commit" → caught by `merge`
   202|- "Squash and merge" / "Rebase and merge" → single-parent commits, caught by `commit`
   203|- Enable both `commit` and `merge` if your repos use mixed merge styles.
   204|
   205|`capture_at: []` is valid and generates a warning-only hook instead of silently doing nothing.
   206|
   207|`.agent/.last_checked_commit` is runtime state and is gitignored automatically by `init` and by `generate.py claude-code`.
   208|
   209|**Updating existing repos that already use this system:**
   210|
   211|1. Update the vendored kit files in that repo's `.agent/memory-kit/` from this version.
   212|2. Add your desired `memory.capture_at` to `.agent/project.yaml`, or omit it to use the default `response + merge` behavior.
   213|3. Re-run only the generated agent config, e.g. `python .agent/memory-kit/generate.py claude-code` or `python .agent/memory-kit/generate.py all`.
   214|4. Existing memory content is preserved. `memory/semantic.md`, `memory/working.md`, and `DECISIONS.md` are not overwritten by generation. `CLAUDE.md` is sentinel-managed: only the block between `<!-- amk:start -->` and `<!-- amk:end -->` is updated; custom content outside that block remains intact.
   215|5. Check `git diff` before committing if you want to verify exactly what changed.
   216|
   217|**If something breaks:**
   218|- Hooks not firing? Check `.claude/settings.json` exists and `hooks/stop.sh` is executable (`chmod +x`)
   219|- Agent forgetting context? Say "re-read semantic.md"
   220|- Agent skipping hook output in long sessions? Say "check the diff and update memory"
   221|
   222|**Regenerating CLAUDE.md safely:**
   223|
   224|`CLAUDE.md` uses a sentinel-based update system. The adapter manages only the block between `<!-- amk:start -->` and `<!-- amk:end -->`. Anything you write outside that block (above or below) is never touched on regen.
   225|
   226|```bash
   227|python .agent/memory-kit/generate.py claude-code
   228|# → "CLAUDE.md (unchanged)"          if config hasn't changed
   229|# → "CLAUDE.md (amk section updated)" + diff  if it changed
   230|# → "CLAUDE.md (amk section appended)" if no sentinels found yet
   231|```
   232|
   233|The project header (title + description) is written once above the sentinel on first create and never regenerated — edit it freely.
   234|
   235|---
   236|
   237|### Hermes (MEDIUM confidence — best effort, no hook mechanism)
   238|
   239|**Files:** `AGENTS.md`
   240|
   241|**How it works:**
   242|- Hermes reads `AGENTS.md` at project root as workspace context
   243|- No hooks. Per-turn instructions are embedded as static text — relies on LLM instruction-following to reload context
   244|- Hermes also has native `MEMORY.md` / `USER.md` persistence
   245|- **Sentinel preservation:** The adapter uses `<!-- amk:start -->` / `<!-- amk:end -->` blocks. Only the managed section (memory protocol, architecture ref, conventions, memory mirroring footer) is updated on regeneration. Custom content outside those blocks — Hermes profile details, two-layer LLM notes, PM skills sections — is always preserved.
   246|
   247|**Limitation:** Medium confidence is a platform constraint, not an implementation bug. Hermes exposes no hook extension points, so context drift in long sessions cannot be solved by better prompting — it's an architecture gap in the agent itself.
   248|
   249|**Your workflow:**
   250|1. Open Hermes in the repo
   251|2. Agent reads `AGENTS.md` at session start
   252|3. Manually prompt before each task: "Read memory/working.md before answering"
   253|4. After significant changes, prompt: "Inspect the diff and update memory per approval_mode"
   254|
   255|**Synergy with Hermes native memory:**
   256|```bash
   257|ln -s memory/semantic.md MEMORY.md
   258|```
   259|This mirrors your file-based memory into Hermes's built-in persistence. `memory/semantic.md` remains the source of truth. Note: if Hermes only loads `MEMORY.md` at session start, updates made mid-session by other agents won't be visible until the next session.
   260|
   261|---
   262|
   263|### Codex (LOW-MEDIUM confidence — best effort, no hook mechanism)
   264|
   265|**Files:** `AGENTS.md` (Hermes version overwrites this if you run `all`)
   266|
   267|**How it works:**
   268|- Same structure as Hermes but without the `agentskills.io` note
   269|- No hooks — same platform-level limitation as Hermes
   270|- Codex's `AGENTS.md` behaviour evolves rapidly and is less documented
   271|- **Sentinel preservation:** Same `<!-- amk:start/end -->` pattern as Hermes. Custom content outside the managed block is preserved. Codex strips superset parts (skills note, memory mirroring) from the managed block; running Hermes restores them.
   272|
   273|**Your workflow:**
   274|- Same as Hermes. If Codex drifts, explicitly say: "Read memory/semantic.md and memory/working.md"
   275|
   276|---
   277|
   278|### Antigravity (HIGH confidence — Rules enforced, Workflows manual)
   279|
   280|**Files:** `.agents/rules/memory-system.md`, `.agents/rules/project-context.md`, `.agents/workflows/memory-update.md`, `.agents/workflows/task-switch.md`
   281|
   282|**How it works:**
   283|- Antigravity reads workspace Rules from `.agents/rules/` and Workflows from `.agents/workflows/`
   284|- Rules can be set to "Always On" in the Antigravity UI for passive context injection
   285|- Workflows are invoked manually via `/workflow-name` (e.g., `/memory-update`)
   286|- No automatic post-response hooks, but Workflows give you structured manual memory maintenance
   287|
   288|**Your workflow:**
   289|1. Generate the Antigravity configs: `python .agent/generate.py antigravity`
   290|2. Open Antigravity's Customizations panel, set both rules to "Always On"
   291|3. Work normally. After significant changes, invoke `/memory-update`
   292|4. To switch tasks mid-session, invoke `/task-switch`
   293|
   294|**Note:** Rules are limited to 12,000 characters each (verified against official docs). Activation mode (Always On / Manual / Glob) is set in the UI only — it cannot be set in the file itself. The one-time UI step is unavoidable.
   295|
   296|---
   297|
   298|## The Memory Files
   299|
   300|These are the same across all agents. This is what makes the system portable.
   301|
   302|| File | Purpose | Size limit | Who writes | Approval mode |
   303||---|---|---|---|---|
   304|| `memory/semantic.md` | Distilled project knowledge | ≤500 lines | Agent | Configurable (default: review) |
   305|| `memory/working.md` | Live task state | ≤300 lines | Agent | auto |
   306|| `DECISIONS.md` | Append-only decisions log | No limit | Agent | Configurable (default: review) |
| `dev/[task]/plan.md` | Task goal and approach | No limit | Agent | auto |
| `dev/[task]/context.md` | Constraints, assumptions | No limit | Agent | auto |
| `dev/[task]/tasks.md` | Progress checklist | No limit | Agent | auto |
   310|
**Approval mode (configurable):** `memory.approval_mode` in `project.yaml` controls whether files are written directly (`auto`) or proposed for human approval (`review`). Default for new projects is `auto` for all files. Projects without `approval_mode` set fall back to `review` for `semantic.md` / `DECISIONS.md` (preserves pre-v3 behavior). See [Configuration](#configuration) for the schema.
   315|
   316|---
   317|
   318|## Task Switching Protocol
   319|
   320|When you change topics mid-session, the agent should ask:
   321|> "This looks like a different task — should I archive the current state first?"
   322|
   323|Say yes. The agent:
   324|1. Archives `working.md` into `dev/[old-task]/context.md`
   325|2. Creates/loads `dev/[new-task]/`
   326|3. Rewrites `working.md` for the new focus
   327|
   328|To resume later:
   329|> "Resume dev/[original-task]/"
   330|
   331|---
   332|
   333|## Weekly Maintenance (10 minutes)
   334|
   335|1. **Skim `semantic.md`** — anything stale? Tell the agent to correct it (or propose a correction if semantic.md is in review mode)
   336|2. **Check `DECISIONS.md`** — reversed decisions should have "Supersedes" entries
   337|3. **Check `dev/`** — ship tasks to `dev/archive/`
   338|4. **Check agent entry-point files** — delete dead rules (they train the agent to ignore live ones)
   339|
   340|---
   341|
   342|## Keeping the kit in sync across repos
   343|
   344|Since this is a solo workflow, the simplest approach is copy-paste:
   345|
   346|1. `applycling/.agent/memory-kit/` is your source of truth
   347|2. When you improve an adapter, copy the improved files to other repos
   348|3. Or use git subtree if you prefer:
   349|   ```bash
   350|   git subtree add --prefix .agent/memory-kit <kit-repo-url> main --squash
   351|   ```
   352|
   353|Do not over-engineer this. For 1–5 repos, copy-paste is faster than any automation.
   354|
   355|---
   356|
   357|## Troubleshooting
   358|
   359|| Symptom | Cause | Fix |
   360||---|---|---|
   361|| Agent re-explains known context | `semantic.md` not loaded or stale | Check entry-point file references it; say "re-read semantic.md" |
   362|| Answers feel off mid-session | Context drift | Say "re-read semantic.md and try again" |
   363|| `semantic.md` > 500 lines | Bloat | "Compact semantic.md — keep only high-signal entries" |
   364|| Agent stops updating memory | Context pressure suppressing hook | "Inspect diff since last memory check and update memory" |
   365|| Agent asks same question across sessions | Assumptions not logged | Check `dev/[task]/context.md` Assumptions section |
   366|| Claude Code hooks not firing | `settings.json` missing or `stop.sh` not executable | `chmod +x hooks/stop.sh`; verify `.claude/settings.json` |
   367|| Stop hook: `No such file or directory` | Hook paths are stale (absolute or relative) | Re-run `generate.py claude-code` — hook commands now use `$CLAUDE_PROJECT_DIR` which Claude Code resolves correctly regardless of cwd |
   368|| `CLAUDE.md` or `AGENTS.md` regen clobbered my content | File had no sentinel block | Content outside `<!-- amk:start/end -->` is always preserved. If your custom content was between the sentinels (inside the managed block), move it outside. If the file had no sentinels at all, the first regeneration appends the managed block — move your custom content below `<!-- amk:end -->` after that. |
   369|| Generated files missing architecture section | `vision.md` (or configured arch file) not found | Create it, or the adapter falls back to `.agent/templates/architecture.md` |
   370|
   371|---
   372|
   373|## File Reference
   374|
   375|```
   376|.agent/
   377|  project.yaml              # Your project config (name, description, conventions)
   378|  generate.py               # Thin wrapper — loads config, calls memory-kit
   379|  adapters/                 # Thin wrappers — load config, call memory-kit adapters
   380|  memory-kit/               # THE REUSABLE CORE
   381|    README.md               # This file
   382|    generate.py             # Standalone generator for any repo
   383|    templates/
   384|      preprompt.txt         # Per-turn instructions (generic)
   385|      stop.sh               # Post-response diff reminder (generic)
   386|      memory_protocol.md    # Memory system rules (generic)
   387|    adapters/
   388|      claude_code.py        # Parameterized Claude Code adapter
   389|      hermes.py             # Parameterized Hermes adapter
   390|      openclaw.py           # Parameterized OpenClaw adapter
   391|      codex.py              # Parameterized Codex adapter
   392|      cursor.py             # Parameterized Cursor adapter
   393|      windsurf.py           # Parameterized Windsurf adapter
   394|      gemini_cli.py         # Parameterized Gemini CLI adapter
   395|      antigravity.py        # Parameterized Antigravity adapter
   396|
   397|memory/
   398|  semantic.md               # Distilled knowledge (≤500 lines)
   399|  working.example.md         # Tracked template — commit this
   400|  working.md                 # Current task (≤300 lines) — gitignored, local only
   401|DECISIONS.md                # Append-only decisions log
   402|dev/                        # Active task folders
   403|```
   404|