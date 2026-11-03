"""Outcome-free attack certificates; the verifier can be imported alone."""


def solve(game, **kwargs):
    from .solver import solve as implementation
    return implementation(game, **kwargs)


def verify(game, certificate, **kwargs):
    from .checker import verify as implementation
    return implementation(game, certificate, **kwargs)


__all__ = ['solve', 'verify']
