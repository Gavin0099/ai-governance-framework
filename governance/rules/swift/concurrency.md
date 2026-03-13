# Swift Concurrency Boundary

- UI-affecting state must respect the correct actor or main-thread boundary.
- Do not mix callback-style side effects and structured concurrency in ways that obscure ownership or cancellation.
- Task cancellation and error propagation must remain explicit across boundaries.
