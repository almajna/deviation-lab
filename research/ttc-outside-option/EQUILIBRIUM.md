# Exact equilibrium welfare and price of anarchy at perfect rationality

## Scope

Consider the finite independent-action model and strict value-separation assumptions in `ORACLE.md`. Additionally, actions for each provider are totally ordered by index and each provider's margins are strictly positive and strictly increase with that index. The outside value may be any rational number. Cross-provider ties and ties with outside are excluded; values of two actions belonging to the same provider may be equal. Welfare and utilities are those in [Test-Time Compute Games v3](https://arxiv.org/html/2601.21839v3), Section 2, with perfectly rational (`β=∞`) users.

These results do not cover finite β, tied participants, coupled action constraints, imperfectly increasing margins, or empirical effects. The computational checks below do not replace the proof.

## Construction and proof

For each provider let `M_i = max_a v_i(a)` and choose any action attaining `M_i`. The provider `d` with largest `M_i` is unique by cross-provider separation.

If `M_d < V₀`, every offered value of every provider is below the outside option at every action profile. Users always abstain, all provider utilities are zero, every profile is a pure Nash equilibrium, and all equilibria and the social optimum have welfare `V₀`.

Suppose `M_d > V₀`. Put `τ = max(V₀, max_{j ≠ d} M_j)`, omitting the rival term for `N=1`. Strict separation ensures `M_d > τ`. Define `a_safe` as the **largest action index** of `d` with `v_d(a_safe)>τ`.

Every equilibrium must be served by `d`: otherwise `d` can deviate to an action attaining `M_d`, uniquely win against the outside and the others, and obtain positive margin. Its winning value must exceed every rival's maximum `M_j`, since otherwise the corresponding rival can deviate to that maximum, win, and obtain positive margin; it also beats `V₀`. Its chosen action is therefore eligible for `a_safe`. If its chosen index were smaller than `a_safe`, switching to `a_safe` would still beat outside and all rival values, while increasing its margin strictly. Thus every equilibrium chooses `d` at `a_safe`, and its welfare is the same number `v_d(a_safe)+m_d(a_safe)`.

An equilibrium exists constructively: set every rival to an action attaining its own maximum `M_j`, and set `d` to `a_safe`. No rival can win, since the dominant value exceeds every rival maximum. Any higher-index action of `d` fails to beat `τ`, which is the actual maximum of outside and current rival values; any lower-index action has lower margin. No deviation strictly increases utility. For `N=1`, outside is the only rival threshold and the same argument applies.

Combine the common equilibrium welfare with the exact attainable social optimum from `ORACLE.md`. When equilibrium welfare is strictly positive, the price of anarchy in the paper's ratio convention is `max_welfare / equilibrium_welfare`, and is the same for every equilibrium. This implementation deliberately reports the ratio as undefined (`None`) when equilibrium welfare is zero or negative, rather than asserting the conventional ratio is meaningful there. It returns an attainable maximizing profile and a Nash equilibrium profile in all cases.

Let `T` be the total number of available actions and count arithmetic/comparisons as unit operations. Computing per-provider maxima, the dominant provider, its threshold, and `a_safe` takes `O(T+N)` operations; the optimizer has the same core bound. The Python input no-tie check uses a hash table with `O(T)` expected validation time and storage; rational bit-complexity is excluded.

## Verification

From this directory run:

```
python3 test_equilibrium.py
```

Exact rational comparisons use a distinct direct full-profile enumeration, compute every unilateral deviation to identify **all** Nash equilibria, and compare the optimized welfare, optimum witness, constructed equilibrium witness, unique equilibrium welfare and ratio. The seeded synthetic test covers 2,250 games, 120,250 profiles and 30,457 equilibria for 2–4 providers and 2–4 actions, including 41 no-service games and 15 games with nonpositive equilibrium welfare. Fixed examples additionally test `N=1`, always-abstain, positive/zero/negative denominator, same-provider repeated values and rejected cross/outside ties or invalid margins. These are synthetic conformance checks, not evidence of market behavior.
