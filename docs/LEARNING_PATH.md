# Research director — what to understand personally

You can delegate coding, not scientific comprehension. Spend ~20–30 minutes after each major milestone:

1. **Budgeted optimization.** Given three models and two tasks, write what is feasible under budget, what the cheapest route is, and what an oracle knows that a real allocator does not.
2. **Prediction market mechanics.** Understand how an event contract pays out, difference between a forecast report and trade, Brier score, virtual credit constraints, and market-maker subsidies.
3. **Game theory.** For a strategic participant, state available actions, private information, utility, truthful baseline and profitable unilateral deviation. Collusion has a different action space.
4. **Causal/counterfactual reasoning.** Explain why real routing only reveals selected results, while a paired offline dataset can evaluate alternative choices on historical prompts.
5. **Research methodology.** Teach back train/validation/test, information leakage, confidence interval, strongest non-market baseline, and why independent review matters.
6. **Exploit interpretation.** Take one saved exploit and reproduce its net payoff/welfare change manually on a 2-task game.

## Prompt for Codex/Claude tutor
> Teach me the currently implemented mechanism from DEVIATION, not a fictional version. Start with a simple numerical example, show the exact payoff and information available to each actor, then quiz me one question at a time until I can explain a reported exploit and its scientific limitations. Link code/test files so I can verify your explanation.

## Questions to ask at your five approval gates
- What exactly can the model/agent see at decision time?
- Does this result rely on fabricated private information or true recorded LLM behavior?
- Could simple averaging or greedy allocation beat the market?
- Is the attack profitable *net* of costs, and is it allowed by the rules?
- Is the final demo powered by experiment traces or handpicked fake numbers?
