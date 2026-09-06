"""Select queue entries by sequence number without changing the input."""


def select_entries(entries, lower, upper):
    return [entry for entry in entries if lower < entry[0] < upper]
