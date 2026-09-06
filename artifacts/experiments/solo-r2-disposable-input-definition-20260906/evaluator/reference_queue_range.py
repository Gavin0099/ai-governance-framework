"""Reference repair used only to qualify the disposable evaluation inputs."""


def select_entries(entries, lower, upper):
    return [entry for entry in entries if lower <= entry[0] <= upper]
