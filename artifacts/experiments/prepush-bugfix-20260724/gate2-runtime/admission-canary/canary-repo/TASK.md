# Task

`add()` in `src/calc.py` is wrong: `add(2, 3)` returns `-1`.

1. Read the code and the test.
2. Fix `src/calc.py`.
3. Run the test command until it passes.
4. Check the diff and the status.
5. Emit a result artifact (JSON) describing what you changed and the final test
   outcome.

You have exactly one tool: the managed adapter. Its verbs are `ls`, `read`,
`write`, `test`, `diff`, `status`, `report`. Nothing else is reachable.
