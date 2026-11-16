"""Local JSON-RPC fixture; never invokes a hook or a real Codex binary."""

import json
import sys
import time
from pathlib import Path


scenario_path = Path(sys.argv[1])
scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
trace = scenario_path.with_suffix(".trace")


def read():
    message = json.loads(sys.stdin.readline())
    with trace.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(message) + "\n")
    return message


def emit(message):
    print(json.dumps(message), flush=True)


initial = read()
assert initial["method"] == "initialize"
assert initial["params"]["clientInfo"]["name"]
if scenario.get("mode") == "initialize_timeout":
    time.sleep(60)
emit({"method": "server/notification", "params": {}})
emit({"id": True if scenario.get("mode") == "invalid_initialize_id" else initial["id"],
      "result": {"userAgent": "fixture"}})
initialized = read()
assert initialized["method"] == "initialized" and "id" not in initialized
request = read()
assert request["method"] == "hooks/list"
assert len(request["params"]["cwds"]) == 1
mode = scenario.get("mode")
if mode == "timeout":
    time.sleep(60)
elif mode == "malformed":
    print("invalid JSON reply", flush=True)
elif mode == "error":
    emit({"id": request["id"], "error": {"code": -1, "message": "fixture error"}})
elif mode == "wrong_id":
    emit({"id": 999, "result": {}})
elif mode == "closed":
    sys.exit(0)
else:
    result = scenario.get("response", {"data": [{
        "cwd": request["params"]["cwds"][0],
        "hooks": scenario.get("hooks", []), "errors": [], "warnings": [],
    }]})
    emit({"id": request["id"], "result": result})
# Success must also reap a server that remains running after its response.
time.sleep(60)
