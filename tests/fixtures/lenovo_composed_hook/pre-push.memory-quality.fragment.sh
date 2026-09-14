# BEGIN LENOVO_ISP_MEMORY_QUALITY_GATE
TODAY_UTC="${TODAY_UTC:-$(date -u +%Y-%m-%d)}"
if [ -f "$TARGET_REPO_ROOT/validate-memory-quality.ps1" ]; then
    if command -v pwsh >/dev/null 2>&1; then
        MEMORY_QUALITY_CMD=(pwsh -NoProfile -ExecutionPolicy Bypass -File "$TARGET_REPO_ROOT/validate-memory-quality.ps1" -UtcDate "$TODAY_UTC")
    elif command -v powershell >/dev/null 2>&1; then
        MEMORY_QUALITY_CMD=(powershell -NoProfile -ExecutionPolicy Bypass -File "$TARGET_REPO_ROOT/validate-memory-quality.ps1" -UtcDate "$TODAY_UTC")
    else
        echo ""
        echo "[governance] blocked: PowerShell not found; cannot run validate-memory-quality.ps1"
        echo "  install PowerShell (pwsh/powershell) or remove the gate script"
        echo ""
        exit 1
    fi

    if ! "${MEMORY_QUALITY_CMD[@]}"; then
        echo ""
        echo "[governance] blocked: daily memory semantic quality gate failed"
        echo "  fix memory/YYYY-MM-DD.md required sections/evidence and push again"
        echo ""
        exit 1
    fi
fi
# END LENOVO_ISP_MEMORY_QUALITY_GATE

