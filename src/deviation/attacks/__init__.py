"""Synthetic outcome-blind adversarial discovery using the working engine."""
from .game import prepare_game
from .search import search
from .evidence import discover, replay, write_bundle, load_bundle

__all__=["prepare_game","search","discover","replay","write_bundle","load_bundle"]
