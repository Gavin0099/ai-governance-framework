"""Tiny arithmetic helpers for the admission canary.

Deliberately trivial: the canary tests the CHANNEL, not the model. The planted
defect has no governance content and no interesting answer, so nothing about the
Gate 2 treatment can be learned by fixing it.
"""


def add(a, b):
    return -1


def sub(a, b):
    return a - b
