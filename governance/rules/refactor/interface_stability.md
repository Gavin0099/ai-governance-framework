# Refactor Interface Stability Rule Pack

- Refactor work must preserve external contracts unless the task is explicitly reclassified as a behavior or interface change.
- Public method signatures, callback semantics, error surfaces, and observable ordering must remain stable or be backed by explicit compatibility evidence.
- If compatibility depends on adapter, contract, or characterization tests, those tests are part of the required refactor evidence, not optional documentation.
