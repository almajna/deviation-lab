# Exact welfare maximization with perfectly rational users

## Scope

This result concerns the **perfect-rationality** (`β=∞`) model in [Test-Time Compute Games v3](https://arxiv.org/html/2601.21839v3), Section 2 and welfare equation (5). Each of `N≥1` providers independently chooses one action from its finite, nonempty set. Provider `i` action `a` offers value `v_i(a)` and margin `m_i(a)`; outside has value and welfare `V₀`. The unique highest value wins, including outside; if provider `i` wins, welfare is `v_i(a)+m_i(a)`. Assume every value of one provider differs from every value of another provider and from `V₀`. Values may repeat between actions of the same provider. Margins need not be positive for the general result below; the paper's positive-margin model is a special case.

This is a mathematical result for independent finite action sets, not a claim about finite-β logit markets, real data, equilibria, coupled resource constraints or empirical performance. The paper says the welfare-maximizing profile is generally intractable; this result concerns a restricted special case, and does not refute a general finite-β intractability claim.

## Theorem and proof

Let `L_i = min_a v_i(a)` and define

```
T_i = max(V₀, max_{j ≠ i} L_j),
```

where the maximum over no rivals is omitted. Provider `i` can win with action `a` **if and only if** `v_i(a) > T_i`.

Necessity: if that action wins, it beats outside and each rival's chosen value, and each rival's minimum is no greater than its chosen value. Sufficiency: put every rival at a minimum-value action. The strict inequality then makes `i` the unique winner.

Outside can win **if and only if** every `L_i < V₀`: necessity follows from each chosen value being at least its minimum; sufficiency follows by choosing a minimum-value action for every provider. Therefore the attainable welfare maximum is exactly

```
max({V₀ if max_i L_i < V₀}
    ∪ {v_i(a) + m_i(a) : v_i(a) > T_i}).
```

The set is nonempty because every finite tie-free profile has either a provider winner or outside winner. A maximizing profile is obtained by selecting the maximizing provider/action (if any) and assigning each rival a minimum-value action; if outside maximizes, assign every provider a minimum-value action. This proves both the value and a constructive witness.

If all margins are **positive**, any realizable provider win has `v_i(a)+m_i(a)>V₀`. Consequently, the expression can be simplified by always including `V₀`, even when outside is unattainable: if outside is unattainable there must be some attainable provider win, and its welfare strictly exceeds `V₀`. This simplification is not generally valid for nonpositive margins. Example: one provider has a single value `1`, margin `−2`, outside `0`. The only feasible welfare is `−1`, not `0`.

## Complexity and implementation

Let `T` be the total number of actions across providers. Compute each `L_i` and a minimizing action in `O(T)`. Find the largest and second-largest `L_i` in one linear pass. Then each `T_i` is available in constant time; scan every action once and build the winning witness once, after the scan. The core uses `O(T+N)` arithmetic/comparison operations and `O(N)` auxiliary storage beyond the input. The implementation also checks the no-tie precondition using a hash table, with `O(T)` expected time and `O(T)` storage. Exact rational arithmetic bit costs are not constant in general. For `N=1`, there is no rival term and `T_1=V₀`.

`oracle.py` implements the general formula for finite rational inputs, including nonpositive margins, and returns both optimum and a realizable action profile. Reproduce the separate direct full-profile comparator and fixed regression cases with:

```
python3 test_oracle.py
```

A deterministic randomized check with seed 20261105 tested 4,000 synthetic games across 1–5 providers and 1–4 actions each, enumerating all 358,800 profiles. Of these games, 3,453 included a nonpositive margin. Every optimum and returned witness matched enumeration; explicit tests cover outside infeasibility, attainable outside, single-provider games, same-provider repeated values, and invalid cross-provider/outside ties. These checks exercise finite examples and do not replace the proof or establish real-world effects.
