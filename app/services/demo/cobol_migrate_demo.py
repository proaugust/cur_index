"""COBOL → Java 多 Agent 迁移引擎示范数据（无真实解析/翻译逻辑）。"""

from __future__ import annotations

from typing import Any

from app.services.demo.agent_common import AgentStepData

STEP_NAMES: dict[int, str] = {
    1: "扫描 COBOL 源码",
    2: "分类文件类型",
    3: "关键信息写入 RAG",
    4: "构建调用关系图",
    5: "翻译并落位 Spring Boot",
    6: "闭环验证",
    7: "代码片段测试",
}

DEMO_ROOT = "legacy/bank-acct"

SCANNED_FILES: list[dict[str, Any]] = [
    {"name": "MAINACCT.cbl", "path": f"{DEMO_ROOT}/cbl/MAINACCT.cbl", "lines": 486, "ext": ".cbl"},
    {"name": "ACCTPOST.cbl", "path": f"{DEMO_ROOT}/cbl/ACCTPOST.cbl", "lines": 312, "ext": ".cbl"},
    {"name": "ACCTINQ.cbl", "path": f"{DEMO_ROOT}/cbl/ACCTINQ.cbl", "lines": 198, "ext": ".cbl"},
    {"name": "DBACCES.cbl", "path": f"{DEMO_ROOT}/cbl/DBACCES.cbl", "lines": 267, "ext": ".cbl"},
    {"name": "FILEIO.cbl", "path": f"{DEMO_ROOT}/cbl/FILEIO.cbl", "lines": 154, "ext": ".cbl"},
    {"name": "INTFAPI.cbl", "path": f"{DEMO_ROOT}/cbl/INTFAPI.cbl", "lines": 121, "ext": ".cbl"},
    {"name": "CUSTCOPY.cpy", "path": f"{DEMO_ROOT}/cpy/CUSTCOPY.cpy", "lines": 88, "ext": ".cpy"},
    {"name": "ACCTCOPY.cpy", "path": f"{DEMO_ROOT}/cpy/ACCTCOPY.cpy", "lines": 64, "ext": ".cpy"},
    {"name": "ERRHAND.cbl", "path": f"{DEMO_ROOT}/cbl/ERRHAND.cbl", "lines": 95, "ext": ".cbl"},
    {"name": "BATCHJOB.cbl", "path": f"{DEMO_ROOT}/cbl/BATCHJOB.cbl", "lines": 203, "ext": ".cbl"},
    {"name": "REPORT.cbl", "path": f"{DEMO_ROOT}/cbl/REPORT.cbl", "lines": 176, "ext": ".cbl"},
    {"name": "AUDITLOG.cbl", "path": f"{DEMO_ROOT}/cbl/AUDITLOG.cbl", "lines": 142, "ext": ".cbl"},
]

CLASSIFICATIONS: list[dict[str, Any]] = [
    {"file": "MAINACCT.cbl", "type": "入口程序", "tags": ["CALL", "BATCH"], "confidence": 0.96},
    {"file": "ACCTPOST.cbl", "type": "业务逻辑", "tags": ["DB", "TRANSACTION"], "confidence": 0.94},
    {"file": "ACCTINQ.cbl", "type": "查询接口", "tags": ["READ-ONLY", "DB"], "confidence": 0.92},
    {"file": "DBACCES.cbl", "type": "数据库访问", "tags": ["EXEC SQL", "CURSOR"], "confidence": 0.98},
    {"file": "FILEIO.cbl", "type": "文件操作", "tags": ["SEQUENTIAL", "REWRITE"], "confidence": 0.91},
    {"file": "INTFAPI.cbl", "type": "外部接口", "tags": ["CICS", "COMMAREA"], "confidence": 0.89},
    {"file": "CUSTCOPY.cpy", "type": "COPYBOOK", "tags": ["DATA-DIVISION"], "confidence": 0.99},
    {"file": "ACCTCOPY.cpy", "type": "COPYBOOK", "tags": ["DATA-DIVISION"], "confidence": 0.99},
    {"file": "ERRHAND.cbl", "type": "公共模块", "tags": ["ERROR", "LOG"], "confidence": 0.93},
    {"file": "BATCHJOB.cbl", "type": "批处理", "tags": ["SCHEDULE", "FILE"], "confidence": 0.90},
    {"file": "REPORT.cbl", "type": "报表生成", "tags": ["FILE", "PRINT"], "confidence": 0.88},
    {"file": "AUDITLOG.cbl", "type": "审计日志", "tags": ["DB", "APPEND"], "confidence": 0.95},
]

RAG_CHUNKS: list[dict[str, Any]] = [
    {
        "file": "ACCTPOST.cbl",
        "chunk_id": "acctpost-001",
        "text": "PERFORM POST-TRANSACTION UNTIL WS-EOF = 'Y'. MOVE ACCT-NO TO DB-KEY.",
        "tags": ["paragraph", "call", "variable"],
    },
    {
        "file": "DBACCES.cbl",
        "chunk_id": "dbacces-003",
        "text": "EXEC SQL SELECT BALANCE INTO :WS-BALANCE FROM ACCT_TBL WHERE ACCT_NO = :WS-ACCT-NO END-EXEC.",
        "tags": ["sql", "select", "db"],
    },
    {
        "file": "MAINACCT.cbl",
        "chunk_id": "mainacct-002",
        "text": "CALL 'ACCTPOST' USING WS-COMMAREA WS-RETURN-CODE.",
        "tags": ["call", "interface"],
    },
    {
        "file": "CUSTCOPY.cpy",
        "chunk_id": "custcopy-001",
        "text": "05 CUST-NAME PIC X(40). 05 CUST-ID PIC 9(12).",
        "tags": ["copybook", "field"],
    },
]

GRAPH_EDGES: list[dict[str, Any]] = [
    {"source": "MAINACCT", "target": "ACCTPOST", "relation": "CALL"},
    {"source": "MAINACCT", "target": "ERRHAND", "relation": "CALL"},
    {"source": "ACCTPOST", "target": "DBACCES", "relation": "CALL"},
    {"source": "ACCTPOST", "target": "AUDITLOG", "relation": "CALL"},
    {"source": "ACCTINQ", "target": "DBACCES", "relation": "CALL"},
    {"source": "BATCHJOB", "target": "FILEIO", "relation": "CALL"},
    {"source": "BATCHJOB", "target": "ACCTPOST", "relation": "CALL"},
    {"source": "INTFAPI", "target": "ACCTINQ", "relation": "CALL"},
    {"source": "ACCTPOST", "target": "CUSTCOPY", "relation": "COPY"},
    {"source": "ACCTPOST", "target": "ACCTCOPY", "relation": "COPY"},
]

GRAPH_NODES: list[dict[str, Any]] = [
    {"id": "MAINACCT", "name": "MAINACCT", "category": "program", "symbol_size": 52},
    {"id": "ACCTPOST", "name": "ACCTPOST", "category": "program", "symbol_size": 48},
    {"id": "ACCTINQ", "name": "ACCTINQ", "category": "program", "symbol_size": 44},
    {"id": "DBACCES", "name": "DBACCES", "category": "program", "symbol_size": 46},
    {"id": "INTFAPI", "name": "INTFAPI", "category": "program", "symbol_size": 42},
    {"id": "BATCHJOB", "name": "BATCHJOB", "category": "program", "symbol_size": 40},
    {"id": "FILEIO", "name": "FILEIO", "category": "program", "symbol_size": 38},
    {"id": "ERRHAND", "name": "ERRHAND", "category": "program", "symbol_size": 36},
    {"id": "AUDITLOG", "name": "AUDITLOG", "category": "program", "symbol_size": 36},
    {"id": "CUSTCOPY", "name": "CUSTCOPY", "category": "copybook", "symbol_size": 32},
    {"id": "ACCTCOPY", "name": "ACCTCOPY", "category": "copybook", "symbol_size": 32},
]

JAVA_MAPPINGS: list[dict[str, Any]] = [
    {
        "cobol": "INTFAPI.cbl",
        "java": "src/main/java/com/bank/acct/web/AccountApiController.java",
        "layer": "Controller",
    },
    {
        "cobol": "ACCTINQ.cbl",
        "java": "src/main/java/com/bank/acct/service/AccountQueryService.java",
        "layer": "Service",
    },
    {
        "cobol": "ACCTPOST.cbl",
        "java": "src/main/java/com/bank/acct/service/AccountPostingService.java",
        "layer": "Service",
    },
    {
        "cobol": "DBACCES.cbl",
        "java": "src/main/java/com/bank/acct/repository/AccountRepository.java",
        "layer": "Repository",
    },
    {
        "cobol": "FILEIO.cbl",
        "java": "src/main/java/com/bank/acct/io/LegacyFileGateway.java",
        "layer": "Infrastructure",
    },
    {
        "cobol": "CUSTCOPY.cpy",
        "java": "src/main/java/com/bank/acct/domain/CustomerRecord.java",
        "layer": "Domain",
    },
]

VALIDATION_ITEMS: list[dict[str, Any]] = [
    {"item": "Controller 与 Service 分层", "status": "pass", "detail": "INTFAPI → AccountApiController，依赖注入正确"},
    {"item": "DB 访问收敛到 Repository", "status": "pass", "detail": "DBACCES 中 3 条 SQL 均已映射到 JPA/Native Query"},
    {"item": "批处理闭环", "status": "warn", "detail": "BATCHJOB 中文件回滚分支尚未生成对应 @Transactional 补偿"},
    {"item": "COPYBOOK 字段完整性", "status": "pass", "detail": "CUSTCOPY / ACCTCOPY 字段 100% 映射到 Domain"},
    {"item": "审计链路", "status": "pass", "detail": "AUDITLOG 调用链在 PostingService 中保留"},
]

TEST_RESULTS: list[dict[str, Any]] = [
    {
        "java_class": "AccountPostingService",
        "method": "postTransaction",
        "status": "pass",
        "duration_ms": 42,
        "message": "过账金额与余额更新符合 COBOL 语义",
        "snippet": (
            "@Test\n"
            "void postTransaction_updatesBalance() {\n"
            "  var result = service.post(new PostCommand(\"10001\", 100.00));\n"
            "  assertThat(result.balance()).isEqualByComparingTo(\"1100.00\");\n"
            "}"
        ),
    },
    {
        "java_class": "AccountQueryService",
        "method": "queryBalance",
        "status": "pass",
        "duration_ms": 28,
        "message": "查询结果与 DBACCES SELECT 一致",
        "snippet": (
            "@Test\n"
            "void queryBalance_returnsStoredValue() {\n"
            "  when(repo.findByAccountNo(\"10001\")).thenReturn(Optional.of(entity(1000)));\n"
            "  assertThat(service.queryBalance(\"10001\")).isEqualByComparingTo(\"1000\");\n"
            "}"
        ),
    },
    {
        "java_class": "AccountRepository",
        "method": "findByAccountNo",
        "status": "pass",
        "duration_ms": 19,
        "message": "Native Query 参数绑定正确",
        "snippet": "@Test\nvoid findByAccountNo_mapsSqlParams() { /* ... */ }",
    },
    {
        "java_class": "LegacyFileGateway",
        "method": "readBatchFile",
        "status": "warn",
        "duration_ms": 65,
        "message": "空文件边界用例未覆盖 REWRITE 分支",
        "snippet": "@Test\nvoid readBatchFile_emptyFile_warnsOnRewrite() { /* TODO */ }",
    },
    {
        "java_class": "AccountApiController",
        "method": "inquiry",
        "status": "pass",
        "duration_ms": 31,
        "message": "REST 入参与 COMMAREA 字段映射一致",
        "snippet": "@Test\nvoid inquiry_mapsCommareaFields() { /* ... */ }",
    },
]

PROJECT_TREE: list[dict[str, Any]] = [
    {
        "label": "spring-boot-bank-acct",
        "children": [
            {
                "label": "src/main/java/com/bank/acct",
                "children": [
                    {"label": "web/AccountApiController.java"},
                    {"label": "service/AccountPostingService.java"},
                    {"label": "service/AccountQueryService.java"},
                    {"label": "repository/AccountRepository.java"},
                    {"label": "domain/CustomerRecord.java"},
                    {"label": "domain/AccountRecord.java"},
                    {"label": "io/LegacyFileGateway.java"},
                    {"label": "job/BatchPostingJob.java"},
                ],
            },
            {
                "label": "src/test/java/com/bank/acct",
                "children": [
                    {"label": "service/AccountPostingServiceTest.java"},
                    {"label": "service/AccountQueryServiceTest.java"},
                ],
            },
            {"label": "src/main/resources/application.yml"},
        ],
    }
]

CODE_PAIRS: list[dict[str, Any]] = [
    {
        "cobol_file": "ACCTPOST.cbl",
        "java_file": "AccountPostingService.java",
        "cobol_snippet": (
            "POST-TRANSACTION.\n"
            "    MOVE ACCT-NO TO DB-KEY\n"
            "    CALL 'DBACCES' USING WS-DB-REQUEST\n"
            "    ADD WS-AMOUNT TO WS-BALANCE\n"
            "    CALL 'AUDITLOG' USING WS-AUDIT-REC."
        ),
        "java_snippet": (
            "@Service\n"
            "public class AccountPostingService {\n"
            "  public PostResult post(PostCommand cmd) {\n"
            "    var acct = repository.findByAccountNo(cmd.accountNo());\n"
            "    acct.addAmount(cmd.amount());\n"
            "    auditLog.append(cmd.toAuditRecord());\n"
            "    return PostResult.of(acct.getBalance());\n"
            "  }\n"
            "}"
        ),
    },
    {
        "cobol_file": "DBACCES.cbl",
        "java_file": "AccountRepository.java",
        "cobol_snippet": (
            "EXEC SQL\n"
            "  SELECT BALANCE INTO :WS-BALANCE\n"
            "  FROM ACCT_TBL WHERE ACCT_NO = :WS-ACCT-NO\n"
            "END-EXEC."
        ),
        "java_snippet": (
            "@Query(\"SELECT balance FROM acct_tbl WHERE acct_no = :acctNo\")\n"
            "Optional<BigDecimal> findBalanceByAccountNo(@Param(\"acctNo\") String acctNo);"
        ),
    },
]

BUSINESS_CHAINS: list[dict[str, Any]] = [
    {
        "name": "账户查询",
        "status": "pass",
        "nodes": ["INTFAPI", "ACCTINQ", "DBACCES", "AccountApiController", "AccountQueryService", "AccountRepository"],
    },
    {
        "name": "账户过账",
        "status": "pass",
        "nodes": ["INTFAPI", "ACCTPOST", "DBACCES", "AUDITLOG", "AccountPostingService", "AccountRepository"],
    },
    {
        "name": "批处理入账",
        "status": "warn",
        "nodes": ["BATCHJOB", "FILEIO", "ACCTPOST", "BatchPostingJob", "LegacyFileGateway"],
        "gap": "文件读取失败时缺少 @Transactional 回滚补偿",
    },
]


def _step_agents(step: int) -> list[AgentStepData]:
    builders = {
        1: _agents_scan,
        2: _agents_classify,
        3: _agents_rag,
        4: _agents_graph,
        5: _agents_translate,
        6: _agents_validate,
        7: _agents_test,
    }
    return builders[step]()


def _agents_scan() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="扫描 Agent",
            role="遍历遗留工程目录",
            input=f"root={DEMO_ROOT}, pattern=**/*.{{cbl,cpy}}",
            output="发现 32 个候选文件（.cbl 26 / .cpy 6），已过滤备份与编译产物",
            meta="files=32",
        ),
        AgentStepData(
            agent="扫描 Agent",
            role="提取文件元数据",
            input="对 32 个文件统计行数、扩展名、相对路径",
            output="生成文件清单，代表性样本 12 条已附在 payload.files",
            meta="sample=12",
        ),
    ]


def _agents_classify() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="分类 Agent",
            role="识别程序角色",
            input="基于 DIVISION 结构、CALL/COPY、EXEC SQL 等特征",
            output="12/12 样本已标注：业务逻辑 2、DB 访问 2、接口 2、COPYBOOK 2、批处理/报表/审计等",
            meta="types=8",
        ),
        AgentStepData(
            agent="分类 Agent",
            role="输出迁移优先级",
            input="依赖 COPYBOOK 与 DB 模块的文件",
            output="建议顺序：COPYBOOK → DBACCES → ACCTPOST → MAINACCT → 接口层",
        ),
    ]


def _agents_rag() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="RAG 入库 Agent",
            role="切块与向量化",
            input="段落、SQL、CALL、COPY 字段定义",
            output="写入 128 个 chunk（dim=1536），覆盖 32 个源文件",
            meta="chunks=128",
        ),
        AgentStepData(
            agent="RAG 入库 Agent",
            role="建立检索索引",
            input="metadata: file, paragraph, tags",
            output="索引就绪，可按「账户过账」「余额查询」等语义检索相关片段",
        ),
    ]


def _agents_graph() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="依赖图 Agent",
            role="解析 CALL / COPY 引用",
            input="32 个文件的符号表与交叉引用",
            output="识别 24 个节点、37 条边（CALL 28 / COPY 9）",
            meta="nodes=24,edges=37",
        ),
        AgentStepData(
            agent="依赖图 Agent",
            role="写入图数据库（示范）",
            input="节点=程序/模块，边=CALL|COPY",
            output="图库已保存；可用图查询解释「MAINACCT 到 DB 的调用链」",
        ),
    ]


def _agents_translate() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="翻译 Agent",
            role="COBOL → Java 语义转换",
            input="结合 RAG 检索结果与 Spring Boot 模板约定",
            output="生成 18 个 Java 源文件草案，映射到 Controller/Service/Repository/Domain",
            meta="java_files=18",
        ),
        AgentStepData(
            agent="落位 Agent",
            role="对齐 Spring Boot 目录",
            input="template=spring-boot-bank-acct",
            output="已写入 com.bank.acct 包结构，批处理入口映射为 @Scheduled 任务",
        ),
    ]


def _agents_validate() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="验证 Agent",
            role="检查分层与包路径",
            input="对比分类结果与 Java 落位清单",
            output="4 项通过，1 项警告（批处理回滚分支）",
            meta="pass=4,warn=1",
        ),
        AgentStepData(
            agent="验证 Agent",
            role="业务闭环分析",
            input="从 INTFAPI  inquiry/post 到 DBACCES 的端到端链路",
            output="查询与过账主链路闭环；批处理文件失败重试待补全",
        ),
    ]


def _agents_test() -> list[AgentStepData]:
    return [
        AgentStepData(
            agent="测试 Agent",
            role="生成 snippet 测试",
            input="对每个 Service/Repository 公共方法生成 JUnit 片段",
            output="共 15 个 snippet，已自动执行",
            meta="snippets=15",
        ),
        AgentStepData(
            agent="测试 Agent",
            role="汇总测试结果",
            input="执行报告",
            output="13 通过，1 警告（文件网关边界用例），1 跳过（需集成 DB）",
            meta="pass=13,warn=1,skip=1",
        ),
    ]


def _payload(step: int) -> dict[str, Any]:
    if step == 1:
        return {
            "total_files": 32,
            "cbl_count": 26,
            "cpy_count": 6,
            "root": DEMO_ROOT,
            "files": SCANNED_FILES,
        }
    if step == 2:
        return {"classifications": CLASSIFICATIONS, "type_summary": _type_summary()}
    if step == 3:
        return {
            "chunk_count": 128,
            "embedding_dim": 1536,
            "samples": RAG_CHUNKS,
        }
    if step == 4:
        return {
            "node_count": 24,
            "edge_count": 37,
            "nodes": GRAPH_NODES,
            "edges": GRAPH_EDGES,
        }
    if step == 5:
        return {
            "template": "spring-boot-bank-acct",
            "java_file_count": 18,
            "mappings": JAVA_MAPPINGS,
            "project_tree": PROJECT_TREE,
            "code_pairs": CODE_PAIRS,
        }
    if step == 6:
        return {
            "overall": "warn",
            "summary": "主业务链路可闭环，批处理回滚需人工复核",
            "items": VALIDATION_ITEMS,
            "business_chains": BUSINESS_CHAINS,
        }
    if step == 7:
        return {
            "total": 15,
            "passed": 13,
            "warned": 1,
            "skipped": 1,
            "results": TEST_RESULTS,
        }
    raise ValueError(f"unknown step: {step}")


def _type_summary() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in CLASSIFICATIONS:
        counts[row["type"]] = counts.get(row["type"], 0) + 1
    return [{"type": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]


def run_step(step: int) -> tuple[int, str, list[AgentStepData], dict[str, Any]]:
    if step < 1 or step > 7:
        raise ValueError("step must be between 1 and 7")
    return step, STEP_NAMES[step], _step_agents(step), _payload(step)


def run_pipeline() -> list[tuple[int, str, list[AgentStepData], dict[str, Any]]]:
    return [run_step(n) for n in range(1, 8)]
