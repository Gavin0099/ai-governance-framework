# Governed Prompt Usage

Use one bridge for ChatGPT / Claude / Gemini so all requests carry the same governance contract.

## Command

```powershell
python -m governance_tools.governed_prompt_bridge `
  --provider chatgpt `
  --lang C++ `
  --level L0 `
  --scope review `
  --plan "Phase 1 / Offer packet check" `
  --loaded "SYSTEM_PROMPT, HUMAN-OVERSIGHT, AGENT" `
  --context "offer review -> check format; NOT: protocol rewrite" `
  --pressure "SAFE (40/200)" `
  --prompt "請檢查 offer 封包欄位定義是否一致" `
  --format json
```

## Providers

- `chatgpt`
- `claude`
- `gemini`

Aliases:

- `chatgot` -> `chatgpt`
- `gemnin` -> `gemini`

## Output

- governed prompt text/json
- injection artifact written to:
  - `artifacts/runtime/injection/<YYYY-MM-DD>/<timestamp>-<provider>.json`

