# USB Hub Firmware Architecture

- Update orchestration lives above transport-specific register writes
- ISR and deferred work boundaries must stay explicit
- Shared buffer ownership must be visible at module boundaries
