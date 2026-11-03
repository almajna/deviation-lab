"""Fail-closed exploratory authorization; no final/test evaluation entry point."""
from copy import deepcopy
from deviation.data.pipeline import digest


class ProtocolError(ValueError):
    pass


def check(protocol, review):
    if (protocol.get('version') != 'benchmark-protocol-1'
            or protocol.get('status') != 'EXPLORATORY_VALIDATION_ONLY_FINAL_DISABLED'
            or protocol.get('guardrails') != {'final_evaluation_enabled': False,
                'recorded_test_split_enabled': False, 'paid_spend_usd': 0,
                'frontend_changes': False, 'validation_tuning': False}
            or protocol.get('recorded', {}).get('allowed_decision_split') != 'validation'):
        raise ProtocolError('FINAL_TEST_OR_UNREVIEWED_SCOPE_FORBIDDEN')
    if (review.get('protocol_sha256') != digest(protocol)
            or review.get('verdict') != 'PASS_EXPLORATORY_VALIDATION_ONLY'
            or not review.get('reviewer') or not review.get('document_sha256')):
        raise ProtocolError('INDEPENDENT_PROTOCOL_REVIEW_REQUIRED')
    d = protocol['synthetic']['development_seeds']
    v = protocol['synthetic']['validation_seeds']
    if not d or not v or set(d) & set(v) or len(set(d)) != len(d) or len(set(v)) != len(v):
        raise ProtocolError('WORLD_SEED_OVERLAP')
    return deepcopy(protocol)
