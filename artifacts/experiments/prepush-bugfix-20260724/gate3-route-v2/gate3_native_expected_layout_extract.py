"""Derive the expected Windows ABI layout from official SDK headers.

This is the **oracle** for the SDK layout gate described in
`docs/governance/gate3-native-handle-boundary-design-candidate-20260815.md`.
Its whole reason for existing is independence: the expected sizes, alignments
and offsets must not be computed from the `ctypes` declarations they will be
compared against, or the gate would check those declarations against themselves
and pass whatever they happen to be.

What it does:

- reads the eleven struct/union definitions this slice depends on out of the
  official SDK headers, by name;
- resolves each field's type through the typedef chains **found in those same
  headers** until it reaches a fundamental C type;
- applies the documented MSVC x64 layout rules to compute size, alignment and
  per-field offsets;
- emits the artifact required by the design's closed schema.

What it does **not** do, stated plainly because it bounds what the artifact is
worth:

- it does not compile anything. A compiled oracle — a C program printing
  `sizeof` and `offsetof` — would be stronger evidence than a computation, and
  is not available here because no toolchain is installed and installing one is
  outside this slice. `extraction_method` records `headers-parsed` so the
  artifact never passes itself off as a compiled measurement;
- it executes nothing from the SDK package. Headers are read as text;
- **two** tables below are ABI facts rather than header facts: the fundamental
  types, and the preprocessor-dependent types whose headers carry more than one
  branch. Both are inputs the headers do not settle, kept small and explicit so
  a reviewer can check them directly.

Provenance is verified, not asserted. The input is the `.nupkg` itself: its
whole-file digest is checked against `PACKAGE_SHA256` before anything is read,
and the headers are then taken from fixed entry paths inside that archive. An
earlier revision accepted any header directory and stamped official package
provenance onto whatever it was handed.

Run:
  python gate3_native_expected_layout_extract.py <package.nupkg> <output.json>
"""

from __future__ import annotations

import hashlib
import io
import json
import pathlib
import re
import sys
import zipfile


SCHEMA = "gate3.native-expected-layout.v1"
EXTRACTION_METHOD = "headers-parsed"
MEASUREMENT_CLASS = "computed-not-compiled"

# The package identity the headers came from.  Recorded so a committed artifact
# names its official source chain rather than only "some header bytes".
PACKAGE_ID = "Microsoft.Windows.SDK.CPP"
PACKAGE_VERSION = "10.0.26100.8249"
PACKAGE_SHA256 = "f8787b2f6678164ae789bdca6247e696c2a0f529a39ceb969d6ef3d69a987131"
PACKAGE_SOURCE_URL = (
    "https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.cpp/"
    "10.0.26100.8249/microsoft.windows.sdk.cpp.10.0.26100.8249.nupkg"
)
SDK_VERSION = "10.0.26100.0"

# Canonical entry paths inside the package.  These are the only entries read,
# and they are read from the digest-verified archive itself, so the recorded
# provenance describes the actual input rather than a hoped-for one.
HEADER_ENTRIES = {
    "winnt.h": "c/Include/10.0.26100.0/um/winnt.h",
    "winternl.h": "c/Include/10.0.26100.0/um/winternl.h",
    "ntdef.h": "c/Include/10.0.26100.0/shared/ntdef.h",
    "WinBase.h": "c/Include/10.0.26100.0/um/WinBase.h",
    "minwinbase.h": "c/Include/10.0.26100.0/um/minwinbase.h",
    "fileapi.h": "c/Include/10.0.26100.0/um/fileapi.h",
    "minwindef.h": "c/Include/10.0.26100.0/shared/minwindef.h",
    "windef.h": "c/Include/10.0.26100.0/shared/windef.h",
    "basetsd.h": "c/Include/10.0.26100.0/shared/basetsd.h",
}

# The SDK spells its anonymous aggregate members with a placeholder macro name.
# The ctypes declarations under test name the same member `u`, and the layout
# gate compares field-name sequences exactly, so the mapping has to be fixed
# here rather than left to whichever spelling each side happened to use.
ANONYMOUS_MEMBER_NAMES = {"DUMMYUNIONNAME": "u"}

# How an anonymous aggregate is *recognised*, which is a separate question from
# how it is mapped.  The SDK writes `union { ... } DUMMYUNIONNAME;`, where the
# trailing token is a macro that expands to nothing; this extractor does not
# preprocess, so it sees the placeholder literally.  A nested aggregate is
# anonymous when it has no declarator at all, or when its declarator is one of
# these placeholders — never merely because it is nested.  `union { ... } named;`
# is an ordinary named member and must survive untouched.
PLACEHOLDER_PATTERN = re.compile(r"^DUMMY(?:UNION|STRUCT)NAME\d*$")


def is_anonymous_declarator(declarator: str) -> bool:
    """True when a nested aggregate's declarator marks it anonymous."""

    stripped = declarator.strip()
    return not stripped or bool(PLACEHOLDER_PATTERN.match(stripped))

# Fundamental C types under the MSVC x64 ABI: (size, alignment).  Not derived
# from the headers — this is the irreducible ABI input, kept small and visible.
FUNDAMENTAL = {
    "char": (1, 1),
    "signed char": (1, 1),
    "unsigned char": (1, 1),
    "short": (2, 2),
    "unsigned short": (2, 2),
    "int": (4, 4),
    "unsigned int": (4, 4),
    "long": (4, 4),
    "unsigned long": (4, 4),
    "long long": (8, 8),
    "unsigned long long": (8, 8),
    "__int64": (8, 8),
    "unsigned __int64": (8, 8),
    "float": (4, 4),
    "double": (8, 8),
    "void": (1, 1),
    "wchar_t": (2, 2),
    "POINTER": (8, 8),
}

# Types the headers define differently in different preprocessor branches.
# This extractor deliberately does **not** run the C preprocessor, so it cannot
# choose a branch by evaluating one.  The x64 arm is stated here, and the
# resolver below fails closed on any *other* type whose typedefs disagree —
# which is how `ULONGLONG` was found: winnt.h also carries a legacy `#else`
# branch defining `LONGLONG`/`ULONGLONG` as `double`, and picking whichever the
# scan reached first would have produced a confidently wrong oracle.
PREPROCESSOR_DEPENDENT = {
    # pointer-sized, behind `#ifdef _WIN64`
    "ULONG_PTR": (8, 8),
    "LONG_PTR": (8, 8),
    "DWORD_PTR": (8, 8),
    "UINT_PTR": (8, 8),
    "INT_PTR": (8, 8),
    "SIZE_T": (8, 8),
    "SSIZE_T": (8, 8),
    # 64-bit integers; the `double` spelling is the legacy no-__int64 branch
    "LONGLONG": (8, 8),
    "ULONGLONG": (8, 8),
    "DWORDLONG": (8, 8),
}

MAX_PACK = 8  # MSVC default for these headers

# The eleven types this slice depends on, and the header each is defined in.
# (Eleven: the anonymous union inside IO_STATUS_BLOCK is laid out separately.)
TARGETS = [
    ("UNICODE_STRING", "_UNICODE_STRING", "winternl.h"),
    ("OBJECT_ATTRIBUTES", "_OBJECT_ATTRIBUTES", "winternl.h"),
    ("IO_STATUS_BLOCK_UNION", "_IO_STATUS_BLOCK", "winternl.h"),
    ("IO_STATUS_BLOCK", "_IO_STATUS_BLOCK", "winternl.h"),
    ("FILE_ID_INFO", "_FILE_ID_INFO", "WinBase.h"),
    ("FILE_ATTRIBUTE_TAG_INFO", "_FILE_ATTRIBUTE_TAG_INFO", "WinBase.h"),
    ("FILE_DISPOSITION_INFO", "_FILE_DISPOSITION_INFO", "WinBase.h"),
    ("FILE_DISPOSITION_INFO_EX", "_FILE_DISPOSITION_INFO_EX", "WinBase.h"),
    ("FILE_BASIC_INFO", "_FILE_BASIC_INFO", "WinBase.h"),
    ("EXCEPTION_RECORD", "_EXCEPTION_RECORD", "winnt.h"),
    ("OSVERSIONINFOEXW", "_OSVERSIONINFOEXW", "winnt.h"),
]

# Headers carrying the eleven definitions, plus the ones their field types are
# typedef'd in.  Resolution stays inside the SDK; nothing is assumed about a
# type that these headers do not define.
HEADER_FILES = (
    "winnt.h",
    "winternl.h",
    "ntdef.h",
    "WinBase.h",
    "minwinbase.h",
    "fileapi.h",
    "minwindef.h",
    "windef.h",
    "basetsd.h",
)


class ExtractionError(Exception):
    """Closed failure. The gate must never proceed on a partial derivation."""


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def _strip_sal(text: str) -> str:
    """Remove SAL annotations, which are not part of any type.

    `typedef _Return_type_success_(return >= 0) LONG NTSTATUS;` would otherwise
    look like a function-pointer typedef because of its parentheses.
    """

    text = re.sub(r"\b_[A-Z][A-Za-z0-9_]*_\s*\([^()]*\)", " ", text)
    return re.sub(r"\b_[A-Z][A-Za-z0-9_]*_\b(?!\w)", " ", text)


def _terminate_directives(text: str) -> str:
    """Replace every preprocessor line with `;`.

    A declaration scan matching `typedef ... ;` will otherwise run across
    `#if` / `#else` / `#define` lines — none of which contain a semicolon — and
    swallow the real typedefs that follow them.  `PVOID` was found this way:
    its definition sat inside a match that began hundreds of lines earlier.
    Replacing directives with a terminator keeps declarations separate without
    pretending to evaluate any branch.  `#define` text is preserved separately
    in RAW_HEADERS, which is what constant lookup reads.
    """

    return re.sub(r"(?m)^[ \t]*#.*$", ";", text)


RAW_HEADERS: dict[str, str] = {}


def read_package(nupkg: pathlib.Path) -> dict[str, bytes]:
    """Verify the package digest, then read exactly the closed entry inventory.

    The digest is checked over the whole file **before** the archive is opened,
    so a substituted package cannot have its contents read at all.  Nothing in
    the archive is executed; only the nine header entries are extracted.
    """

    if not nupkg.is_file():
        raise ExtractionError("package not found")
    payload = nupkg.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != PACKAGE_SHA256:
        raise ExtractionError("package digest mismatch")

    contents: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        available = set(archive.namelist())
        for name, entry in HEADER_ENTRIES.items():
            if entry not in available:
                raise ExtractionError(f"missing package entry: {entry}")
            contents[name] = archive.read(entry)
    return contents


def load_headers(contents: dict[str, bytes]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name in HEADER_FILES:
        if name not in contents:
            raise ExtractionError(f"missing header: {name}")
        cleaned = _strip_sal(
            _strip_comments(contents[name].decode("utf-8", errors="replace"))
        )
        RAW_HEADERS[name] = cleaned
        headers[name] = _terminate_directives(cleaned)
    return headers


def header_digests(contents: dict[str, bytes]) -> list[dict[str, object]]:
    """One record per header, keyed by its canonical path inside the package."""

    records = []
    for name in HEADER_FILES:
        payload = contents[name]
        records.append(
            {
                "path": HEADER_ENTRIES[name],
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return sorted(records, key=lambda record: record["path"])


def find_body(headers: dict[str, str], header: str, tag: str) -> tuple[str, str]:
    """Return (kind, brace-delimited body) for `struct tag` / `union tag`."""

    text = headers[header]
    match = re.search(r"typedef\s+(struct|union)\s+" + re.escape(tag) + r"\b", text)
    if match is None:
        raise ExtractionError(f"definition not found: {tag} in {header}")
    start = text.index("{", match.start())
    depth = 0
    index = start
    while index < len(text):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                break
        index += 1
    else:
        raise ExtractionError(f"unbalanced braces in {tag}")
    return match.group(1), text[start + 1 : index]


def resolve_constant(headers: dict[str, str], name: str) -> int:
    """Resolve an integer `#define` from the headers."""

    for text in RAW_HEADERS.values():
        match = re.search(
            r"#define\s+" + re.escape(name) + r"\s+(0x[0-9A-Fa-f]+|\d+)\b", text
        )
        if match:
            token = match.group(1)
            return int(token, 16) if token.lower().startswith("0x") else int(token)
    raise ExtractionError(f"constant not found: {name}")


def resolve_typedef(headers: dict[str, str], name: str) -> set[str]:
    """Every base-type spelling the headers give for `name`.

    A set, not one answer, because the headers carry every preprocessor branch.
    Disagreement is settled by the caller comparing *resolved metrics* rather
    than spellings: `HANDLE` is spelled both `void *` and `PVOID` under
    `#ifdef STRICT`, and those are the same type, while `ULONG_PTR` really does
    differ between the 32- and 64-bit arms.
    """

    statement_pattern = re.compile(r"typedef\s+([^;{}]+);")
    resolutions: set[str] = set()

    for text in headers.values():
        for match in statement_pattern.finditer(text):
            statement = " ".join(match.group(1).split())
            if "(" in statement:
                # function-pointer typedef; only relevant if it names our type
                # Require an explicit `*`: `(*PFOO)` is a declarator, whereas
                # `(DWORD)` is a parameter and says nothing about DWORD.
                if re.search(r"\*\s*" + re.escape(name) + r"\s*\)", statement):
                    resolutions.add("POINTER")
                continue
            declarators = [d.strip() for d in statement.split(",") if d.strip()]
            if not declarators:
                continue
            base = re.sub(
                r"[\*\s]*[A-Za-z_]\w*(\[[^\]]*\])?$", "", declarators[0]
            ).strip()
            for declarator in declarators:
                tokens = declarator.replace("*", " * ").split()
                if not tokens or tokens[-1] != name:
                    continue
                resolutions.add("POINTER" if "*" in declarator else base)

    if not resolutions:
        raise ExtractionError(f"typedef not found: {name}")
    return resolutions


def type_metrics(headers: dict[str, str], spec: str, seen: frozenset[str]) -> tuple[int, int]:
    """(size, alignment) for a type spelling, resolved through the headers."""

    spec = " ".join(spec.replace("CONST", "").replace("const", "").split())
    if "*" in spec:
        return FUNDAMENTAL["POINTER"]
    spec = re.sub(r"^(struct|union|enum)\s+", "", spec).strip()
    if spec in FUNDAMENTAL:
        return FUNDAMENTAL[spec]
    if spec in ("WCHAR", "wchar_t"):
        return FUNDAMENTAL["wchar_t"]
    if spec in PREPROCESSOR_DEPENDENT:
        return PREPROCESSOR_DEPENDENT[spec]
    if spec in seen:
        raise ExtractionError(f"typedef cycle at {spec}")

    # A composite the headers define, such as LARGE_INTEGER or FILE_ID_128.
    for header in HEADER_FILES:
        for tag in (f"_{spec}", spec):
            try:
                kind, body = find_body(headers, header, tag)
            except ExtractionError:
                continue
            fields = parse_fields(headers, body, seen | {spec})
            size, alignment, _ = lay_out(kind, fields)
            return size, alignment

    candidates = resolve_typedef(headers, spec)
    metrics = {
        type_metrics(headers, candidate, seen | {spec}) for candidate in candidates
    }
    if len(metrics) > 1:
        raise ExtractionError(
            f"conflicting typedefs for {spec}: "
            f"{sorted(candidates)} resolve to {sorted(metrics)}"
        )
    return metrics.pop()


def parse_fields(
    headers: dict[str, str], body: str, seen: frozenset[str] = frozenset()
) -> list[dict[str, object]]:
    """Parse one level of member declarations out of a struct/union body."""

    fields: list[dict[str, object]] = []
    index = 0
    while index < len(body):
        character = body[index]
        if character == "#":  # a pragma line inside the body
            index = body.find("\n", index) + 1 or len(body)
            continue
        if character.isspace():
            index += 1
            continue

        nested = re.match(r"(struct|union)\s*\{", body[index:])
        if nested:
            open_brace = body.index("{", index)
            depth = 0
            cursor = open_brace
            while cursor < len(body):
                if body[cursor] == "{":
                    depth += 1
                elif body[cursor] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                cursor += 1
            inner = body[open_brace + 1 : cursor]
            end = body.index(";", cursor)
            inner_fields = parse_fields(headers, inner, seen)
            size, alignment, _ = lay_out(nested.group(1), inner_fields)
            declarator = body[cursor + 1 : end].strip()
            anonymous = is_anonymous_declarator(declarator)
            fields.append(
                {
                    "name": declarator or "DUMMYUNIONNAME",
                    "size": size,
                    "alignment": alignment,
                    "anonymous": anonymous,
                    "anonymous_members": inner_fields,
                }
            )
            index = end + 1
            continue

        end = body.find(";", index)
        if end == -1:
            break
        declaration = " ".join(body[index:end].split())
        index = end + 1
        if not declaration:
            continue

        array = re.search(r"\[\s*([^\]]+?)\s*\]$", declaration)
        count = 1
        if array:
            token = array.group(1)
            count = int(token) if token.isdigit() else resolve_constant(headers, token)
            declaration = declaration[: array.start()].strip()

        parts = declaration.split()
        name = parts[-1].lstrip("*")
        spec = " ".join(parts[:-1])
        if declaration.count("*") and "*" not in spec:
            spec += " *"
        size, alignment = type_metrics(headers, spec, seen)
        fields.append(
            {"name": name, "size": size * count, "alignment": alignment}
        )
    return fields


def lay_out(kind: str, fields: list[dict[str, object]]):
    """MSVC x64 layout: members at min(natural, pack), size rounded to alignment."""

    if not fields:
        raise ExtractionError("empty aggregate")
    placed = []
    if kind == "union":
        size = max(int(f["size"]) for f in fields)
        alignment = max(min(int(f["alignment"]), MAX_PACK) for f in fields)
        for field in fields:
            placed.append(
                {
                    "name": field["name"],
                    "offset": 0,
                    "size": int(field["size"]),
                    "anonymous": bool(field.get("anonymous")),
                }
            )
    else:
        offset = 0
        alignment = 1
        for field in fields:
            field_alignment = min(int(field["alignment"]), MAX_PACK)
            alignment = max(alignment, field_alignment)
            if offset % field_alignment:
                offset += field_alignment - (offset % field_alignment)
            placed.append(
                {
                    "name": field["name"],
                    "offset": offset,
                    "size": int(field["size"]),
                    "anonymous": bool(field.get("anonymous")),
                }
            )
            offset += int(field["size"])
        size = offset
    if size % alignment:
        size += alignment - (size % alignment)
    return size, alignment, placed


def canonical_field_names(placed: list[dict[str, object]]) -> list[dict[str, object]]:
    """Apply the anonymous-member mapping, refusing anything unregistered.

    Only members the parser marked anonymous are considered, so a *named*
    member that happens to collide with a placeholder spelling is untouched.
    An anonymous member with no exact mapping is a closed failure: the layout
    gate compares names exactly, so passing an unknown spelling through would
    quietly make it the expected one.
    """

    result = []
    for field in placed:
        entry = dict(field)
        anonymous = entry.pop("anonymous", False)
        if anonymous:
            mapped = ANONYMOUS_MEMBER_NAMES.get(entry["name"])
            if mapped is None:
                raise ExtractionError(f"unmapped anonymous member: {entry['name']}")
            entry["name"] = mapped
        result.append(entry)
    return result


def build(nupkg: pathlib.Path, extractor_path: str) -> dict[str, object]:
    contents = read_package(nupkg)
    headers = load_headers(contents)
    types: dict[str, object] = {}

    for public_name, tag, header in TARGETS:
        kind, body = find_body(headers, header, tag)
        fields = parse_fields(headers, body)

        if public_name == "IO_STATUS_BLOCK_UNION":
            # The union is declared anonymously inside IO_STATUS_BLOCK; the
            # design names it separately, so it is laid out on its own.
            anonymous = next(
                (f for f in fields if "anonymous_members" in f), None
            )
            if anonymous is None:
                raise ExtractionError("IO_STATUS_BLOCK has no anonymous union")
            kind = "union"
            fields = anonymous["anonymous_members"]  # type: ignore[assignment]

        size, alignment, placed = lay_out(kind, fields)
        placed = canonical_field_names(placed)
        types[public_name] = {
            "kind": "union" if kind == "union" else "structure",
            "size": size,
            "alignment": alignment,
            "fields": placed,
        }

    return {
        "schema": SCHEMA,
        "provenance": {
            "abi": "64/win64/WinDLL",
            "extraction_method": EXTRACTION_METHOD,
            "extractor_path": extractor_path,
            "extractor_sha256": hashlib.sha256(
                pathlib.Path(__file__).read_bytes()
            ).hexdigest(),
            "fundamental_type_table": {
                name: list(value) for name, value in sorted(FUNDAMENTAL.items())
            },
            "header_digests": header_digests(contents),
            "measurement_class": MEASUREMENT_CLASS,
            "pack": MAX_PACK,
            "package_id": PACKAGE_ID,
            "package_sha256": PACKAGE_SHA256,
            "package_source_url": PACKAGE_SOURCE_URL,
            "package_version": PACKAGE_VERSION,
            "preprocessor_dependent_type_table": {
                name: list(value)
                for name, value in sorted(PREPROCESSOR_DEPENDENT.items())
            },
            "sdk_version": SDK_VERSION,
        },
        "types": types,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    package = pathlib.Path(sys.argv[1])
    destination = pathlib.Path(sys.argv[2])
    report = build(
        package,
        "artifacts/experiments/prepush-bugfix-20260724/gate3-route-v2/"
        "gate3_native_expected_layout_extract.py",
    )
    destination.write_bytes(
        json.dumps(report, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    print(f"wrote {destination}")
