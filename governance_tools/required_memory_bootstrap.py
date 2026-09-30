"""Build-time template embedded verbatim in the inactive Hook definition.

The host's exact-definition trust is the eventual root, not this file's path.
Only BINDING supplied as a literal inside that definition is accepted.
"""
import hashlib
import json
from pathlib import Path


def run(binding):
    try:
        path = Path(binding["launcher_path"])
        if not path.is_absolute():
            raise ValueError("launcher path must be absolute")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest().upper() != binding["launcher_sha256"]:
            raise ValueError("launcher SHA mismatch")
        # Execute the bytes just verified; do not reopen the executable file.
        namespace = {"__name__": "__candidate_launcher__", "__file__": str(path)}
        exec(compile(raw, str(path), "exec"), namespace)
        result = namespace["run"](binding)
        if not isinstance(result, dict):
            raise ValueError("launcher response must be an object")
    except Exception as exc:
        result = {"decision": "block", "reason":
                  "MEMORY_BOOTSTRAP_INTEGRITY_ERROR: " + type(exc).__name__ + ": " + str(exc)}
    print(json.dumps(result, ensure_ascii=True))


# The builder appends run(<literal binding>); this template never loads a config file.
