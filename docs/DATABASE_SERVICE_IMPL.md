# Database Service — 實作規格

> **LANG = C++ | LEVEL = L2 | SCOPE = feature**
>
> ⬆️ **LEVEL 升級說明（AGENT.md §1）**：本服務涉及身份驗證（LDAP）、存取控制、資料完整性（audit log）
> 屬核心 domain + 安全邊界，依治理規則強制升級 L1 → L2。
> L2 要求：全量 unit + contract + integration tests，人可讀驗收標準，≥2 平台 native interop 測試。
>
> **Bounded Context**: `DatabaseService` 負責統一身份驗證（LDAP）、操作授權、DB 讀寫、審計日誌。
> **不負責**: TLS handshake 細節、dongle 操作、簽章運算、網域帳號管理。

---

## 1. 目錄結構

```
database_service/
├── DatabaseService.sln
├── setup.bat                         ← 沿用 etoken_server 模式
├── DatabaseService/
│   ├── DatabaseService.vcxproj
│   ├── DatabaseService.vcxproj.filters
│   ├── main.cpp                      ← 入口，讀 ini 啟動 CDbService
│   ├── Global.h/cpp                  ← 全域設定（IP / Port / cert 路徑 / LDAP hosts）
│   ├── version.h
│   │
│   ├── DbServiceDefine.h             ← 協議 opcode、請求/回應結構
│   │
│   ├── Service/
│   │   ├── DbService.h/cpp           ← TcpServer 主體，accept → DbSession
│   │   └── DbSession.h/cpp           ← 單一連線的 Session 生命週期管理
│   │
│   ├── Handler/
│   │   ├── DbSessionHandler.h/cpp        ← 主迴圈 + dispatch
│   │   ├── DbSessionHandler_Auth.cpp     ← DBFO_LOGIN / DBFO_FINISH
│   │   ├── DbSessionHandler_Key.cpp      ← DBFO_QUERY_KEY / NEW / BAN / RESET / SIGN_RESOLVE
│   │   ├── DbSessionHandler_Token.cpp    ← DBFO_UPDATE_TOKEN / GET_TOKEN_INFO
│   │   ├── DbSessionHandler_Pc.cpp       ← DBFO_PC_LOGIN / DBFO_PC_LOGOUT
│   │   └── DbSessionHandler_Log.cpp      ← DBFO_LOG_WRITE / DBFO_LOG_QUERY / DBFO_LOG_ARCHIVE / DBFO_AUDIT_READ
│   │
│   ├── Auth/
│   │   ├── LdapAuth.h/cpp            ← 提取自 TcpClientCmd_ldap.cpp，純函式
│   │   └── PermissionGuard.h/cpp     ← client_type × opcode × stUserAuthority 三層許可
│   │
│   └── AuditLog/
│       ├── AuditLogger.h/cpp         ← 所有操作寫入 DB audit_log + DbgPrint
│       └── AuditDefine.h             ← AuditEntry struct、AuditEvent enum
│
└── vs_project_settings/              ← 沿用既有 .props
```

---

## 2. 協議定義（`DbServiceDefine.h`）

```cpp
#pragma once
#include <cstdint>
#include <string>

// ── 版本 ─────────────────────────────────────────────
#define DB_SERVICE_FLOW_VERSION 1

// ── 呼叫端類型 ────────────────────────────────────────
enum DB_CLIENT_TYPE : uint8_t
{
    DBCT_NONE           = 0,
    DBCT_ETOKEN_SERVER  = 1,   // eToken Server：key / token / sign / log_write
    DBCT_LOG_SERVER     = 2,   // Log Server：log_read only
};

// ── opcode ────────────────────────────────────────────
enum DB_FLOW_OPCODE : uint8_t
{
    DBFO_NONE           = 0,
    // 認證
    DBFO_LOGIN          = 1,
    // Key 操作
    DBFO_QUERY_KEY      = 2,
    DBFO_NEW_KEY        = 3,
    DBFO_BAN_KEY        = 4,
    DBFO_RESET_KEY      = 5,
    DBFO_SIGN_RESOLVE   = 6,   // 取得簽章所需 private key ID
    // Token 操作
    DBFO_UPDATE_TOKEN   = 7,
    DBFO_GET_TOKEN_INFO = 8,
    // PC 操作
    DBFO_PC_LOGIN       = 9,
    DBFO_PC_LOGOUT      = 10,
    // Log
    DBFO_LOG_WRITE      = 11,  // 寫入 operation_log（何人何時對何物做什麼）
    DBFO_AUDIT_READ     = 12,  // 安全審計讀取（Log Server 專用）
    DBFO_LOG_QUERY      = 13,  // 查詢 operation_log（Log Server 專用）
    DBFO_LOG_ARCHIVE    = 14,  // 觸發封存作業（將舊延記錄移至 etokensystem_archive）
    DBFO_FINISH         = 0xFF
};

// ── 行為常數 ──────────────────────────────────────────
// 決策 P1-1：Login 第二段等待獨立 timeout，非全域 CMD_WAITING_TIME
#define DB_SERVICE_LOGIN_TIMEOUT  30000  // ms

// 決策 P1-6：DBFO_AUDIT_READ 服務端最大查詢範圍（防全表掃描）
#define DB_AUDIT_MAX_QUERY_DAYS    90    // 超過此範圍回 STATUS_FAIL "RANGE_EXCEEDED"

// operation_log 封存閨値（決策 L3-1）
#define LOG_ARCHIVE_THRESHOLD_DAYS 180  // 超過 180 天的記錄移至 etokensystem_archive

// operation_log 單次查詢最大頁大小（防大結果集塀積內存）
#define LOG_QUERY_MAX_PAGE_SIZE    200

// ── 權限對照表 ────────────────────────────────────────
// DBCT_ETOKEN_SERVER → LOGIN, QUERY_KEY, NEW_KEY, BAN_KEY, RESET_KEY,
//                      SIGN_RESOLVE, UPDATE_TOKEN, GET_TOKEN_INFO,
//                      PC_LOGIN, PC_LOGOUT, LOG_WRITE
//                      ⚠️ 禁止：AUDIT_READ, LOG_QUERY, LOG_ARCHIVE
// DBCT_LOG_SERVER    → LOGIN, AUDIT_READ, LOG_QUERY, LOG_ARCHIVE
//                      ⚠️ 禁止：所有業務 opcode（KEY/TOKEN/PC/LOG_WRITE）
```

---

## 3. 協議封包格式

沿用既有 `CTcpSsl::SendCmd / ReceiveCmdEx`，封包格式不變：

```
[1 byte: opcode] [1 byte: STATUS_OPCODE] [N bytes: payload string]
```

### DBFO_LOGIN payload

```
請求 (STATUS_START):
  "<DB_SERVICE_FLOW_VERSION> <DB_CLIENT_TYPE> <domain>\<user>"

回應 (STATUS_NEXT):
  服務端確認版本 / 類型，等待密碼

請求 (STATUS_NEXT):
  "<password>"

回應 (STATUS_OK / STATUS_FAIL):
  OK → 已通過 LDAP + DB 身份驗證
  FAIL → "LDAP_FAIL" | "DB_FAIL" | "PERM_DENIED"
```

### 一般操作 payload

```
請求 (STATUS_START):
  "<JSON 或 space-separated 參數>"

回應 (STATUS_OK):
  "<JSON 或 space-separated 結果>"

回應 (STATUS_FAIL):
  "<錯誤描述字串>"
```

> **Payload 序列化採 space-separated 基本型別** （與現有 etoken_server 協議一致，避免引入額外依賴）。
> 複雜回傳（如 key group list）以換行 `\n` 分隔多筆記錄，欄位以空格分隔。

---

## 4. 核心類別介面

### 4.1 `CDbSessionHandler`（`Handler/DbSessionHandler.h`）

```cpp
#pragma once
#include "../Auth/LdapAuth.h"
#include "../Auth/PermissionGuard.h"
#include "../AuditLog/AuditLogger.h"
#include "../DbServiceDefine.h"
#include "Database/GlMySql.h"   // 沿用既有
#include "TcpSsl.h"              // 沿用既有 tcp_engine
#include <string>

namespace gli
{
// 決策 P0-1：不繼承 CGlMySql。改以 has-a 持有獨立 _mainDb
// 理由：若繼承，CAuditLogger 與 DoKey/Token/Pc 共用同一連線，
//       主操作 rollback 會沉默審計寫入，違反「失敗也要留紀錄」原則。
class CDbSessionHandler : public CTcpSsl
{
public:
    CDbSessionHandler() = default;
    ~CDbSessionHandler() override;

    // copy / move — 全刪，Session 不可複製或移動
    CDbSessionHandler(const CDbSessionHandler &)            = delete;
    CDbSessionHandler &operator=(const CDbSessionHandler &) = delete;
    CDbSessionHandler(CDbSessionHandler &&)                 = delete;
    CDbSessionHandler &operator=(CDbSessionHandler &&)      = delete;

    // 主迴圈（由 DbSession thread 調用）
    void Run(SSL_CTX *ctx);

private:
    // ── Auth ──────────────────────────────────────────
    bool DoLogin();

    // ── Key ───────────────────────────────────────────
    bool DoQueryKey();
    bool DoNewKey();
    bool DoBanKey();
    bool DoResetKey();
    bool DoSignResolve();

    // ── Token ─────────────────────────────────────────
    bool DoUpdateToken();
    bool DoGetTokenInfo();

    // ── Pc ────────────────────────────────────────────
    bool DoPcLogin();
    bool DoPcLogout();

    // ── Log ───────────────────────────────────────────
    bool DoLogWrite();    // DBFO_LOG_WRITE：寫入 operation_log
    bool DoLogQuery();    // DBFO_LOG_QUERY：查詢 operation_log
    bool DoLogArchive();  // DBFO_LOG_ARCHIVE：觸發封存
    bool DoAuditRead();   // DBFO_AUDIT_READ：安全審計讀取（Log Server only）

    // ── 共用 helpers ──────────────────────────────────
    // 送回 STATUS_OK/FAIL，同時寫入 audit log
    void ReplyAndAudit(DB_FLOW_OPCODE op, bool ok,
                       const std::string &payload,
                       const std::string &detail);
    // 送回 STATUS_FAIL，同時寫 audit log
    void ReplyFail(DB_FLOW_OPCODE op, const std::string &reason);

    // ── Session 狀態 ──────────────────────────────────
    bool            _loggedIn   = false;
    DB_CLIENT_TYPE  _clientType = DBCT_NONE;
    std::string     _sessionUser;   // "domain\user"
    stUserAuthority _auth{};        // DB 查回的使用者權限

    // ── DB 連線（決策 P0-1 + P0-2）───────────────────
    // _mainDb : 業務操作，per-dispatch ConnectDb/DisconnectDb
    //           ConnectDb() 內部會先呼叫 DisconnectDb()，重複調用安全
    // _audit  : 內部持有獨立 CGlMySql 實例，確保主操作失敗時審計仍可寫入
    CGlMySql        _mainDb;
    CAuditLogger    _audit;
};
} // namespace gli
```

---

### 4.2 `CLdapAuth`（`Auth/LdapAuth.h`）

提取自 `TcpClientCmd_ldap.cpp`，保持相同邏輯，改為可獨立測試的純函式類別。

```cpp
#pragma once
#include <array>
#include <string>

namespace gli
{
class CLdapAuth
{
public:
    // 設定 LDAP server 列表（至少 1 台，預設嘗試順序）
    void SetHosts(const std::array<std::string, 2> &hosts);

    // 驗證 domain\user + password。TEST_MODE 下永遠回 true。
    // @param sDomainUser  格式："DOMAIN\username"
    // @param sPassword
    // @return true = 驗證通過
    bool Validate(const std::string &sDomainUser, const std::string &sPassword) const;

private:
    std::array<std::string, 2> _hosts =
        {"gli-dc161.genesyslogic.com.tw", "gli-dc162.genesyslogic.com.tw"};
};
} // namespace gli
```

---

### 4.3 `CPermissionGuard`（`Auth/PermissionGuard.h`）

```cpp
#pragma once
#include "../DbServiceDefine.h"
#include "Database/GlMySql.h"

namespace gli
{
class CPermissionGuard
{
public:
    // 第一層：client 類型是否有權執行此 opcode
    static bool IsClientAllowed(DB_CLIENT_TYPE type, DB_FLOW_OPCODE op);

    // 第二層：使用者 DB 權限（stUserAuthority）是否滿足此 opcode
    // 例如：DBFO_BAN_KEY 需要 auth.isBan == true
    static bool HasUserPermission(const stUserAuthority &auth, DB_FLOW_OPCODE op);
};
} // namespace gli
```

**Permission table 實作（`PermissionGuard.cpp`）**:

```cpp
bool CPermissionGuard::IsClientAllowed(DB_CLIENT_TYPE type, DB_FLOW_OPCODE op)
{
    if (op == DBFO_LOGIN || op == DBFO_FINISH) return true;

    switch (type)
    {
    case DBCT_ETOKEN_SERVER:
        // LOG_QUERY / LOG_ARCHIVE 也屬 Log Server 專用，一律封鎖
        return op != DBFO_AUDIT_READ
            && op != DBFO_LOG_QUERY
            && op != DBFO_LOG_ARCHIVE;
    case DBCT_LOG_SERVER:
        // Log Server 僅允許三個讀取 / 封存 opcode
        return op == DBFO_AUDIT_READ
            || op == DBFO_LOG_QUERY
            || op == DBFO_LOG_ARCHIVE;
    default:
        return false;
    }
}

bool CPermissionGuard::HasUserPermission(const stUserAuthority &auth, DB_FLOW_OPCODE op)
{
    switch (op)
    {
    // 欄位名稱對應 etokensystem.authority 表：query / rename / sign / ban / reset
    case DBFO_QUERY_KEY:      return auth.isQuery;
    case DBFO_NEW_KEY:        return auth.isQuery;   // 能查才能申請
    case DBFO_BAN_KEY:        return auth.isBan;
    case DBFO_RESET_KEY:      return auth.isReset;
    case DBFO_SIGN_RESOLVE:   return auth.isSign;
    // server-to-server 操作明確 whitelist（決策 P1-3：fail-closed）
    // 未來新增 opcode 必須在此明確列出，否則預設拒絕
    case DBFO_UPDATE_TOKEN:   return true;
    case DBFO_GET_TOKEN_INFO: return true;
    case DBFO_PC_LOGIN:       return true;
    case DBFO_PC_LOGOUT:      return true;
    case DBFO_LOG_WRITE:      return true;
    case DBFO_AUDIT_READ:     return true;
    case DBFO_LOG_QUERY:      return auth.isLogQueryAll;  // authority.log_query_all（決策 L3-15）
    case DBFO_LOG_ARCHIVE:    return true;
    default:                  return false;  // ⚠️ fail-closed：未知 opcode 一律拒絕
    }
}
```

---

### 4.4 `CAuditLogger`（`AuditLog/AuditLogger.h`）

```cpp
#pragma once
#include "AuditDefine.h"
#include "Database/GlMySql.h"
#include <string>
#include <vector>

namespace gli
{
class CAuditLogger
{
public:
    // 決策 P0-1：CAuditLogger 持有獨立 CGlMySql 實例（非 shared pointer / 非繼承）
    // 理由：主操作 rollback 或 DisconnectDb 不能影響審計寫入
    // 每次 Write() 內部執行 ConnectDb → INSERT → DisconnectDb
    void Init(const std::string &sMySqlIp,
              uint16_t uMySqlPort,
              const std::string &sUser,
              DB_CLIENT_TYPE clientType);

    // 寫入一筆 security audit 記錄（同步，獨立連線）
    // 決策 P1-5：回傳 bool；失敗時 DbgPrint 記錄錯誤，業務操作繼續（Option B）
    // 理由：可用性優先於完整審計；DbgPrint 輸出本身即為備用稽核紀錄
    //       若日後引入合規要求，可升級為 Option C（審計失敗則 rollback 主操作）
    // DoLogin 失敗時也應呼叫，確保任何操作嘗試都有紀錄
    bool Write(DB_FLOW_OPCODE op, bool bSuccess, const std::string &sDetail);

    // Log Server 讀取介面（DBFO_AUDIT_READ 專用）
    // 決策 P2-2：防競性重複驗證——Handler 層已做第一道 gate，
    //   此處再次檢查是防競性設計，防止未來直接呼叫的内部工具/測試甲湞過 Handler 限制。
    //   如果內部工具需要超過 90 天，必須明確决策并修改這裡的常數。
    bool Read(const std::string &sFrom,   // "YYYY-MM-DD HH:MM:SS"
              const std::string &sTo,
              uint8_t filterOpcode,        // 0 = all
              std::vector<AuditEntry> &out) const;

private:
    CGlMySql       _db;             // 獨立實例，不與 session _mainDb 共用
    std::string    _sUser;
    DB_CLIENT_TYPE _clientType = DBCT_NONE;
};
} // namespace gli
```

---

### 4.5 `AuditEntry`（`AuditLog/AuditDefine.h`）

```cpp
#pragma once
#include "../DbServiceDefine.h"
#include <cstdint>
#include <string>

namespace gli
{
struct AuditEntry
{
    uint64_t       uIndex      = 0;
    std::string    sTimestamp;          // "YYYY-MM-DD HH:MM:SS"
    std::string    sUser;               // "domain\user"
    DB_CLIENT_TYPE clientType  = DBCT_NONE;
    DB_FLOW_OPCODE opcode      = DBFO_NONE;
    bool           bSuccess    = false;
    std::string    sDetail;             // 例如 keyGroupIndex=3, tokenSn=ABC123
};
} // namespace gli
```

---

## 5. 主迴圈邏輯（`DbSessionHandler.cpp`）

```cpp
void CDbSessionHandler::Run(SSL_CTX *ctx)
{
    // 1. TLS 握手
    if (!NewSsl(ctx) || !PerformSslAccept(CMD_WAITING_TIME))
    {
        DbgPrint(XD_ERR, "[DbSession] TLS accept failed.");
        return;
    }

    // 2. 強制第一個 opcode 必須是 DBFO_LOGIN
    if (!DoLogin()) return;

    // 3. 主迴圈
    while (true)
    {
        uint8_t uOpcode = 0;
        STATUS_OPCODE eStatus = STATUS_NONE;
        if (!ReceiveCmd(uOpcode, eStatus, CMD_WAITING_TIME)) break;

        const auto op = static_cast<DB_FLOW_OPCODE>(uOpcode);
        if (op == DBFO_FINISH) break;

        // 第一層：client 類型許可
        if (!CPermissionGuard::IsClientAllowed(_clientType, op))
        {
            ReplyFail(op, "CLIENT_PERM_DENIED");
            continue;
        }

        // 第二層：使用者 DB 權限
        if (!CPermissionGuard::HasUserPermission(_auth, op))
        {
            ReplyFail(op, "USER_PERM_DENIED");
            continue;
        }

        // 決策 P0-2：per-dispatch 重新連線
        // 理由：CGlMySql 無自動重連（確認自 TcpDongleSsl.cpp:205、TcpDongleManage.cpp:252）
        // ConnectDb() 底層為 ODBC SQLDriverConnect()（TCP + MySQL auth），LAN RTT 約 1-5 ms
        // AddLogToDb() 僅為 DbgPrint placeholder，無額外 DB 開銷
        //
        // ⚠️ 實作注意：GlMySql.cpp:60 SQLSetConnectAttr(SQL_LOGIN_TIMEOUT, nullptr, 0)
        //    nullptr 對 SQLUINTEGER 型別屬誤用，可能造成無限等待
        //    DatabaseService 實作時應修正為具體秒數（建議 5 秒）：
        //    SQLSetConnectAttr(m_dbc, SQL_LOGIN_TIMEOUT, (SQLPOINTER)5, 0)
        //
        // 效能 gate（在 Phase D 壓力測試前必須量測）：
        //    P99 ConnectDb() < 10 ms（LAN 環境）
        //    若 SIGN_RESOLVE 成為瓶頸，Phase E 可為 server-to-server opcode 引入連線重用
        if (!_mainDb.ConnectDb())
        {
            ReplyFail(op, "DB_CONNECT_FAIL");
            continue;
        }

        // 派發
        bool ok = false;
        switch (op)
        {
        case DBFO_QUERY_KEY:      ok = DoQueryKey();      break;
        case DBFO_NEW_KEY:        ok = DoNewKey();        break;
        case DBFO_BAN_KEY:        ok = DoBanKey();        break;
        case DBFO_RESET_KEY:      ok = DoResetKey();      break;
        case DBFO_SIGN_RESOLVE:   ok = DoSignResolve();   break;
        case DBFO_UPDATE_TOKEN:   ok = DoUpdateToken();   break;
        case DBFO_GET_TOKEN_INFO: ok = DoGetTokenInfo();  break;
        case DBFO_PC_LOGIN:       ok = DoPcLogin();       break;
        case DBFO_PC_LOGOUT:      ok = DoPcLogout();      break;
        case DBFO_LOG_WRITE:      ok = DoLogWrite();      break;
        case DBFO_AUDIT_READ:     ok = DoAuditRead();     break;
        case DBFO_LOG_QUERY:      ok = DoLogQuery();      break;
        case DBFO_LOG_ARCHIVE:    ok = DoLogArchive();    break;
        default:
            ReplyFail(op, "UNKNOWN_OPCODE");
            break;
        }

        _mainDb.DisconnectDb();
        // audit 由各 Do*() 內部透過 ReplyAndAudit() 寫入（_audit 獨立連線，不受影響）
    }

    // Session 結束
    _audit.Write(DBFO_FINISH, true, "session_end");
    Disconnect();
}
```

---

## 6. 各 Handler 實作概要

### DBFO_LOGIN（`DbSessionHandler_Auth.cpp`）

```
收: STATUS_START  "<version> <client_type> <domain\user>"
送: STATUS_NEXT   (等待密碼)
收: STATUS_NEXT   "<password>"

驗證流程:
  1. 解析 version / client_type / domainUser
     → 格式錯誤 → STATUS_FAIL "PARSE_ERROR"

     ① 立即 _audit.Init(g_config.sMySqlIp, g_config.uMySqlPort,
                              domainUser, clientType)
     理由：後續任何失敗路徑均需呼叫 _audit.Write()，
             Init() 必須在所有可能失敗的步驟之前執行。
             DB 此時尚未連線，但 Write() 失敗 = Option B（DbgPrint、業務繼續），行為一致。

  2. 若不符 DB_SERVICE_FLOW_VERSION → STATUS_FAIL "VERSION_MISMATCH"
     → _audit.Write(DBFO_LOGIN, false, "VERSION_MISMATCH")

  3. 送 STATUS_NEXT，改用 DB_SERVICE_LOGIN_TIMEOUT (30000ms) 等待密碼
     （決策 P1-1）

  4. CLdapAuth::Validate(domainUser, password)
     → 失敗 → _audit.Write(DBFO_LOGIN, false, "LDAP_FAIL")
              → STATUS_FAIL "LDAP_FAIL"

  5. _mainDb.ConnectDb() → _mainDb.GetAuthority(domain, user, _auth)
     → ConnectDb 失敗 → _audit.Write(..., "DB_CONNECT_FAIL") → STATUS_FAIL
     → GetAuthority 失敗 → _audit.Write(..., "DB_AUTH_FAIL")    → STATUS_FAIL

  6. _mainDb.DisconnectDb()（決策 P0-2：Login 後不保留連線）

  7. CPermissionGuard::IsClientAllowed(client_type, DBFO_LOGIN)
     → 失敗 → _audit.Write(..., "PERM_DENIED") → STATUS_FAIL

  8. _loggedIn = true
  9. 送: STATUS_OK → _audit.Write(DBFO_LOGIN, true, "")

注：_audit 在步驟 1 完成 Init()，之後所有失敗路徑均已可寫入。
     Write() 連線失敗時 = Option B：DbgPrint + 回傳 false，不阻断後續流程。
```

---

### DBFO_QUERY_KEY（`DbSessionHandler_Key.cpp`）

```
收: STATUS_START  "<key_type> <status_filter> <start_index> <max_count>"
    -- key_type: keytype.id (0=RSA, 3=ECDSA)
    -- status_filter: keygroupstatus.id (0=Unused, 1=Used, 2=Banned)
    → 呼叫 CGlMySql::GetKeyGroupList()
       SQL: SELECT `index`, `label`, `status`, `renametime`
            FROM keygroup WHERE type=? AND status=?
            ORDER BY `index` LIMIT ?,?
送: STATUS_OK     "<count>\n<index> <label> <status> <renametime>\n..."
  | STATUS_FAIL   "<reason>"
```

---

### DBFO_NEW_KEY

```
收: STATUS_START  "<key_type> <label>"
    -- key_type: 0=RSA, 3=ECDSA（對應 keytype.id）
    → 呼叫 CGlMySql::NewKeyGroup()
       -- ⚠️ 非 INSERT：系統需預先在 DB 建立 status=0(Unused) 的 keygroup 行；
       --    NewKeyGroup 從中「認領」一個，SQL 流程如下：
       --
       --  1. START TRANSACTION
       --  2. SELECT `index` INTO @target_index
       --        FROM keygroup WHERE status=0 AND type=?
       --        ORDER BY `index` ASC LIMIT 1 FOR UPDATE
       --  3. UPDATE keygroup AS kg
       --        INNER JOIN tokengroup AS tg ON kg.tokengroup = tg.index
       --        INNER JOIN token      AS t  ON tg.index = t.group
       --        SET kg.label=?, kg.status=1,
       --            kg.renametime=CURRENT_TIMESTAMP, kg.lasttime=CURRENT_TIMESTAMP,
       --            t.lasttime=CURRENT_TIMESTAMP
       --        WHERE kg.index = @target_index
       --  4. SELECT @target_index  → uKeyGroupIndex
       --  5. COMMIT
送: STATUS_OK     "<new_key_group_index>"   -- 被認領的 keygroup.index
  | STATUS_FAIL   "<reason>"               -- 若無 Unused row 可認領則失敗
```

---

### DBFO_BAN_KEY

```
收: STATUS_START  "<key_group_index>"
    → 呼叫 CGlMySql::BanKeyGroup()
       SQL: UPDATE keygroup SET status=2 WHERE `index`=?  -- 2=Banned
送: STATUS_OK
  | STATUS_FAIL
```

---

### DBFO_RESET_KEY

```
收: STATUS_START  "<key_group_index>"
    → 呼叫 CGlMySql::ResetKeyGroup()
       SQL: UPDATE keygroup SET status=0 WHERE `index`=?  -- 0=Unused
送: STATUS_OK
  | STATUS_FAIL
```

---

### DBFO_SIGN_RESOLVE

```
收: STATUS_START  "<key_group_index>"
    → 呼叫 CGlMySql::GetPrivateKeyId(keyGroupIndex)
       SQL: SELECT `id` FROM `key`
            WHERE `group` = {keyGroupIndex} AND `class` = 3
            LIMIT 1
       -- keyclass.id=3 = 'private'（eTPkcs11 CKO_PRIVATE_KEY）
       -- key.id 為 VARCHAR(64)，即 PKCS#11 物件的 CKA_ID / label
    → 呼叫 CGlMySql::UpdateKeyGroupLastTime()
       SQL: UPDATE `keygroup` SET `lasttime` = CURRENT_TIMESTAMP
            WHERE `index` = {keyGroupIndex}
送: STATUS_OK     "<private_key_id>"   -- key.id VARCHAR(64)
  | STATUS_FAIL
```

---

### DBFO_UPDATE_TOKEN（`DbSessionHandler_Token.cpp`）

```
收: STATUS_START  "<token_serialnumber> <new_status> [pc_name]"
    -- token_serialnumber 對應 token.serialnumber (VARCHAR 10)
    -- new_status: tokenstatus.id (0=Offline, 1=Online, 2=Banned)
    → 若 pc_name 存在 → CGlMySql::UpdateTokenLocation()
       (更新 tokengroup.pc；注意 tokengroup↔pc FK 已移除，pc=0 表示無關聯)
    → CGlMySql::UpdateTokenStatus()
       SQL: UPDATE token SET status=? WHERE serialnumber=?
送: STATUS_OK
  | STATUS_FAIL
```

---

### DBFO_GET_TOKEN_INFO

```
收: STATUS_START  "<token_serialnumber>"
    -- 對應 token.serialnumber (VARCHAR 10)
    → CGlMySql::GetTokenInfoEx()
       SQL: SELECT t.label, t.status, p.name
            FROM token t
            LEFT JOIN tokengroup tg ON tg.index = t.group
            LEFT JOIN pc p ON p.index = tg.pc
            WHERE t.serialnumber = ?
送: STATUS_OK     "<label> <status> <pc_name>"
  | STATUS_FAIL
```

---

### DBFO_PC_LOGIN（`DbSessionHandler_Pc.cpp`）

```
收: STATUS_START  "<pc_name> <ip> <port>"
    → CGlMySql::GetPcExist()  -- SELECT index FROM pc WHERE name=?
    → 存在 → CGlMySql::UpdatePcInfo()
               SQL: UPDATE pc SET ip=?, port=? WHERE name=?
             CGlMySql::UpdatePcLoginTime()
               SQL: UPDATE pc SET logintime=CURRENT_TIMESTAMP WHERE name=?
    → 不存在 → CGlMySql::AddPcInfo()
                SQL: INSERT INTO pc(ip,port,name) VALUES(?,?,?)
               CGlMySql::UpdatePcLoginTime()
    -- pc 表欄位（ALTER 後）：index, ip, port, name, remark, logintime, logouttime
    -- tokengroup↔pc FK 已移除；pc 登入不再需要級聯更新 tokengroup
送: STATUS_OK
  | STATUS_FAIL
```

---

### DBFO_PC_LOGOUT

```
收: STATUS_START  "<pc_name>"
    → CGlMySql::UpdatePcLogoutTime()
       SQL: UPDATE pc SET logouttime=CURRENT_TIMESTAMP WHERE name=?
送: STATUS_OK
  | STATUS_FAIL
```

---

### DBFO_LOG_WRITE（`DbSessionHandler_Log.cpp`）

> 取代前身 `DBFO_EVENT_LOG`，opcode byte 值不變（11），展開為結構化 JSON payload。
> 記錄「何人 / 何時 / 對何物 / 做什麼 / 結果」寫入 `operation_log` 表。
> `user` / `ts` / `obj_label` 全部由 DatabaseService 自行填入，eToken Server **不傳送**。

```
收: STATUS_START  JSON:
    {
      "action":   "SIGN_REQUEST",  // 動詞字串，規範見 §13.2
      "obj_type": "KEY",           // KEY | TOKEN | PC | SESSION
      "obj_id":   "3",             // key_group_index | token_serialnumber | pc_name
      "result":   1,               // 1=success, 0=fail
      "detail":   "key_id=abc123"  // 補充資訊，可空字串
    }
    決策 L3-2：payload 改用 JSON（obj_id 等欄位可含特殊字元）
    決策 L3-6：obj_label 移除出 payload（防偽造），由 DatabaseService 查 DB 填入：
      KEY     → SELECT label FROM keygroup WHERE `index` = CAST(obj_id AS UNSIGNED)
      TOKEN   → SELECT label FROM token    WHERE serialnumber = obj_id
      PC      → label = obj_id（pc.name 即 label，不額外查）
      SESSION → obj_label = NULL
    user / ts 由 DatabaseService 從 _sessionUser / CURRENT_TIMESTAMP(3) 自動填入
送: STATUS_OK
  | STATUS_FAIL  "PARSE_ERROR" | "DB_FAIL"
```

---

### DBFO_LOG_QUERY（Log Server 專用）

```
收: STATUS_START  JSON:
    {
      "filter": {
        "user":           "DOMAIN\\john",     // 可省略
        "obj_label_like": "ProjectAlpha",    // FULLTEXT MATCH; 可省略
                                              // ⚠️ 決策 P1-4：
                                              //    obj_label_like + include_archive:true 不支援
                                              //    → STATUS_FAIL "FEATURE_NOT_SUPPORTED"
        "action":         "SIGN_REQUEST",    // 可省略
        "obj_type":       "KEY",             // 可省略
        "result":         1,                 // 1 | 0 | null=不限
        "from_ts":  "2026-01-01T00:00:00",   // 決策 P1-6：服務端驗證範圍
        "to_ts":    "2026-03-01T00:00:00"
      },
      "page":            1,
      "page_size":       50,               // 上限 LOG_QUERY_MAX_PAGE_SIZE
      "include_archive": false             // true 則同時查 etokensystem_archive
                                           // ⚠️ true 時 total_matched 固定回傳 -1（決策 P1-2）
    }

    驗證流程：
    1. obj_label_like 存在 AND include_archive=true
       → STATUS_FAIL "FEATURE_NOT_SUPPORTED"
       （FULLTEXT 搜尋無法跨 UNION ALL 兩張表）
    2. page_size > LOG_QUERY_MAX_PAGE_SIZE
       → STATUS_FAIL "PAGE_SIZE_EXCEEDED"

送: STATUS_OK  JSON:
    {
      "total_matched": 523,   // include_archive=false → 精確 COUNT(*)
                              // include_archive=true  → 固定 -1（不支援跨表 COUNT）
      "page":          1,
      "page_size":     50,
      "data": [
        { "id": 1001, "ts": "2026-01-15T10:23:44.123",
          "user": "DOMAIN\\john", "action": "SIGN_REQUEST",
          "obj_type": "KEY", "obj_id": "3",
          "obj_label": "ProjectAlpha_RSA2048",
          "result": 1, "detail": "" }
      ]
    }
  | STATUS_FAIL  "RANGE_EXCEEDED" | "PAGE_SIZE_EXCEEDED" | "FEATURE_NOT_SUPPORTED"
               | "PARSE_ERROR" | "DB_FAIL"
```

---

### DBFO_LOG_ARCHIVE（Log Server 專用）

```
收: STATUS_START  JSON:
    {
      "dry_run": false,           // true 則僅回傳預計移動筆數，不實際移動
      "threshold_days": 180       // 可覆寫 LOG_ARCHIVE_THRESHOLD_DAYS
    }

    決策 P0-2：使用 id-range 批次，避免 race condition
    ──────────────────────────────────────────────────
    跨 DB（etokensystem → etokensystem_archive）在同一 MySQL instance 的同一連線上
    InnoDB 支援統一 transaction，不需要 LOCK TABLES。
    新寫入記錄的 id > batch_max_id 且 ts ≥ threshold，故不干擾封存批次。

    每批次 SQL（同一 transaction 內）：
    ① SET @min_id = NULL, @max_id = NULL;
       SELECT MIN(id), MAX(id) INTO @min_id, @max_id
         FROM (SELECT id FROM etokensystem.operation_log
               WHERE ts < {threshold} ORDER BY id LIMIT 5000) t;
       -- 若 @min_id IS NULL → 無剩餘記錄，封存完成

    ② INSERT INTO etokensystem_archive.operation_log
         SELECT * FROM etokensystem.operation_log
         WHERE id BETWEEN @min_id AND @max_id
           AND ts < {threshold};

    ③ DELETE FROM etokensystem.operation_log
         WHERE id BETWEEN @min_id AND @max_id
           AND ts < {threshold};

    ④ COMMIT — 重複 ① 直到 @min_id IS NULL

送: STATUS_OK  JSON: { "moved": 12543, "dry_run": false }
  | STATUS_FAIL  "ARCHIVE_PARTIAL" | "DB_FAIL"
```

---

### DBFO_AUDIT_READ（Log Server 專用）

```
收: STATUS_START  "<from_ts> <to_ts> <filter_opcode>"
    from_ts / to_ts 格式："YYYY-MM-DD HH:MM:SS"

    驗證流程（決策 P1-6）：
    1. 解析 from_ts / to_ts → 格式錯誤 → STATUS_FAIL "INVALID_TIMESTAMP"
    2. (to_ts - from_ts) > DB_AUDIT_MAX_QUERY_DAYS 天 → STATUS_FAIL "RANGE_EXCEEDED"
       說明：90 天上限防止全表掃描（audit_log 無上限可能有數百萬筆）
    3. CAuditLogger::Read()（查 audit_log 表，WHERE timestamp BETWEEN from_ts AND to_ts）
       filter_opcode == 0 → 不過濾；否則 AND opcode = filter_opcode

送: STATUS_OK     "<count>\n<index> <timestamp> <user> <client_type> <opcode> <success> <detail>\n..."
  | STATUS_FAIL   "INVALID_TIMESTAMP" | "RANGE_EXCEEDED" | "DB_FAIL"
```

---

## 7. DB Schema 新增

> **注意：以下僅列出 DatabaseService 需要新建的表。**
> 現有表（`keygroup`, `key`, `keyclass`, `keytype`, `token`, `tokengroup`,
> `tokenstatus`, `tokengroupstatus`, `pc`, `user`, `authority`）已存在，
> DatabaseService 直接讀寫，不重建。
>
> **現有 schema 關鍵摘要（實作時參考）：**
> - `keygroup.index` — PK（INTEGER UNSIGNED），非 `id`
> - `key.id` — VARCHAR(64)，PKCS#11 object id（CKA_ID），是 SIGN_RESOLVE 回傳值
> - `key.class` — TINYINT，2=public / 3=private（對應 `keyclass` 表）
> - `keytype.id` — 0=RSA / 3=ECDSA
> - `keygroupstatus.id` — 0=Unused / 1=Used / 2=Banned
> - `token.serialnumber` — VARCHAR(10)，唯一識別符（非 `token.index`）
> - `tokenstatus.id` — 0=Offline / 1=Online / 2=Banned
> - `authority` 表欄位：`query`, `rename`, `sign`, `ban`, `reset`, `log_query_all`（ALTER TABLE 新增，見下方 Migration SQL）
>   → 對應 `stUserAuthority`：`isQuery`, `isRename`, `isSign`, `isBan`, `isReset`, `isLogQueryAll`
> - `log_query_all = 1`：可查所有人的 operation_log（Admin / Manager）
>   `log_query_all = 0`（預設）：只能查自己的 log，帶其他人 `user` filter → `PERMISSION_DENIED`
>
> ```sql
> -- Migration SQL（首次部署時執行）
> ALTER TABLE `etokensystem`.`authority`
>   ADD COLUMN `log_query_all` TINYINT(1) NOT NULL DEFAULT 0
>   COMMENT '1=可查所有人 operation_log (Admin/Manager); 0=只能查自己';
> ```
> - `pc` 表（ALTER 後）含 `logintime` / `logouttime` (TIMESTAMP)
> - `tokengroup.pc` FK 已移除（不再強制關聯）

```sql
-- 決策 P1-2：兩張獨立日誌表，職責不同
-- audit_log：安全審計，由 DatabaseService 自動生成，client 不可直接寫入
-- operation_log：業務操作記錄（何人/何時/對何物/做什麼/結果）
--             eToken Server 透過 DBFO_LOG_WRITE 寫入
--             詳細表設計見 §13

-- 主動資料 DB
CREATE DATABASE IF NOT EXISTS `etokensystem`   DEFAULT CHARSET utf8mb4;
-- 封存目標 DB（決策 L3-1）
CREATE DATABASE IF NOT EXISTS `etokensystem_archive` DEFAULT CHARSET utf8mb4;

-- 建立 operation_log 表（詳細設計見 §13）
CREATE TABLE IF NOT EXISTS `etokensystem`.`operation_log` (
    `id`        BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    `ts`        DATETIME(3)      NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `user`      VARCHAR(128)     NOT NULL,   -- "DOMAIN\username"
    `action`    VARCHAR(64)      NOT NULL,   -- SIGN_REQUEST | KEY_ISSUE | KEY_BAN | ...
    `obj_type`  ENUM('KEY','TOKEN','PC','SESSION') NOT NULL,
    `obj_id`    VARCHAR(128)     NOT NULL,   -- key_group_index | token_sn | pc_name
    `obj_label` VARCHAR(256)     NULL,       -- 人可讀標籤，含專案名
    `result`    TINYINT(1)       NOT NULL,   -- 1=success, 0=fail
    `detail`    VARCHAR(1024)    NULL,
    PRIMARY KEY (`id`),
    INDEX       idx_ts       (`ts`),
    INDEX       idx_user_ts  (`user`, `ts`),       -- 最常用查詢組合
    FULLTEXT    idx_ft_label (`obj_label`)         -- 专案名全文搜尋決策 L3-3
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=COMPRESSED;

-- 封存表（結構與主動表完全相同、便於 JOIN 查詢）
CREATE TABLE IF NOT EXISTS `etokensystem_archive`.`operation_log` LIKE `etokensystem`.`operation_log`;

-- 安全審計日誌表（自動生成，client 不可直接控制）
CREATE TABLE IF NOT EXISTS `etokensystem`.`audit_log` (
    `index`       BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    `timestamp`   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `user`        VARCHAR(128)     NOT NULL,
    `client_type` TINYINT UNSIGNED NOT NULL,
    `opcode`      TINYINT UNSIGNED NOT NULL,
    `success`     TINYINT UNSIGNED NOT NULL,
    `detail`      VARCHAR(512)         NULL,
    PRIMARY KEY (`index`),
    INDEX idx_ts   (`timestamp`),
    INDEX idx_user (`user`),
    INDEX idx_op   (`opcode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

`DatabaseDefine.h` 新增：

```cpp
// audit_log 新欄位
#define DB_TABLE_AUDIT_LOG     "audit_log"
#define DB_TABLE_OPERATION_LOG "operation_log"
#define DB_ITEM_ACTION         "action"
#define DB_ITEM_OBJ_TYPE       "obj_type"
#define DB_ITEM_OBJ_ID         "obj_id"
#define DB_ITEM_OBJ_LABEL      "obj_label"
#define DB_ITEM_RESULT         "result"
#define DB_ITEM_CLIENT_TYPE    "client_type"
#define DB_ITEM_SUCCESS        "success"
#define DB_ITEM_DETAIL         "detail"
#define DB_ITEM_TIMESTAMP      "timestamp"
```

---

## 8. `Global.h` 設定結構

```cpp
#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <string>

namespace gli
{
struct DbServiceConfig
{
    // 監聽
    std::string  sListenIp   = "0.0.0.0";
    uint16_t     uListenPort = 28015;

    // TLS
    std::filesystem::path fsCertFile;
    std::filesystem::path fsKeyFile;

    // MySQL
    std::string  sMySqlIp;
    uint16_t     uMySqlPort = 3306;

    // LDAP
    std::array<std::string, 2> ldapHosts = {
        "gli-dc161.genesyslogic.com.tw",
        "gli-dc162.genesyslogic.com.tw"
    };
};

extern DbServiceConfig g_config;
bool LoadConfig(const std::filesystem::path &fsIni);
} // namespace gli
```

---

## 9. 測試清單（符合 TESTING.md L1 要求）

### Unit Tests（純邏輯）

| 測試項目 | 輸入 | 預期輸出 |
|---|---|---|
| `PermissionGuard::IsClientAllowed` | `DBCT_LOG_SERVER`, `DBFO_NEW_KEY` | `false` |
| `PermissionGuard::IsClientAllowed` | `DBCT_LOG_SERVER`, `DBFO_AUDIT_READ` | `true` |
| `PermissionGuard::IsClientAllowed` | `DBCT_LOG_SERVER`, `DBFO_LOG_QUERY` | `true` |
| `PermissionGuard::IsClientAllowed` | `DBCT_LOG_SERVER`, `DBFO_LOG_ARCHIVE` | `true` |
| `PermissionGuard::IsClientAllowed` | `DBCT_LOG_SERVER`, `DBFO_LOG_WRITE` | `false` |
| `PermissionGuard::IsClientAllowed` | `DBCT_ETOKEN_SERVER`, `DBFO_AUDIT_READ` | `false` |
| `PermissionGuard::IsClientAllowed` | `DBCT_ETOKEN_SERVER`, `DBFO_LOG_QUERY` | `false` |
| `PermissionGuard::IsClientAllowed` | `DBCT_ETOKEN_SERVER`, `DBFO_LOG_ARCHIVE` | `false` |
| `PermissionGuard::IsClientAllowed` | `DBCT_ETOKEN_SERVER`, `DBFO_LOG_WRITE` | `true` |
| `PermissionGuard::HasUserPermission` | `auth.isBan=false`, `DBFO_BAN_KEY` | `false` |
| `PermissionGuard::HasUserPermission` | `auth.isSign=true`, `DBFO_SIGN_RESOLVE` | `true` |
| `PermissionGuard::HasUserPermission` | 任意 `auth`，`DBFO_UPDATE_TOKEN` | `true`（server-to-server whitelist） |
| `AuditEntry` 欄位預設值 | 預設建構 | `uIndex=0, bSuccess=false` |
| `DBFO_AUDIT_READ` range check | `from_ts="2025-01-01"`, `to_ts="2025-12-31"` (364 days) | `RANGE_EXCEEDED` |
| `DBFO_LOG_QUERY` `page_size` 邊界 | `page_size=200`（上限）| 正常分頁回傳 |
| `DBFO_LOG_QUERY` `page_size` 超限 | `page_size=201` | `STATUS_FAIL "PAGE_SIZE_EXCEEDED"` |
| `DBFO_AUDIT_READ` range check | `from_ts="2025-01-01"`, `to_ts="2025-03-31"` (89 days) | pass validation |

### Failure Path Tests（至少各一路）

| Path | 預期行為 |
|---|---|
| LDAP 兩台主機均失敗 | `STATUS_FAIL "LDAP_FAIL"` |
| DB 連線失敗（錯誤 IP）| `STATUS_FAIL "DB_CONNECT_FAIL"` |
| client_type = LOG_SERVER 發 `DBFO_BAN_KEY` | `STATUS_FAIL "CLIENT_PERM_DENIED"` |
| client_type = ETOKEN_SERVER 發 `DBFO_AUDIT_READ` | `STATUS_FAIL "CLIENT_PERM_DENIED"` |
| 使用者 `auth.isBan=false` 發 `DBFO_BAN_KEY` | `STATUS_FAIL "USER_PERM_DENIED"` |
| `DBFO_NEW_KEY` 傳空 label | `STATUS_FAIL` + DB 不寫入 |
| Session 在 DBFO_LOGIN 前發 DBFO_QUERY_KEY | `STATUS_FAIL` + 斷線 |
| `DBFO_AUDIT_READ` 查詢範圍 > 90 天 | `STATUS_FAIL "RANGE_EXCEEDED"` |
| `CAuditLogger::Write()` DB 連線失敗 | 回傳 `false` + DbgPrint，業務層不 rollback（Option B）|
| `DBFO_LOG_WRITE` 傳送非法 JSON | `STATUS_FAIL "PARSE_ERROR"` |
| `client_type = ETOKEN_SERVER` 發 `DBFO_LOG_QUERY` | `STATUS_FAIL "CLIENT_PERM_DENIED"` |
| `client_type = ETOKEN_SERVER` 發 `DBFO_LOG_ARCHIVE` | `STATUS_FAIL "CLIENT_PERM_DENIED"` |
| `client_type = LOG_SERVER` 發 `DBFO_LOG_WRITE` | `STATUS_FAIL "CLIENT_PERM_DENIED"` |
| `DBFO_LOG_WRITE` 傳入 `obj_label` 欄位 | 該欄位被忽略，DatabaseService 從 DB 查回覆寫 |
| `DBFO_LOG_QUERY` 傳入 `obj_label_like` + `include_archive: true` | `STATUS_FAIL "FEATURE_NOT_SUPPORTED"` |
| `DBFO_LOG_QUERY` 傳入 `include_archive: true`，無 obj_label_like | `total_matched = -1`，data 正常回傳 |
| `DBFO_LOG_ARCHIVE` 封存期間 eToken Server 寫入新記錄 | 新記錄 ts ≥ threshold，不被封存，不被刪除 |

### Integration Tests（需 DB 連線）

- 完整 Login → QueryKey → Logout 流程
- Login → NewKey → BanKey → ResetKey 流程
- Login → SignResolve + UpdateToken 對應流程
- Log Server 登入 → `DBFO_AUDIT_READ`（30 天範圍）流程
- eToken Server 登入 → `DBFO_LOG_WRITE`（JSON payload，含 obj_label 查回）流程
- Log Server 登入 → `DBFO_LOG_QUERY`（`include_archive: false`）流程
- Log Server 登入 → `DBFO_LOG_QUERY`（`include_archive: true`，UNION ALL 路徑）流程
- Log Server 登入 → `DBFO_LOG_ARCHIVE`（`dry_run: true`，不實際移動）流程
- Log Server 登入 → `DBFO_LOG_ARCHIVE`（`dry_run: false`，實際移動並驗證 etokensystem_archive）流程
- 效能 gate（Phase D 前置）：P99 `ConnectDb()` < 10 ms（LAN 環境）

---

## 10. 實作順序（Phase）

```
Phase A（獨立可完成，無 TCP 依賴）
  1. DbServiceDefine.h
  2. AuditDefine.h + AuditLogger.h/cpp（含 DB schema migration SQL）
  3. PermissionGuard.h/cpp（含 unit tests）
  4. LdapAuth.h/cpp（從 TcpClientCmd_ldap.cpp 提取）

Phase B（Session 核心）
  5. DbSessionHandler.h/cpp（Run + dispatch skeleton）
  6. DbSessionHandler_Auth.cpp（LOGIN 流程）
  7. DbSessionHandler_Key.cpp
  8. DbSessionHandler_Sign.cpp（SIGN_RESOLVE）
  9. DbSessionHandler_Token.cpp
  10. DbSessionHandler_Pc.cpp

Phase C（服務主體 + Log Server 介面）
  11. DbSessionHandler_Log.cpp（LOG_WRITE / LOG_QUERY / LOG_ARCHIVE / AUDIT_READ）
  12. DbService.h/cpp（TcpServer accept 主體）
  13. Global.h/cpp + main.cpp（ini 讀取 + 啟動）
  14. setup.bat + .vcxproj

Phase D（整合測試）
  15. Stress test 新增 DB Service Client scene
  16. eToken Server 遷移（選項：從 in-process CGlMySql → DB Service TCP）
```

---

## 11. 遷移決策（決策 P1-4：table 單一 writer 邊界）

> ⚠️ **eToken Server 端的遷移屬 L2 任務**（核心協議路徑）。
> 策略：**漸進式遷移 + 明確 table 所有權邊界**

### Table 所有權切換時間點

| Table | Phase A~C Writer | Phase D Writer（切換後）| 切換前置條件 |
|---|---|---|---|
| `keygroup` / `key` | eToken Server 直連 | DatabaseService only | KEY ops 整合測試通過 |
| `token` / `tokengroup` | eToken Server 直連 | DatabaseService only | TOKEN ops 整合測試通過 |
| `pc` | eToken Server 直連 | DatabaseService only | PC ops 整合測試通過 |
| `audit_log` | DatabaseService only | DatabaseService only | Day 1 起禁止直連 |
| `event_log` | DatabaseService only | DatabaseService only | Day 1 起禁止直連 |

**規則：任何時間點，某個 table 只允許一個 writer。** 禁止雙寫期間同一 table 跨兩條路徑。

### 遷移步驟

1. Phase A~C：DatabaseService 新增 `audit_log` / `event_log`；eToken Server 保留直連 key/token/pc
2. Phase D 前置：為每個 table 群組補整合測試，gate 通過後才切換
3. Phase D 切換：以 `CDbServiceClient` 逐一替換 `CTcpClientCmd` / `CTcpDongleSsl` 的直連調用
4. 切換完成：移除 `CTcpClientCmd : public CGlMySql` 及 `CTcpDongleSsl : public CGlMySql` 繼承

---

## 12. 架構決策記錄（ADR）

| ID | 決策問題 | 決策 | 理由 |
|---|---|---|---|
| P0-1 | CAuditLogger 使用共用還是獨立 DB 連線 | **獨立 `CGlMySql` 實例（has-a，非繼承）** | rollback 不能沉默審計；主操作失敗時審計必須仍可寫入 |
| P0-2 | Session 保持長連線還是 per-dispatch 重連 | **per-dispatch `ConnectDb/DisconnectDb`** | `CGlMySql` 無自動重連（程式碼確認）；與既有 `TcpDongleSsl` / `TcpDongleManage` 模式一致 |
| P1-1 | Login 第二段等待 timeout | **獨立常數 `DB_SERVICE_LOGIN_TIMEOUT = 30000ms`** | 防使用者輸入超時（5s 全域太短） vs 防 DoS 佔用 thread 的平衡 |
| P1-2 | LOG_WRITE 的信任邊界 | **業務事件日誌（event_log）與安全審計（audit_log）分離** | 安全審計不能由 client 控制；防被入侵 eToken Server 偽造審計紀錄 |
| P1-3 | PermissionGuard 未知 opcode 預設行為 | **fail-closed（`default: return false`）+ 明確 whitelist** | 安全設計原則；未來新增 opcode 若忘記加 case，預設拒絕而非放行 |
| P1-4 | 遷移期間 table 雙寫 | **明確 table 所有權切換時間點，禁止雙寫** | 串行保證：同一 table 同一時間只有一個 writer |
| P0-3 | `GlMySql.cpp` `SQL_LOGIN_TIMEOUT = nullptr` | **實作時修正為 `(SQLPOINTER)5`（5 秒）** | `nullptr` 對 `SQLUINTEGER` 屬誤用；per-dispatch 模式下無限等待可無限佔用 thread |
| P1-5 | `CAuditLogger::Write()` 失敗行為 | **Option B：`bool` 回傳 + DbgPrint，業務操作繼續** | 可用性優先；DbgPrint 為備用稽核紀錄；合規升級時改為 Option C |
| P1-5b | `event_log` 是否記錄操作者 | **加入 `user` + `client_type` 欄位** | 設計遺漏修正；事後鑑識需要操作者歸因 |
| P2-1 | `DBFO_EVENT_LOG` detail_string 含空格時解析斷裂 | **Option B：SplitString(sRecv,' ',2)，detail 保留剩餘全文** | 與既有協議一致；Utility::SplitString nMaxTokens 機制保證最後 token 含所有剩餘 |
| P2-2 | `CAuditLogger::Read()` 無內部 range 防護 | **也做 range 驗證（防競性重複）** | 內部工具/測試拱過 Handler gate；變更上限僅需改這一處 |
| P2-3 | `DoLogin()` 中 `_audit.Init()` 順序 | **Init() 移至步驟 1（解析完 user 後立即執行）** | 步驟 3（LDAP）失敗就需 Write()；功 Init() 必須早於所有失敗路徑 |
| L3-1 | 封存目標媒介 | **同一 MySQL 的 `etokensystem_archive` DB** | 不需距離連線；SQL INSERT SELECT 就能移動；未來需要可改為遠端 |
| L3-2 | `DBFO_LOG_WRITE` payload 格式 | **JSON（obj_label 可含空格、特殊字元）** | SplitString nMaxTokens 只解决末尾空格，第 3 欄的空格仍斷裂 |
| L3-3 | `obj_label` 搜尋方式 | **InnoDB FULLTEXT index** | 專案名可在 label 中間；FULLTEXT 支援 MATCH/AGAINST，優於前缀索引 |
| L3-4 | Log Service 對外協議 | **Length-Prefixed JSON over TLS** | 分頁、多欄位過濾對於 JSON 較自然；現有 binary 協議適合結構簡單的 key/token ops |
| L3-5 | `obj_label` 搜尋索引策略 | **InnoDB FULLTEXT index on `operation_log.obj_label`** | 專案名可在 label 中間；FULLTEXT 支援 MATCH/AGAINST，優於 B-Tree 前缀索引；archive 表同步建立 |
| L3-6 | `obj_label` 由誰填入 | **移除出 client payload；DatabaseService 查 DB 填入** | 防 eToken Server 偽造 label；KEY→keygroup.label，TOKEN→token.label，PC→obj_id，SESSION→NULL |
| L3-7 | `DBFO_LOG_ARCHIVE` 批次刪除安全性 | **id-range 批次（@min_id/@max_id）+ 跨 DB InnoDB transaction** | DELETE WHERE id IN (SELECT ...) 在跨批次間有 id 不確定性；id BETWEEN 固定範圍確保 INSERT/DELETE 精確對應；新寫入 id > max_id 不干擾 |
| L3-8 | LogService 連接 DatabaseService 的 client type | **`DBCT_LOG_SERVER = 2`** | 使用 Log Server 的 opcode 白名單（AUDIT_READ/LOG_QUERY/LOG_ARCHIVE）；需要擴充時新增枚舉值 |
| L3-9 | `DBFO_LOG_QUERY` `total_matched` 精確度 | **include_archive=false → 精確 COUNT；include_archive=true → -1** | UNION ALL 兩張表的 COUNT(*) 無法利用索引，大資料量時代價過高；-1 明確表示不支援而非 bug |
| L3-10 | LogService 使用者授權模型 | ~~管理員 full-read~~ **Superseded by L3-15** | — |
| L3-11 | `obj_label_like` + `include_archive: true` | **NOT SUPPORTED，回傳 `FEATURE_NOT_SUPPORTED`** | FULLTEXT MATCH...AGAINST 不能跨 UNION ALL 兩表；若強行使用將退化全表 LIKE 掃描，效能不可接受 |
| L3-12 | `DbServiceClient` 連線生命週期 | **per-request（每次查詢重新 Connect/Login/Finish/Disconnect）** | LogService 查詢頻率低；per-request 與既有 per-dispatch 模式一致；無需 health-check / reconnect 邏輯 |
| L3-13 | `req_id` 規格 | **選填，max 128 bytes，超出 → REQ_ID_TOO_LONG，缺少 → echo ""，不驗證格式** | Echo 用途：client 對齊非同步回應；長度限制防 echo 膨脹；格式不限讓 client 自由選 UUID 或序號 |
| L3-14 | `DBFO_LOG_ARCHIVE` 觸發方式 | **管理員手動 API（§16.5 `log_archive` message type）** | 系統無排程框架；手動控制符合低頻封存需求；外部 API 路徑確定後，日後加排程只需在 LogService 內部複用相同路徑 |
| L3-15 | LogService `log_query_all` 權限模型 | **`authority.log_query_all` 欄位控制跨用戶查詢**；false → 只看自己；true → 看全部；PERMISSION_DENIED 防跨界 | Admin/Manager 需全覽；一般用戶自助查詢；單欄位簡單；DB 存的是真值，不依賴 LDAP 群組 |
| L3-16 | Key Management Tool（future） | **未規劃，預留 `DBCT_KEY_MGMT_TOOL = 3`** | 未來增加/管理 keys 與 tokens 的工具；需要時擴充 `DB_CLIENT_TYPE` 枚舉並在 `IsClientAllowed` 新增 whitelist case；不影響現有 opcode 設計 |

---

## 13. `operation_log` 表設計

### 13.1 Schema

```
欄位    類型                          說明
────────────────────────────────────────────────────────────────────────────
id         BIGINT UNSIGNED AUTO_INCREMENT   主鍵
ts         DATETIME(3)                      毫秒等級時間戳
user       VARCHAR(128)  NOT NULL           "DOMAIN\user" 以 LDAP 
                                            已驗證身份為主
action     VARCHAR(64)   NOT NULL           動詞，規範字串（見 13.2）
obj_type   ENUM(KEY,TOKEN,PC,SESSION)       被操作物體類型
obj_id     VARCHAR(128)  NOT NULL           物體 ID（key_group_index 等）
obj_label  VARCHAR(256)  NULL               人可讀標籤，含專案名
                                            不由 eToken Server 傳入：
                                            DatabaseService 從 DB 查回後填入
result     TINYINT(1)    NOT NULL           1=success, 0=fail
detail     VARCHAR(1024) NULL               补充資訊
```

> **`obj_label` 填入策略（決策 L3-6）**：
> eToken Server **不傳送** `obj_label`（防偽造），DatabaseService 收到 `obj_id` 後，
> 依 `obj_type` 在同一 DB 連線中查詢對應表：
>
> | obj_type | 查詢 SQL | 失敗行為 |
> |---|---|---|
> | `KEY` | `SELECT label FROM keygroup WHERE \`index\` = CAST(obj_id AS UNSIGNED)` | NULL，不阻止寫入 |
> | `TOKEN` | `SELECT label FROM token WHERE serialnumber = obj_id` | NULL，不阻止寫入 |
> | `PC` | label = obj_id（pc.name 即人可讀名稱，不需額外查詢）| — |
> | `SESSION` | label = NULL（無對應物件）| — |
>
> 好處：eToken Server 不持有 label 快取，不需額外 roundtrip；label 來源唯一（DB truth）。

### 13.2 action 字典

| action 字串 | obj_type | 觸發時機 |
|---|---|---|
| `KEY_QUERY` | KEY | 查詢 key group 列表 |
| `KEY_ISSUE` | KEY | 新建 key group |
| `KEY_BAN` | KEY | 封鎖 key group |
| `KEY_RESET` | KEY | 重置 key group |
| `SIGN_REQUEST` | KEY | 取得 private key ID 用於簽章 |
| `TOKEN_STATUS_CHANGE` | TOKEN | token 狀態變更 |
| `TOKEN_LOCATION_CHANGE` | TOKEN | token 位置變更 |
| `PC_LOGIN` | PC | PC 登入 |
| `PC_LOGOUT` | PC | PC 登出 |
| `SESSION_LOGIN` | SESSION | DatabaseService 登入（自動生成）|
| `SESSION_LOGOUT` | SESSION | DatabaseService 登出（自動生成）|

### 13.3 索引設計與查詢驗證

| 查詢場景 | 使用索引 |
|---|---|
| 以使用者查所有操作 | `idx_user_ts (user, ts)` |
| 以專案名搜尋 key | `FULLTEXT idx_ft_label` → `MATCH(obj_label) AGAINST(? IN BOOLEAN MODE)` |
| 封存移動作業 | `idx_ts (ts)` + `WHERE ts < threshold` |
| 組合查詢（user + label）| MySQL 選擇其中一個；建議先對 user 過濾再 FULLTEXT |

---

## 14. 資料量管理與封存策略

### 14.1 封存作業流程

```
[觸發方式]
  • 管理員透過 LogService 外部 API 傳送 log_archive 請求（§16.5）
  • LogSession 收到後，向 DatabaseService 發送 DBFO_LOG_ARCHIVE { "dry_run": false, "threshold_days": N }
  • 排程觸發不在本版本範圍內；日後擴充時在 LogService 內部加 timer，複用相同 DBFO_LOG_ARCHIVE 路徑即可

[執行步驟]
  1. 確認 etokensystem_archive.operation_log 表存在
  2. 計算 threshold = NOW() - INTERVAL threshold_days DAY
  3. 以 id-range 批次循環（決策 P0-2，防止 race condition）：

     每輪批次：
     ① SET @min_id = NULL, @max_id = NULL;
        SELECT MIN(id), MAX(id) INTO @min_id, @max_id
          FROM (SELECT id FROM etokensystem.operation_log
                WHERE ts < threshold ORDER BY id LIMIT 5000) t;
        -- @min_id IS NULL → 本次封存完成，跳出迴圈

     ② BEGIN TRANSACTION（在同一連線上跨 DB）
     ③ INSERT INTO etokensystem_archive.operation_log
          SELECT * FROM etokensystem.operation_log
          WHERE id BETWEEN @min_id AND @max_id AND ts < threshold;
     ④ DELETE FROM etokensystem.operation_log
          WHERE id BETWEEN @min_id AND @max_id AND ts < threshold;
     ⑤ COMMIT → 回到 ①

     安全性保證：AUTO_INCREMENT 只增不減，新寫入記錄 id > @max_id 且 ts ≥ threshold，
                不會被 ③ INSERT 捲走，亦不會被 ④ DELETE 誤刪。

  4. 回傳封存總筆數

[變化量預估基準]
  每筆 operation_log 大約 0.3-0.5 KB
  若每天 5000 筆，半年 = ~270 萬筆 = ~135 MB
  若每天 50000 筆，半年 = ~1350 MB——封存前可考慮加 ROW_FORMAT=COMPRESSED
```

### 14.2 封存 DB 的讀取策略

| 場景 | 方法 |
|---|---|
| 日常查詢 | `include_archive: false`（預設）——查 `etokensystem.operation_log` |
| 查歷史资料 | `include_archive: true`——DatabaseService 對兩張表各淘再 UNION ALL |
| 全期結果 | UNION ALL 對 `ts` DESC 排序 + LIMIT/OFFSET 分頁 |

---

## 15. LogService 設計

### 15.1 架構定位

```
[eToken Client]
   |  TLS (Port 28016)
   |  Length-Prefixed JSON
   v
[LogService]
   |  TLS (localhost:28015)
   |  Binary opcode protocol
   |  DBFO_LOG_QUERY / DBFO_LOG_ARCHIVE
   v
[DatabaseService]
   |  ODBC
   v
[MySQL: etokensystem + etokensystem_archive]
```

- **DatabaseService**：只監聽 `127.0.0.1:28015`，拒絕外部連線
- **LogService**：監聽 `0.0.0.0:28016`，對外提供「讀取」 API，不提供寫入
- 兩個服務各自獨立身份驗證（LDAP）

> **LogService 連線 DatabaseService 時使用 `DB_CLIENT_TYPE = DBCT_LOG_SERVER (2)`（決策 P1-1）**。
> 若未來新增管理工具等第三方 client，需擴充 `DB_CLIENT_TYPE` 枚舉並更新 `IsClientAllowed`。

> **LogService 授權模型（決策 L3-15）**：
> 查看他人 log 的權限由 `authority.log_query_all` 欄位控制：
> - `log_query_all = 1`（Admin / Manager）：可查所有人的 operation_log；`user` filter 為可選
> - `log_query_all = 0`（一般使用者）：`user` filter **由 LogService 強制設為自己**；
>   若 client 傳入他人的 `user` filter → 回傳 `PERMISSION_DENIED`
>
> `HasUserPermission(auth, DBFO_LOG_QUERY)` 在 `isLogQueryAll = false` 時回傳 `false`，
> 導致 DatabaseService 拒絕一般使用者直連。
> LogService 層在轉發前做第二道 filter 強制（見 §16.3）。

### 15.2 目錄結構

```
log_service/
├── LogService.sln
├── setup.bat
└── LogService/
    ├── LogService.vcxproj
    ├── main.cpp
    ├── Global.h/cpp              ← 監聽 port, DatabaseService 本機地址, cert 路徑
    ├── LogServiceDefine.h        ← JSON message type 常數
    ├── Service/
    │   ├── LogServer.h/cpp           ← TcpServer accept → LogSession thread
    │   └── LogSession.h/cpp          ← Session 生命週期管理
    ├── Handler/
    │   ├── LogSessionHandler.h/cpp   ← JSON 解析 + dispatch
    │   └── LogSessionHandler_Query.cpp
    ├── Auth/
    │   └── LdapAuth.h/cpp            ← 對外客戶端身份驗證（與 DatabaseService 共用原始碼）
    └── DbClient/
        └── DbServiceClient.h/cpp     ← 本機連線 DatabaseService，發送 DBFO_LOG_QUERY / DBFO_LOG_ARCHIVE
                                         ← 連線生命週期：per-request（決策 L3-12）
                                            每次查詢：Connect → Login → Query/Archive → Finish → Disconnect
                                            無長連線、無 health-check 邏輯
```

---

## 16. Length-Prefixed JSON 協議規格（LogService 對外）

### 16.1 幀結構

```
[4 bytes big-endian uint32: JSON 字節數][UTF-8 JSON 內容]
```

- TLS 框架與現有 CTcpSsl 相同（OpenSSL SSL_read/SSL_write）
- 只將 payload 格式從 binary string 改為 JSON，長度前置不再用 `CTcpSsl::SendCmd`
- 最大幀大小：4 MB（防止惡意大 payload）

### 16.2 登入流程

> **`req_id` 規格（決策 L3-13，適用所有 message type）**
> - 選填（missing 或 `null` → 回應中 echo `""`）
> - 型別：字串；最大 **128 bytes**（UTF-8）；超過 → `{ "success": false, "error": "REQ_ID_TOO_LONG" }`
> - 不驗證格式（UUID、任意字串皆可）；server 原樣 echo，不解析

```json
// Client → LogService
{
  "type": "login",
  "req_id": "unique-uuid",   ← 選填，max 128 bytes
  "user": "DOMAIN\\john",
  "password": "..."
}

// LogService → Client（成功）
{ "type": "login", "req_id": "unique-uuid", "success": true }

// LogService → Client（失敗）
{ "type": "login", "req_id": "unique-uuid", "success": false, "error": "LDAP_FAIL" }
```

### 16.3 查詢

> **`user` filter 與 `log_query_all` 的互動（決策 L3-15）**：
> | 情境 | LogService 行為 |
> |---|---|
> | `isLogQueryAll=true`，不帶 `user` | 查全部人，不插入 filter |
> | `isLogQueryAll=true`，帶 `user` | 依 client 指定查詢 |
> | `isLogQueryAll=false`，不帶 `user` | **強制插入** `user = <自己>` |
> | `isLogQueryAll=false`，`user = <自己>` | 正常查詢 |
> | `isLogQueryAll=false`，`user = 他人` | `{ "success": false, "error": "PERMISSION_DENIED" }` |

```json
// Client → LogService
{
  "type": "log_query",
  "req_id": "abc123",
  "filter": {
    "user":           "DOMAIN\\john",       ← 可省略；isLogQueryAll=false 時強制覆寫為自己
    "obj_label_like": "ProjectAlpha",        ← FULLTEXT MATCH，可省略
                                              ← ⚠️ include_archive:true 時禁止使用
    "action":         "SIGN_REQUEST",        ← 可省略
    "result":         1,                     ← 1|0|null
    "from_ts":        "2026-01-01T00:00:00", ← 必填
    "to_ts":          "2026-03-01T00:00:00"  ← 必填
  },
  "page":            1,
  "page_size":       50,
  "include_archive": false     ← true 時：total_matched 回傳 -1；不可搭配 obj_label_like
}

// LogService → Client（include_archive: false，精確 COUNT）
{
  "type": "log_query",
  "req_id": "abc123",
  "success": true,
  "total_matched": 523,        ← 精確值
  "page": 1,
  "page_size": 50,
  "data": [ ... ]
}

// LogService → Client（include_archive: true，跨表 COUNT 不支援）
{
  "type": "log_query",
  "req_id": "abc123",
  "success": true,
  "total_matched": -1,         ← -1 表示不支援精確計算，使用頁面導航
  "page": 1,
  "page_size": 50,
  "data": [ ... ]
}

// LogService → Client（obj_label_like + include_archive:true 不支援）
{
  "type": "log_query",
  "req_id": "abc123",
  "success": false,
  "error": "FEATURE_NOT_SUPPORTED",
  "message": "obj_label_like cannot be combined with include_archive=true"
}
```

### 16.5 封存（管理員手動觸發）

```json
// Client → LogService
{
  "type": "log_archive",
  "req_id": "arc-001",
  "threshold_days": 180,   ← 封存 N 天前的記錄；必填；合法範圍 30–3650
  "dry_run": false         ← true = 只回傳預估筆數，不實際移動資料
}

// LogService → Client（成功）
{
  "type": "log_archive",
  "req_id": "arc-001",
  "success": true,
  "archived_count": 27340,  ← 實際移動筆數（dry_run=true 時為預估值）
  "dry_run": false
}

// LogService → Client（失敗 — threshold_days 超出範圍）
{
  "type": "log_archive",
  "req_id": "arc-001",
  "success": false,
  "error": "INVALID_THRESHOLD",
  "message": "threshold_days must be between 30 and 3650"
}
```

驗證規則：

| 欄位 | 型別 | 必填 | 合法範圍 | 錯誤碼 |
|---|---|---|---|---|
| `threshold_days` | int | ✓ | 30–3650 | `INVALID_THRESHOLD` |
| `dry_run` | bool | 否，預設 `false` | — | — |

> `log_archive` 只有通過 LDAP 驗證後的 session 才能呼叫（與 `log_query` 相同）。

---

### 16.4 JSON 庫選擇

| 選項 | 優點 | 缺點 |
|---|---|---|
| **nlohmann/json**（建議） | header-only，非常成熟，Conan 套件直接引入 | 編譯速度較 simdjson 慢 |
| simdjson | 語法解析最快 | API 較不直觀，不支援小 draft |
| 手寫解析 | 零依賴 | 維護成本極高，不建議 |

> 建議使用 **nlohmann/json 3.x**，Conan recipe = `nlohmann_json/3.11.3`。

---

*最後更新: 2026-03-05*
