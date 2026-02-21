# ADR-002: Sequential Conditioned Sampling over Evolutionary Search for v1

## Status
Accepted

## Context
The original design specified a full evolutionary search system:
frontier of K=8, epsilon-greedy parent selection, granularity distributions,
5 generation strategies, and population-based selection.

Research from Feb 2025 ("Simple Baselines are Competitive with Code Evolution",
arxiv 2602.16805) showed that Sequential Conditioned Sampling (SCS) -
generate, evaluate, feed successes as context to next batch - matches or
beats sophisticated evolutionary systems on most tasks using identical LLM budgets.

Key finding: "a problem's search space and domain knowledge in the prompt
are chiefly what dictate a search's performance ceiling."

This aligns with findings from AlphaEvolve, OpenEvolve, and CodeEvolve
where the evaluation pipeline and feedback mechanisms drive more improvement
than selection sophistication.

## Decision
v1 uses **Sequential Conditioned Sampling**:
- No frontier/population management
- No epsilon-greedy selection
- No granularity prescriptions or strategy portfolios
- Selection = "best so far" as context conditioning
- Feedback loops (success context + failure traces) as the convergence mechanism

Added two new critical specs:
- **Feedback Loop**: how evaluation results flow back to generation
- **Context Engineering**: what goes into each Claude Code prompt

## Consequences
- Dramatically simpler implementation (Python script vs framework)
- Faster to build and debug
- Easier to understand what's working vs what's not
- Clear upgrade path: add population/frontier when data shows SCS plateaus
- Risk: may converge slower on tasks where population diversity matters
- Mitigation: always maintain IID RS baseline comparison - if SCS doesn't beat
  "ask N times and pick best", the feedback loop needs debugging, not more machinery

## References
- "Simple Baselines are Competitive with Code Evolution" (arxiv 2602.16805, Feb 2025)
- AlphaEvolve (Google DeepMind, May 2025)
- OpenEvolve cascade evaluation pattern
- CodeEvolve inspiration-based crossover via LLM context
- Eureka reward reflection mechanism
