"""Reuse pinned JSON ingestion; raw rows stay in the local cache."""
from deviation.data.acquire import cached_input, result_members
from deviation.data.pipeline import (load_llmrouterbench, overlap_report, validate_records,
                                     validate_splits, digest, decision_view)
from deviation.simulator.reservations import prepare_records


def load(manifest, splits, cache, *, download=False, decision_split='validation'):
    if decision_split != 'validation' or splits.get('status') != 'EXPLORATORY_NOT_FROZEN':
        raise ValueError('FINAL_OR_TEST_ACCESS_FORBIDDEN')
    raw = cached_input(manifest['inputs']['llm_archive_prefix'],cache,download=download)
    records=[]
    for spec, doc in result_members(raw,manifest['llm_sample']['members']):
        rows,_=load_llmrouterbench(doc,revision=manifest['llm_sample']['revision'],
            metric='arena_hard_judged_win_tie_loss',cost_unit='reported_usd',
            cost_basis='api_usage_cost_or_token_pricing_unresolved',collect_invalid=True)
        records.extend(rows)
    models=tuple(sorted(m['model_id'] for m in manifest['llm_sample']['members']))
    complete=set(overlap_report(records,required_models=models)['complete_task_ids'])
    cohort=[r for r in records if r.task_id in complete]
    validate_records(cohort,required_models=models);validate_splits(cohort,splits)
    # Existing exploratory test rows are parsed only by the audited ingestion
    # validator; no models, calibration or metrics below can receive those rows.
    training=[r for r in cohort if splits['tasks'][r.task_id]['split']=='train']
    selected=[r for r in cohort if splits['tasks'][r.task_id]['split']=='validation']
    prepared=prepare_records(cohort,splits,source_manifest_sha256=digest(manifest),decision_split='validation')
    train=[{'task_id':r.task_id,'model_id':r.model_id,'prompt':r.prompt,'quality':r.quality} for r in training]
    return prepared,train,{'cohort_tasks':len(complete),'training_tasks':len({r.task_id for r in training}),
        'validation_tasks':len({r.task_id for r in selected}), 'excluded_exploratory_test_tasks':len(complete)-len(training)//len(models)-len(selected)//len(models),
        'source_manifest_sha256':digest(manifest),'split_manifest_sha256':splits['sha256'],
        'data_kind':'RECORDED_LLM_OUTCOMES_PLUS_SIMULATED_AGENTS','raw_data_redistributed':False}
