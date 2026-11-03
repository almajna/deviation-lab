"""Paired cluster resampling; never treats correlated trades/seeds as tasks."""
from collections import defaultdict
import random
from math import fsum


def interval(sums, sizes, *, replicates=2000, seed=7307):
    if not sums or len(sums)!=len(sizes) or min(sizes)<=0:raise ValueError('INVALID_CLUSTERS')
    rng=random.Random(seed);N=len(sums);draws=[]
    for _ in range(replicates):
        idx=[rng.randrange(N) for _ in range(N)]
        draws.append(fsum(sums[i] for i in idx)/sum(sizes[i] for i in idx))
    draws.sort()
    return {'estimate':fsum(sums)/sum(sizes),'lower':draws[int(.025*(replicates-1))],
        'upper':draws[int(.975*(replicates-1))],'clusters':N,
        'method':'paired_cluster_percentile_ratio_95','replicates':replicates}


def recorded_summary(rows, mechanisms, cfg):
    output=[]
    for budget in sorted({r['budget_fraction'] for r in rows}):
        selected=[r for r in rows if r['budget_fraction']==budget]
        ref={(r['batch'],r['seed']):r for r in selected if r['mechanism']=='calibrated-pool'}
        for m in mechanisms:
            own=[r for r in selected if r['mechanism']==m]
            grouped=defaultdict(list)
            for r in own:grouped[r['batch']].append(r)
            sums=[];sizes=[];deltas=[]
            for batch,rs in sorted(grouped.items()):
                n=rs[0]['task_count'];sizes.append(n)
                sums.append(fsum(r['quality'] for r in rs)*n/len(rs))
                deltas.append(fsum(r['quality']-ref[batch,r['seed']]['quality'] for r in rs)*n/len(rs))
            result={'mechanism':m,'budget_fraction':budget,'tasks':sum(sizes),
                'quality':interval(sums,sizes,replicates=cfg['bootstrap_replicates'],seed=cfg['bootstrap_seed']),
                'difference_vs_calibrated_pool':interval(deltas,sizes,replicates=cfg['bootstrap_replicates'],seed=cfg['bootstrap_seed']),
                'uncertainty_scope':'conditional_fixed_budget_batches_seed_averaged_not_population'}
            for key in ['regret','brier','proxy_squared_error','tie_zero_quality','tie_one_quality','zero_as_one_quality','reservation_utilization','calibration_abs_error','rerouted_fraction']:
                result[key]=fsum(r[key]*r['task_count'] for r in own)/sum(r['task_count'] for r in own)
            for key in ['reservation_spend','realized_spend','positive_task_overruns','unused_reservations','net_overrun','realized_budget_excess','fees','maker_initial_funding','maker_cash_pnl','score_reserve','score_paid','accepted','rejected','trades','updates','noops','optional_slots']:
                result[key]=fsum(r[key] for r in own)/len({r['seed'] for r in own})
            result['reliability_bins']=[{k:fsum(r['calibration_bins'][i][k] for r in own)/len({r['seed'] for r in own}) for k in ['count','prediction_sum','outcome_sum']} for i in range(5)]
            result['brier_interval']=interval([fsum(r['brier']*r['task_count'] for r in rs)/len(rs) for _,rs in sorted(grouped.items())],sizes,replicates=cfg['bootstrap_replicates'],seed=cfg['bootstrap_seed'])
            result['batch_budget_violation_fraction']=sum(r['realized_budget_violated'] for r in own)/len(own)
            output.append(result)
    return output


def synthetic_summary(rows,cfg):
    output=[]
    for profile in sorted({r['profile'] for r in rows}):
        for mechanism in sorted({r['mechanism'] for r in rows}):
            rs=[r for r in rows if r['profile']==profile and r['mechanism']==mechanism]
            result={'profile':profile,'mechanism':mechanism,'worlds':len(rs),'all_schedules_supported':True}
            for field in ['utility_gain','gain_vs_no_action','cash_gain','external_gain','welfare_loss','rerouted_fraction','zero_external_gain','quality','brier','fees','maker_cash_pnl','score_paid','accepted','rejected','trades','updates','noops']:
                result[field]=interval([r[field] for r in rs],[1]*len(rs),replicates=cfg['bootstrap_replicates'],seed=cfg['bootstrap_seed'])
            result['profitability_interpretation']='POSITIVE_WORLD_MEAN_INTERVAL' if result['utility_gain']['lower']>0 else 'INCONCLUSIVE_OR_NONPOSITIVE'
            result['uncertainty_scope']='Monte_Carlo_worlds_within_profile_not_LLM_population'
            output.append(result)
    return output
