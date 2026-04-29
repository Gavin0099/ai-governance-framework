# C++ User-Space Safety Rules

## CPP_MUTEX_BARE_LOCK

**Category**: resource-safety
**Enforcement**: advisory (promote to hard_stop after 20 evaluations, FP-rate = 0.0)
**Files checked**: `.cpp`, `.cxx`, `.cc`, `.h`, `.hpp`

### What it checks

Any C++ source file that contains `.lock()` or `.unlock()` called as a
standalone statement expression (e.g., `m_mutex.lock();`).

### Why it matters

Bare `.lock()` / `.unlock()` pairs are not exception-safe.  If an exception
is thrown or an early `return` is taken between the `.lock()` and `.unlock()`
calls, the mutex is never released, causing a deadlock on the next acquisition.

RAII wrappers (`std::scoped_lock`, `std::lock_guard`, `std::unique_lock`)
guarantee the mutex is released when the wrapper goes out of scope, including
on exception and early-return paths.

### Accepted patterns

```cpp
// ✅ OK — RAII via scoped_lock (C++17)
std::scoped_lock lock(m_mutex);

// ✅ OK — RAII via lock_guard (C++11)
std::lock_guard<std::mutex> guard(m_mutex);

// ✅ OK — RAII via unique_lock (C++11, needed for condition variables)
std::unique_lock<std::mutex> lk(m_mutex);
```

### Violating patterns

```cpp
// ❌ VIOLATION — unlock not guaranteed on early return or exception
m_mutex.lock();
DoWork();
m_mutex.unlock();
```

### False positive guidance

`std::unique_lock` has `.lock()` and `.unlock()` methods for advanced
patterns (e.g., deferred lock, condition variable signalling).  If a
`unique_lock` is constructed first and its `.lock()` is called intentionally,
add a triage record with `type: FP` and `root_cause: context`.

---

## CPP_RAW_MEMORY_ALLOC

**Category**: resource-safety
**Enforcement**: advisory
**Files checked**: `.cpp`, `.cxx`, `.cc`

### What it checks

Any C++ implementation file that contains a `= new Type` or
`return new Type` raw allocation pattern.

### Why it matters

Raw `new` allocations require a matching `delete` or `delete[]` on every
exit path.  In the presence of exceptions, early returns, or complex control
flow, the matching `delete` is frequently omitted, causing memory leaks or
use-after-free defects.

Smart pointer factory functions transfer ownership to a RAII wrapper at the
point of allocation, eliminating the possibility of a leak.

### Accepted patterns

```cpp
// ✅ OK — unique_ptr takes ownership immediately
auto buf = std::make_unique<uint8_t[]>(size);

// ✅ OK — shared_ptr for shared ownership
auto device = std::make_shared<DeviceContext>(handle);

// ✅ OK — stack allocation (no heap, no delete needed)
std::vector<uint8_t> buffer(size);
```

### Violating patterns

```cpp
// ❌ VIOLATION — leaked on early return
uint8_t* pBuffer = new uint8_t[dwSize];
if (!ReadFile(...)) return FALSE;  // leak
delete[] pBuffer;

// ❌ VIOLATION — exception between new and delete
SomeType* p = new SomeType();
p->risky_operation();  // throws → p leaked
delete p;
```

### False positive guidance

Placement new (`new (buf) T`) is a valid low-level pattern.  If your code
uses placement new intentionally, add a triage record with `type: FP` and
`root_cause: placement_new`.

---

## CPP_REINTERPRET_CAST_CALLBACK

**Category**: type-safety
**Enforcement**: advisory
**Files checked**: `.cpp`, `.cxx`, `.cc`

### What it checks

Any C++ implementation file that contains `reinterpret_cast<`.

### Why it matters

`reinterpret_cast<>` bypasses the C++ type system entirely.  At callback
boundaries (WinAPI `LPARAM`/`WPARAM` parameters, COM `IUnknown`, C-style
function pointers), the pointer recovered via `reinterpret_cast` has no
compiler-enforced type relationship to the actual object.

If the callback is invoked with the wrong context value (wrong cast type,
stale pointer, race condition), dereferencing the result causes undefined
behaviour, crashes, or security vulnerabilities.

### Accepted patterns (with mandatory null-check)

```cpp
// ✅ OK — null-check before use, documented reasoning
CMyDialog* pDlg = reinterpret_cast<CMyDialog*>(lParamContext);
if (!pDlg) return FALSE;  // null-check mandatory
pDlg->OnEvent(lParam);

// ✅ Better — use magic/tag field to validate type before cast
if (ctx->magic != MY_MAGIC) return FALSE;
CMyDialog* pDlg = reinterpret_cast<CMyDialog*>(ctx->pDlg);
```

### Violating patterns

```cpp
// ❌ VIOLATION — no null-check, no type validation
CMyDialog* pDlg = reinterpret_cast<CMyDialog*>(lParamContext);
pDlg->OnEvent(lParam);  // crash if lParamContext is wrong
```

### False positive guidance

`reinterpret_cast` at WinAPI boundaries is often unavoidable (e.g.,
`GetWindowLongPtr` returns `LONG_PTR` which requires `reinterpret_cast` to
recover a pointer).  If the cast is validated by a null-check and the context
is well-controlled, add a triage record with `type: FP` and
`root_cause: winapi_boundary`.
