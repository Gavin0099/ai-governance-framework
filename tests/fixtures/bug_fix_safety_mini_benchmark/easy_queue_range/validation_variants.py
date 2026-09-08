"""Evaluator-only authored fixtures, never arm/scorer input."""


def correct(entries, lower, upper):
    return [entry for entry in entries if lower <= entry[0] <= upper]


def superficial(entries, lower, upper):
    return [entry for entry in entries if lower <= entry[0] < upper]
