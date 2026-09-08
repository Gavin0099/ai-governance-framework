# C1 Gate 1 D5 countability amendment freeze

This directory freezes the owner-approved decision that the current internal
C1 Skill-funding experiment does not require a second external receipt after
mapping release.

The decision does not remove external anchoring from the evidence chain.
Event 7 (`external_chain_head_pinned`) remains proof-bearing and mandatory
after both scorer submissions and before event 8 (`mapping_released`). Event 8
remains mandatory in the local create-once chain and must validate against the
frozen mapping commitment. Only an additional event-9-style external anchor of
the final mapping-release bytes is not required for current C1 countability.

`d5_countability_amendment.py` is a pure countability calculator plus a
fail-closed admission overlay. The overlay consumes the already-passing base
admission terminal, verifies exact bindings and this resolved decision, and
never creates randomization.

This freeze is limited to the current internal Skill-funding decision. It does
not support external publication, a public benchmark, cross-team reliance, or
a claim that the mapping-release event or final chain head was externally
witnessed.

Execution authority remains closed. A separate owner authorization bound to a
reviewed admission commit is still required before randomization.
