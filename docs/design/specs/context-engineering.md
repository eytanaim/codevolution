# Context Engineering Spec

What goes into each Claude Code invocation.
This is the highest-leverage design decision in the system.

Research consistently shows that **problem formulation and prompt context
matter more than search sophistication**. Getting this right is more
important than any other component.

## Prompt structure

Each `claude -p` invocation receives a structured prompt with these sections:

```
┌─────────────────────────────────┐
│  1. System context              │  ~10% of budget
│     (role, constraints, rules)  │
├─────────────────────────────────┤
│  2. Goal                        │  ~10% of budget
│     (what to optimize, metric)  │
├─────────────────────────────────┤
│  3. Repository context          │  ~30% of budget
│     (relevant code, structure)  │
├─────────────────────────────────┤
│  4. Feedback from prior runs    │  ~25% of budget
│     (best result, failures)     │
├─────────────────────────────────┤
│  5. Action request              │  ~5% of budget
│     (generate a patch)          │
├─────────────────────────────────┤
│  6. Output format               │  ~5% of budget
│     (how to structure response) │
└─────────────────────────────────┘
     ~15% reserved headroom
```

## Section details

### 1. System context

Sets the role and hard constraints:

```
You are optimizing code in a bounded experiment.

Rules:
- Only modify files in: {allowed_paths}
- Never modify: {forbidden_paths}
- Maximum {max_files} files, {max_loc} lines changed
- Do not disable tests or weaken assertions
- Do not add benchmark-specific conditionals
```

Delivered via `--append-system-prompt`.

### 2. Goal

Natural language description of what to optimize:

```
Goal: Improve throughput (requests per second) of the HTTP handler
in src/server/handler.py while maintaining all existing tests.

Target metric: throughput_rps (higher is better)
Baseline: 1200 rps (mean over 10 runs, stddev 45)
Current best: 1250 rps (+4.2%)
```

Keep it specific. "Make it faster" is bad. "Improve throughput_rps in handler.py" is good.

### 3. Repository context

The relevant code the LLM needs to understand the problem.
This is NOT the whole repo - it's the targeted slice.

Two approaches:
- **Claude Code's built-in repo map**: Let Claude Code discover context
  via its native codebase understanding (simpler, but less controlled)
- **Pre-selected files**: Include specific files in the prompt
  (more controlled, but requires knowing what's relevant)

v1 recommendation: Use Claude Code's native codebase understanding.
Pass the goal and let it explore. The `--allowedTools "Read,Edit,Bash,Glob,Grep"`
flags give it the tools to find relevant code.

### 4. Feedback from prior runs

The SCS conditioning signal. See [Feedback Loop spec](feedback-loop.md) for details.

Structured as:

```
## Previous Results

### Best result so far:
[diff of best candidate]
Metrics: throughput_rps = 1250 (+4.2% over baseline)

### Recent failure (iteration 6):
Failed: test_concurrent_access - TimeoutError
Avoid: the locking pattern used in that attempt

### Recent low-reward attempt (iteration 6):
Passed tests but throughput only 1205 (+0.4%)
The caching approach didn't help
```

Priority: best result > recent failures > low-reward attempts.
Budget: max ~25% of context.

### 5. Action request

```
Generate a code change that improves the target metric.
Apply your changes directly to the repository files.
```

Claude Code will use its Edit/Write tools to make changes.
The changes are captured as a git diff after execution.

### 6. Output format

Use `--output-format json` for structured response metadata.
The actual code changes are captured from the git diff, not from the response text.

## Claude Code invocation

Putting it together:

```bash
claude -p "$PROMPT" \
  --allowedTools "Read,Edit,Bash(git diff *),Glob,Grep" \
  --append-system-prompt "$SYSTEM_CONTEXT" \
  --output-format json \
  --max-turns 20
```

Key flags:
- `--allowedTools`: Controls what Claude can do (no Write = can't create new files)
- `--append-system-prompt`: Experiment constraints
- `--max-turns`: Prevents runaway agent loops
- Working directory: set to the git worktree for this candidate

## Context budget management

Claude Code has a large context window but we should be efficient:

| Section | Max budget | Notes |
|---------|-----------|-------|
| System context | 500 tokens | Short, declarative |
| Goal | 300 tokens | Specific, measurable |
| Repo context | Managed by Claude Code | It explores as needed |
| Feedback | 2000 tokens | Summarized, not raw |
| Action + format | 200 tokens | Minimal |

The main risk is **feedback bloat** - too many historical results
crowding out space for the LLM to think. Keep feedback concise.

## What makes a good goal description

Good:
- "Improve throughput_rps in src/server/handler.py. Baseline: 1200 rps."
- "Reduce p95 latency of the /api/search endpoint. Currently 48ms."
- "Fix the flaky test in test_cache.py::test_invalidation that fails ~20% of runs."

Bad:
- "Make it faster" (what metric? what baseline?)
- "Optimize everything" (unbounded scope)
- "Improve code quality" (unmeasurable)

## Anti-gaming in context

We deliberately omit from the prompt:
- The reward formula and weights
- Evaluation infrastructure details
- Which specific tests are run
- The holdout evaluation criteria (v2+)

The LLM should optimize for the stated goal, not for the scoring system.
