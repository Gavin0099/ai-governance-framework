from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = REPO_ROOT / "governance" / "AUTHORITY.md"


def _authority_documents() -> list[str]:
    documents: list[str] = []
    in_authority_table = False
    for line in AUTHORITY.read_text(encoding="utf-8").splitlines():
        if line == "## Authority Table":
            in_authority_table = True
            continue
        if in_authority_table and line == "---":
            break
        if not in_authority_table:
            continue
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        document = cells[0].split("`", maxsplit=2)[1]
        if document == "document":
            continue
        documents.append(document)
    return documents


def _is_repo_local_file_reference(document: str) -> bool:
    if "*" in document:
        return False
    if document.startswith(("governance/", "docs/", "memory/", ".github/", "AGENTS.md")):
        return True
    return False


def test_authority_repo_local_document_references_exist() -> None:
    missing = []
    for document in _authority_documents():
        if not _is_repo_local_file_reference(document):
            continue
        candidate = REPO_ROOT / document
        if not candidate.exists():
            missing.append(document)

    assert missing == []
