# C++ Build Boundary Rule Pack

- Keep `AdditionalIncludeDirectories` scoped to the current project's own tree and explicitly approved shared layers only.
- Do not add a peer project's private source directory to include search paths, even if the build succeeds.
- Treat cross-project private header access as a boundary violation, not a convenience.
- If multiple projects require the same header, extract it into an explicit shared boundary component with clear ownership.
- Reject changes that justify hidden coupling with "the build passes" or equivalent reasoning.
