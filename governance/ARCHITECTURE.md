# ARCHITECTURE.md
**Architecture Governance and Boundary Rules - v4.1**

> **Version**: 4.1 | **Priority**: 5 (Structural Red Lines)
>
> Defines how the system is partitioned, what may change, and which boundaries are hard red lines.

---

## 0. Loading Condition

- load for new features, refactors, boundary changes, and other non-trivial L1/L2 work
- load when architecture impact is plausible, not only when it is already proven

---

## 1. Core Principles

### 1.1 Architecture Before Implementation

Boundaries, responsibilities, and data flow must be understandable before implementation expands.

If the architecture cannot be articulated at all, implementation is not yet defensible.

### 1.2 Explicit Boundaries

Every touched component should be classifiable as one of:
- Domain
- Application
- Adapter
- Infrastructure

Each component should answer:
- responsible for what
- explicitly **NOT** responsible for what

### 1.3 Governance Goal

Architecture governance exists to prevent catastrophic coupling and hidden boundary erosion.

It should reduce risk, not punish trivial, low-risk work.

---

## 2. Bounded Context

### 2.1 Mandatory Questions for L1+

Before boundary-sensitive work, answer:
- which bounded context does this belong to
- does it involve native APIs, platform variance, or external systems
- is an Anti-Corruption Layer required

### 2.2 Continue / Escalate / Stop for Architecture

- **Continue**: context and ownership are clear
- **Escalate**: context is mostly clear, but a boundary choice or abstraction choice has multiple defensible options
- **Stop**: the proposed change crosses a hard boundary or cannot be classified coherently

Do not stop merely because some design judgment is needed; use escalate first unless a red line is already crossed.

### 2.3 L0 Exception

L0 remains limited to presentation-only or trivial edits with:
- no Domain/Infrastructure crossing
- no native/I/O/state interaction
- no hidden behavior change

Uncertain -> upgrade to L1.

---

## 3. Domain vs Infrastructure

### 3.1 Domain Hard Red Lines

Domain must **not**:
- call native APIs directly
- depend on `.dll`, `.so`, `.dylib`, `.framework`, or equivalent runtime bindings
- depend on UI, OS, filesystem, network, time, or environment state

Domain should consume capabilities only through explicit, stable interfaces.

### 3.2 Infrastructure Anti-False-Positive Rule

The following are **not automatically** infrastructure leakage:
- pure data transformations
- OS-agnostic utilities
- compile-time constants
- presentation-only state mapping

Do not reject valid low-risk designs due to doctrinal overreach.

---

## 4. Anti-Corruption Layer (ACL)

### 4.1 ACL is Mandatory When

- native or external models do not match domain language
- the boundary carries state, side effects, async behavior, or unstable semantics
- translation, validation, caching, or error conversion is required

### 4.2 ACL is Usually Unnecessary When

- behavior is stable, pure, and stateless
- the code is purely computational
- there is no meaningful boundary risk

`replaceable` does not mean `abstract everything immediately`.

---

## 5. Interface Rules

Introduce explicit interfaces when:
- platform behavior differs
- resource lifetime is non-trivial
- ABI or binary stability matters
- the boundary is expected to change independently of the caller

Do not introduce speculative interfaces when the abstraction cost exceeds the boundary risk.

---

## 6. ADR Rules

### 6.1 ADR Triggers

Create or update an ADR when a decision affects:
- memory ownership strategy
- cross-platform loading strategy
- ABI or calling convention
- boundary partitioning
- long-lived interface placement

### 6.2 Conflict Check

Before adding a new ADR:
1. list relevant titles in `docs/adr/`
2. identify any conflict
3. either mark supersession clearly or escalate if ambiguity remains
4. link related ADRs in the new record

Producing an ADR without conflict review is a governance failure.

---

## 7. Build Boundary Addendum

Build-system wiring is part of architecture, not merely tooling.

Hard rules:
- a project may include headers from its own tree and explicitly approved shared layers only
- a project must **not** add a peer project's private directory to include-search settings
- a successful build does **not** legitimize a boundary violation
- if multiple projects need the same header, move it into a shared boundary layer with explicit ownership

Cross-project private include access is an architecture violation because it hides coupling and bypasses ownership boundaries.

---

## 8. Legacy and Refactor Interpretation

For legacy repos and large refactors:
- hidden historical coupling is a risk, not an excuse
- baseline instability should be surfaced explicitly
- boundary judgment should consider the canonical build environment, not random toolchain noise

If the current repo reality makes the boundary unclear, escalate with evidence instead of pretending the architecture is obvious.

---

## 9. Evidence Expectations

Acceptable architecture evidence includes:
- touched-layer list
- dependency path or include path inspection
- entrypoint/call-path summary
- before/after boundary diff
- statement of what remains intentionally unchanged

Do not claim "architecture-safe" without naming the evidence used.

---

## 10. Final Principle

> **Architecture prevents catastrophic mistakes, not ordinary progress.**
> **Use hard stops for hard violations; use escalation for real design ambiguity.**
