# Running an agent slice and watching it quietly

How to hand a coding agent one approved slice and get told only when something
needs you. The tools already exist: `codex exec` (or any agent CLI), the agent's
own exit, `git`, `gh`, and the harness's background-task notification. Nothing
here is a gate, a daemon or a new tool. It is report-only practice.

## 1. Run one slice

Give the agent the goal, the approved scope and DONE in the prompt. Do not
restate governance rules; the repo's instruction files carry them.

```text
<goal>.
Approved slice: you may edit, build, test and commit on the current branch `<branch>`; do not push.
DONE = <observable check, e.g. `dotnet test <project>` passes> and the change is committed. Report the result when done.
```

```bash
codex exec --json -C <repo> -s workspace-write --add-dir <git-dir> -o <out>/last.txt "<prompt>" > <out>/run.jsonl 2> <out>/run.err
```

- The `workspace-write` sandbox keeps `.git` read-only. For a slice that may
  commit, keep the git directory outside the workspace
  (`git init --separate-git-dir=<git-dir>`) and pass it with `--add-dir`.
- Start it as a background task and let the harness notify you when it exits.
  Do not poll it with `sleep`.

## 2. Judge from the repository, not from the report

When the run ends, check git and rerun the DONE check yourself. The agent's
final text is a claim, not evidence.

- `git log --oneline <base>..HEAD` and `git status --short`: is the work
  committed on the slice branch, is the tree clean, did anything get pushed?
- Rerun the DONE command. For a bug fix, also run the new test against the
  pre-fix tree and confirm that it fails there.
- Check that the work did not grow beyond the slice: no unrequested renames,
  no new files outside it, no second task started.

## 3. Watch a PR, CI or review quietly

Poll at a pace that matches how fast the state changes, about once a minute
for CI and review. Then:

- **Log every poll** to a local file, one line per poll.
- **Notify only** when the state changes, when a terminal result appears, or
  after 3 polls in a row with no change. The 3-poll message is a stall report,
  not a failure.
- **Bind to the exact head SHA.** Read every bot comment for that SHA, not only
  the latest comment. A later comment can be about an older head.
- **Stop by itself** at a terminal state: review finished for this head and no
  check pending, the PR merged or closed, or a time limit.
- Keep the log file name outside any pattern the watcher deletes on start.

```bash
LOG=<out>/watch.log; prev=""; same=0
while :; do
  state=$(<command that prints one line of state for the exact head SHA>)
  echo "$(date -u +%H:%M:%S) $state" >> "$LOG"
  if [ "$state" != "$prev" ]; then echo "$state"; prev=$state; same=0; else same=$((same + 1)); fi
  [ "$same" -eq 3 ] && echo "no change for 3 polls: $state"
  case "$state" in *terminal*) echo "DONE"; exit 0;; esac
  sleep 60
done
```

Run the watcher as a background task too. Its printed lines are the only
notifications. The log is there if you need the full history.
