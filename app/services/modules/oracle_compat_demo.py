"""用已安装的 orafce（oracle 模式）跑常见 Oracle 函数，并和同义 PG 写法比耗时。"""

from __future__ import annotations

import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

BENCH_MIN = 1000
BENCH_MAX = 100_000
BENCH_DEFAULT = 20_000
TIMING_REPEATS = 3

EMP_FIELDS = [
    "empno",
    "ename",
    "job",
    "job_code",
    "mgr",
    "hiredate",
    "birthdate",
    "sal",
    "comm",
    "bonus",
    "commission_rate",
    "deptno",
    "email",
    "phone",
    "grade",
    "status",
    "city",
    "remark",
]
DEPT_FIELDS = ["deptno", "dname", "loc", "region", "cost_center", "budget"]


def _require_orafce(db: Session) -> str:
    row = db.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'orafce'")).first()
    if row is None:
        raise RuntimeError("当前库没有 orafce，装上插件后再测")
    return str(row[0])


def _table_count(db: Session, table: str) -> int:
    try:
        with db.begin_nested():
            value = db.execute(text(f"SELECT count(*) FROM ora_demo.{table}")).scalar()
        return int(value or 0)
    except Exception:
        return 0


def extension_status(db: Session) -> dict[str, Any]:
    row = db.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'orafce'")).first()
    return {
        "installed": row is not None,
        "version": None if row is None else str(row[0]),
        "schema": "oracle",
        "emp_rows": _table_count(db, "emp"),
        "bench_rows": _table_count(db, "emp_bench"),
        "emp_fields": EMP_FIELDS,
        "dept_fields": DEPT_FIELDS,
    }


def _clamp_rows(rows: int) -> int:
    try:
        value = int(rows)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("行数必须是整数") from exc
    if value < BENCH_MIN or value > BENCH_MAX:
        raise RuntimeError(f"性能表行数需在 {BENCH_MIN} 到 {BENCH_MAX} 之间")
    return value


def seed_data(db: Session, rows: int = BENCH_DEFAULT) -> dict[str, Any]:
    version = _require_orafce(db)
    add_rows = _clamp_rows(rows)
    db.execute(text("CREATE SCHEMA IF NOT EXISTS ora_demo"))
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS ora_demo.dept (
                deptno integer PRIMARY KEY,
                dname text NOT NULL,
                loc text NOT NULL,
                region text NOT NULL,
                cost_center text NOT NULL,
                budget numeric(12, 2) NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS ora_demo.emp (
                empno integer PRIMARY KEY,
                ename text NOT NULL,
                job text NOT NULL,
                job_code text NOT NULL,
                mgr integer NOT NULL,
                hiredate date NOT NULL,
                birthdate date NOT NULL,
                sal numeric(10, 2) NOT NULL,
                comm numeric(10, 2) NOT NULL,
                bonus double precision NOT NULL,
                commission_rate numeric(8, 4) NOT NULL,
                deptno integer NOT NULL,
                email text NOT NULL,
                phone text NOT NULL,
                grade text NOT NULL,
                status text NOT NULL,
                city text NOT NULL,
                remark text NOT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS ora_demo.emp_bench (LIKE ora_demo.emp INCLUDING DEFAULTS)
            """
        )
    )
    if _table_count(db, "dept") == 0:
        db.execute(
            text(
                """
                INSERT INTO ora_demo.dept (deptno, dname, loc, region, cost_center, budget) VALUES
                (10, 'ACCOUNTING', 'NEW YORK', 'EAST', 'CC-10', 500000),
                (20, 'RESEARCH', 'DALLAS', 'CENTRAL', 'CC-20', 800000),
                (30, 'SALES', 'CHICAGO', 'CENTRAL', 'CC-30', 650000),
                (40, 'OPERATIONS', 'BOSTON', 'EAST', 'CC-40', 400000)
                """
            )
        )
    if _table_count(db, "emp") == 0:
        db.execute(
            text(
                """
                INSERT INTO ora_demo.emp (
                    empno, ename, job, job_code, mgr, hiredate, birthdate, sal, comm, bonus,
                    commission_rate, deptno, email, phone, grade, status, city, remark
                ) VALUES
                (7369, 'SMITH', 'CLERK', 'CLK', 7902, DATE '1980-12-17', DATE '1955-03-08', 800, 0, 120,
                    0, 20, 'smith7369@example.com', '13800007369', 'G1', 'A', 'DALLAS', '档案完整'),
                (7499, 'ALLEN', 'SALESMAN', 'SAL', 7698, DATE '1981-02-20', DATE '1956-07-14', 1600, 300, 80,
                    0.0800, 30, 'allen7499@example.com', '13800007499', 'G2', 'A', 'CHICAGO', '有佣金'),
                (7521, 'WARD', 'SALESMAN', 'SAL', 7698, DATE '1981-02-22', DATE '1958-11-02', 1250, 500, 60,
                    0.1000, 30, 'ward7521@example.com', '13800007521', 'G1', 'A', 'CHICAGO', '有佣金'),
                (7566, 'JONES', 'MANAGER', 'MGR', 7839, DATE '1981-04-02', DATE '1952-01-19', 2975, 0, 200,
                    0.0200, 20, 'jones7566@example.com', '13800007566', 'G3', 'A', 'DALLAS', '部门经理'),
                (7654, 'MARTIN', 'SALESMAN', 'SAL', 7698, DATE '1981-09-28', DATE '1957-09-28', 1250, 1400, 40,
                    0.1200, 30, 'martin7654@example.com', '13800007654', 'G1', 'P', 'CHICAGO', '试用'),
                (7698, 'BLAKE', 'MANAGER', 'MGR', 7839, DATE '1981-05-01', DATE '1950-05-01', 2850, 0, 180,
                    0.0200, 30, 'blake7698@example.com', '13800007698', 'G3', 'A', 'CHICAGO', '部门经理'),
                (7782, 'CLARK', 'MANAGER', 'MGR', 7839, DATE '1981-06-09', DATE '1951-06-09', 2450, 0, 150,
                    0.0200, 10, 'clark7782@example.com', '13800007782', 'G2', 'A', 'NEW YORK', '部门经理'),
                (7788, 'SCOTT', 'ANALYST', 'ANA', 7566, DATE '1987-04-19', DATE '1959-04-19', 3000, 0, 260,
                    0, 20, 'scott7788@example.com', '13800007788', 'G3', 'A', 'DALLAS', '分析师'),
                (7839, 'KING', 'PRESIDENT', 'PRE', 0, DATE '1981-11-17', DATE '1948-11-17', 5000, 0, 500,
                    0, 10, 'king7839@example.com', '13800007839', 'G4', 'A', 'NEW YORK', '总裁'),
                (7844, 'TURNER', 'SALESMAN', 'SAL', 7698, DATE '1981-09-08', DATE '1956-09-08', 1500, 0, 20,
                    0.0500, 30, 'turner7844@example.com', '13800007844', 'G2', 'L', 'CHICAGO', '佣金为 0，已离职'),
                (7876, 'ADAMS', 'CLERK', 'CLK', 7788, DATE '1987-05-23', DATE '1962-05-23', 1100, 0, 30,
                    0, 20, 'adams7876@example.com', '13800007876', 'G1', 'A', 'DALLAS', '文员'),
                (7900, 'JAMES', 'CLERK', 'CLK', 7698, DATE '1981-12-03', DATE '1954-12-03', 950, 0, 15,
                    0, 30, 'james7900@example.com', '13800007900', 'G1', 'A', 'CHICAGO', '文员'),
                (7902, 'FORD', 'ANALYST', 'ANA', 7566, DATE '1981-12-03', DATE '1953-12-03', 3000, 0, 240,
                    0, 20, 'ford7902@example.com', '13800007902', 'G3', 'A', 'DALLAS', '分析师'),
                (7934, 'MILLER', 'CLERK', 'CLK', 7782, DATE '1982-01-23', DATE '1960-01-23', 1300, 0, 90,
                    0, 10, 'miller7934@example.com', '13800007934', 'G1', 'A', 'NEW YORK', '文员')
                """
            )
        )
    start = int(
        db.execute(text("SELECT coalesce(max(empno), 0) FROM ora_demo.emp_bench")).scalar() or 0
    )
    db.execute(
        text(
            """
            INSERT INTO ora_demo.emp_bench (
                empno, ename, job, job_code, mgr, hiredate, birthdate, sal, comm, bonus,
                commission_rate, deptno, email, phone, grade, status, city, remark
            )
            SELECT
                :start + g,
                'N' || lpad((:start + g)::text, 5, '0'),
                (ARRAY['CLERK', 'SALESMAN', 'MANAGER', 'ANALYST'])[1 + ((:start + g) % 4)],
                (ARRAY['CLK', 'SAL', 'MGR', 'ANA'])[1 + ((:start + g) % 4)],
                CASE WHEN (:start + g) % 9 = 0 THEN 0 ELSE 1000 + ((:start + g) % 50) END,
                DATE '2010-01-01' + ((:start + g) % 4000),
                DATE '1980-01-01' + ((:start + g) % 5000),
                (3000 + ((:start + g) % 7000))::numeric(10, 2),
                ((:start + g) % 1500)::numeric(10, 2),
                ((:start + g) % 800)::float8,
                CASE WHEN (:start + g) % 4 = 1 THEN 0.0800 ELSE 0 END,
                (ARRAY[10, 20, 30, 40])[1 + ((:start + g) % 4)],
                'n' || (:start + g)::text || '@example.com',
                '138' || lpad(((:start + g) % 100000000)::text, 8, '0'),
                (ARRAY['G1', 'G2', 'G3', 'G4', 'G5'])[1 + ((:start + g) % 5)],
                (ARRAY['A', 'A', 'A', 'L', 'P'])[1 + ((:start + g) % 5)],
                (ARRAY['NEW YORK', 'DALLAS', 'CHICAGO', 'BOSTON'])[1 + ((:start + g) % 4)],
                '备注' || ((:start + g) % 50)::text
            FROM generate_series(1, :rows) AS g
            """
        ),
        {"rows": add_rows, "start": start},
    )
    db.commit()
    return {
        "installed": True,
        "version": version,
        "emp_rows": _table_count(db, "emp"),
        "dept_rows": _table_count(db, "dept"),
        "bench_rows": _table_count(db, "emp_bench"),
        "added_rows": add_rows,
        "emp_fields": EMP_FIELDS,
        "dept_fields": DEPT_FIELDS,
    }


def clear_data(db: Session) -> dict[str, Any]:
    db.execute(text("DROP TABLE IF EXISTS ora_demo.emp_bench"))
    db.execute(text("DROP TABLE IF EXISTS ora_demo.emp"))
    db.execute(text("DROP TABLE IF EXISTS ora_demo.dept"))
    db.commit()
    return extension_status(db)


def _expr_bench(expr: str) -> str:
    return f"""
        SELECT count(*)::int, coalesce(sum(hashtext(result::text)), 0)
        FROM (SELECT {expr} AS result FROM ora_demo.emp_bench) s
    """


def _group_bench(expr: str) -> str:
    return f"""
        SELECT count(*)::int, coalesce(sum(hashtext(coalesce(result::text, ''))), 0)
        FROM (
            SELECT deptno, {expr} AS result
            FROM ora_demo.emp_bench
            GROUP BY deptno
        ) s
    """


def _cases() -> list[dict[str, Any]]:
    decode_plugin = (
        "oracle.decode(status, 'A'::text, '在职'::text, 'L'::text, '离职'::text, "
        "'P'::text, '试用'::text, '未知'::text)"
    )
    decode_native = (
        "CASE status WHEN 'A' THEN '在职' WHEN 'L' THEN '离职' WHEN 'P' THEN '试用' ELSE '未知' END"
    )
    return [
        {
            "id": "nvl",
            "category": "空值",
            "fn": "oracle.nvl",
            "what": "字面量 NULL 补 0；表内佣金全非空时结果不变",
            "note": "和 COALESCE 一样，只替换 NULL。样本表字段均非空，空值用字面量验证。",
            "sample_sql": """
                SELECT
                    oracle.nvl(NULL::numeric, 0)::text AS null_plugin,
                    COALESCE(NULL::numeric, 0)::text AS null_native,
                    empno, ename, comm::text AS comm,
                    oracle.nvl(comm, 0)::text AS plugin,
                    COALESCE(comm, 0)::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.nvl(NULL::numeric, 0) = 0
                   AND oracle.nvl(300::numeric, 0) = 300
                   AND bool_and(oracle.nvl(comm, 0) = COALESCE(comm, 0))
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench(
                "oracle.nvl(CASE WHEN empno % 7 = 0 THEN NULL::numeric ELSE comm END, 0)"
            ),
            "native_bench": _expr_bench(
                "COALESCE(CASE WHEN empno % 7 = 0 THEN NULL::numeric ELSE comm END, 0)"
            ),
        },
        {
            "id": "nvl2",
            "category": "空值",
            "fn": "oracle.nvl2",
            "what": "有值（含 0）走第二参数，字面量 NULL 走第三参数",
            "note": "0 不是 NULL。表内字段均非空；NULL 分支用字面量验证。",
            "sample_sql": """
                SELECT
                    oracle.nvl2(NULL::numeric, 9::numeric, 1::numeric)::text AS null_plugin,
                    (CASE WHEN NULL::numeric IS NOT NULL THEN 9 ELSE 1 END)::text AS null_native,
                    empno, ename, sal::text AS sal, comm::text AS comm,
                    oracle.nvl2(comm, sal + comm, sal)::text AS plugin,
                    (CASE WHEN comm IS NOT NULL THEN sal + comm ELSE sal END)::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.nvl2(NULL::numeric, 9::numeric, 1::numeric) = 1
                   AND oracle.nvl2(0::numeric, 9::numeric, 1::numeric) = 9
                   AND bool_and(
                        oracle.nvl2(comm, sal + comm, sal)
                        = CASE WHEN comm IS NOT NULL THEN sal + comm ELSE sal END
                   )
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench(
                "oracle.nvl2("
                "CASE WHEN empno % 7 = 0 THEN NULL::numeric ELSE comm END, "
                "sal + coalesce(comm, 0), sal)"
            ),
            "native_bench": _expr_bench(
                "CASE WHEN (CASE WHEN empno % 7 = 0 THEN NULL::numeric ELSE comm END) "
                "IS NOT NULL THEN sal + coalesce(comm, 0) ELSE sal END"
            ),
        },
        {
            "id": "decode",
            "category": "空值",
            "fn": "oracle.decode",
            "what": "把状态码 A/L/P 译成在职、离职、试用",
            "note": "字面量要带 text 类型，否则 orafce 的多态重载选不出来。",
            "sample_sql": f"""
                SELECT empno, ename, status, grade, city,
                       {decode_plugin} AS plugin,
                       {decode_native} AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": f"""
                SELECT bool_and({decode_plugin} = {decode_native}) FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench(decode_plugin),
            "native_bench": _expr_bench(decode_native),
        },
        {
            "id": "nanvl",
            "category": "空值",
            "fn": "oracle.nanvl",
            "what": "字面量 NaN 改成 0；表内奖金全是正常数",
            "note": "样本表不存 NaN。用字面量区分「非数」和「正常值」。",
            "sample_sql": """
                SELECT
                    oracle.nanvl('NaN'::float8, 0)::text AS nan_plugin,
                    0::float8::text AS nan_native,
                    empno, ename, bonus::text AS bonus,
                    oracle.nanvl(bonus, 0)::text AS plugin,
                    bonus::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.nanvl('NaN'::float8, 0) = 0
                   AND oracle.nanvl(12::float8, 0) = 12
                   AND bool_and(oracle.nanvl(bonus, 0) = bonus)
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench(
                "oracle.nanvl(CASE WHEN empno % 97 = 0 THEN 'NaN'::float8 ELSE bonus END, 0)"
            ),
            "native_bench": _expr_bench(
                "CASE WHEN (CASE WHEN empno % 97 = 0 THEN 'NaN'::float8 ELSE bonus END) "
                "= 'NaN'::float8 THEN 0::float8 ELSE bonus END"
            ),
        },
        {
            "id": "instr",
            "category": "字符串",
            "fn": "oracle.instr",
            "what": "在邮箱里找 @ 的位置",
            "note": "位置从 1 开始，找不到返回 0，和 strpos 一致。",
            "sample_sql": """
                SELECT empno, ename, email,
                       oracle.instr(email, '@')::text AS plugin,
                       strpos(email, '@')::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT bool_and(oracle.instr(email, '@') = strpos(email, '@')) FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.instr(email, '@')"),
            "native_bench": _expr_bench("strpos(email, '@')"),
        },
        {
            "id": "substr",
            "category": "字符串",
            "fn": "oracle.substr",
            "what": "截取姓名前 3 个字符，岗位码原样对照",
            "note": "起点按 1 计，和 substring(text from start for len) 一致。",
            "sample_sql": """
                SELECT empno, ename, job_code,
                       oracle.substr(ename, 1, 3) AS plugin,
                       substring(ename from 1 for 3) AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT bool_and(oracle.substr(ename, 1, 3) = substring(ename from 1 for 3))
                   AND bool_and(oracle.substr(job_code, 1, 2) = substring(job_code from 1 for 2))
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.substr(ename, 1, 3)"),
            "native_bench": _expr_bench("substring(ename from 1 for 3)"),
        },
        {
            "id": "regexp_substr",
            "category": "字符串",
            "fn": "oracle.regexp_substr",
            "what": "从电话号码取出末 4 位",
            "note": "这套 orafce 的正则用 [0-9]，不要写 \\d。",
            "sample_sql": """
                SELECT empno, ename, phone,
                       oracle.regexp_substr(phone, '[0-9]{4}$') AS plugin,
                       substring(phone from '[0-9]{4}$') AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT bool_and(
                    oracle.regexp_substr(phone, '[0-9]{4}$')
                    IS NOT DISTINCT FROM substring(phone from '[0-9]{4}$')
                ) FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.regexp_substr(phone, '[0-9]{4}$')"),
            "native_bench": _expr_bench("substring(phone from '[0-9]{4}$')"),
        },
        {
            "id": "add_months",
            "category": "日期",
            "fn": "oracle.add_months",
            "what": "入职日加 6 个月",
            "note": "可用性用非月末日期断言。月末时 add_months 和 interval 可能差一天。",
            "sample_sql": """
                SELECT empno, ename, hiredate::text AS hiredate, birthdate::text AS birthdate,
                       oracle.add_months(hiredate, 6)::text AS plugin,
                       (hiredate + interval '6 months')::date::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.add_months(DATE '1981-12-03', 2) = DATE '1982-02-03'
                   AND bool_and(oracle.add_months(hiredate, 6) = (hiredate + interval '6 months')::date)
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.add_months(hiredate, 6)"),
            "native_bench": _expr_bench("(hiredate + interval '6 months')::date"),
        },
        {
            "id": "months_between",
            "category": "日期",
            "fn": "oracle.months_between",
            "what": "入职日到 1982-01-23 的月数，带日差小数",
            "note": "Oracle 用「整月 + 日差/31」。对照的 age 只取整月，倍数只说明耗时。",
            "sample_sql": """
                SELECT empno, ename, hiredate::text AS hiredate,
                       oracle.months_between(DATE '1982-01-23', hiredate)::text AS plugin,
                       (EXTRACT(YEAR FROM age(DATE '1982-01-23', hiredate)) * 12
                        + EXTRACT(MONTH FROM age(DATE '1982-01-23', hiredate)))::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT abs(oracle.months_between(DATE '1982-01-23', DATE '1981-12-03') - 1.64516129032258) < 0.000001
            """,
            "plugin_bench": _expr_bench("oracle.months_between(DATE '2024-06-15', hiredate)"),
            "native_bench": _expr_bench(
                "EXTRACT(YEAR FROM age(DATE '2024-06-15', hiredate)) * 12"
                " + EXTRACT(MONTH FROM age(DATE '2024-06-15', hiredate))"
            ),
        },
        {
            "id": "last_day",
            "category": "日期",
            "fn": "oracle.last_day",
            "what": "出生日期所在月的最后一天",
            "note": "1981-02 应为 28 日，闰年 2 月应为 29 日。",
            "sample_sql": """
                SELECT empno, ename, birthdate::text AS birthdate,
                       oracle.last_day(birthdate)::text AS plugin,
                       (date_trunc('month', birthdate) + interval '1 month - 1 day')::date::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.last_day(DATE '1981-02-20') = DATE '1981-02-28'
                   AND oracle.last_day(DATE '2024-02-01') = DATE '2024-02-29'
                   AND bool_and(
                        oracle.last_day(birthdate)
                        = (date_trunc('month', birthdate) + interval '1 month - 1 day')::date
                   )
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.last_day(birthdate)"),
            "native_bench": _expr_bench("(date_trunc('month', birthdate) + interval '1 month - 1 day')::date"),
        },
        {
            "id": "trunc",
            "category": "日期",
            "fn": "oracle.trunc",
            "what": "把入职日截到当月 1 日",
            "note": "格式串 MM 对应 date_trunc('month')。",
            "sample_sql": """
                SELECT empno, ename, hiredate::text AS hiredate,
                       oracle.trunc(hiredate, 'MM')::text AS plugin,
                       date_trunc('month', hiredate)::date::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.trunc(DATE '1981-12-03', 'MM') = DATE '1981-12-01'
                   AND bool_and(oracle.trunc(hiredate, 'MM') = date_trunc('month', hiredate)::date)
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.trunc(hiredate, 'MM')"),
            "native_bench": _expr_bench("date_trunc('month', hiredate)::date"),
        },
        {
            "id": "to_char",
            "category": "日期",
            "fn": "oracle.to_char",
            "what": "把工资数值转成文本",
            "note": "当前 orafce 没有 oracle.to_char(timestamp, 格式串)。日期格式化仍用 PG 自带 to_char。",
            "sample_sql": """
                SELECT empno, ename, sal::text AS sal,
                       oracle.to_char(sal) AS plugin,
                       sal::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.to_char(800::numeric) IS NOT NULL
                   AND length(oracle.to_char(800::numeric)) > 0
                   AND bool_and(oracle.to_char(sal) IS NOT NULL)
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.to_char(sal)"),
            "native_bench": _expr_bench("sal::text"),
        },
        {
            "id": "to_date",
            "category": "日期",
            "fn": "oracle.to_date",
            "what": "把入职日格式化后再按 YYYY-MM-DD 解析回来",
            "note": "返回 timestamp。对照 PG 的 to_date。格式串那一步用的是 pg_catalog.to_char。",
            "sample_sql": """
                SELECT empno, ename, hiredate::text AS hiredate,
                       oracle.to_date(pg_catalog.to_char(hiredate, 'YYYY-MM-DD'), 'YYYY-MM-DD')::date::text AS plugin,
                       pg_catalog.to_date(pg_catalog.to_char(hiredate, 'YYYY-MM-DD'), 'YYYY-MM-DD')::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.to_date('1981-12-03', 'YYYY-MM-DD')::date = DATE '1981-12-03'
                   AND bool_and(
                        oracle.to_date(pg_catalog.to_char(hiredate, 'YYYY-MM-DD'), 'YYYY-MM-DD')::date = hiredate
                   )
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench(
                "oracle.to_date(pg_catalog.to_char(hiredate, 'YYYY-MM-DD'), 'YYYY-MM-DD')"
            ),
            "native_bench": _expr_bench(
                "pg_catalog.to_date(pg_catalog.to_char(hiredate, 'YYYY-MM-DD'), 'YYYY-MM-DD')"
            ),
        },
        {
            "id": "sysdate",
            "category": "日期",
            "fn": "oracle.sysdate",
            "what": "取当前时间，类型是 oracle.date",
            "note": "必须写成函数 oracle.sysdate()，不是无括号的关键字。",
            "sample_sql": """
                SELECT oracle.sysdate()::text AS plugin,
                       localtimestamp::text AS native
            """,
            "check_sql": """
                SELECT abs(extract(epoch FROM (oracle.sysdate()::timestamp - localtimestamp))) < 120
            """,
            "plugin_bench": _expr_bench("oracle.sysdate()::timestamp"),
            "native_bench": _expr_bench("localtimestamp"),
        },
        {
            "id": "listagg",
            "category": "聚合",
            "fn": "oracle.listagg",
            "what": "按部门把岗位码拼成一串",
            "note": "这个版本不支持 WITHIN GROUP (ORDER BY)，顺序不稳定，可用性只核对成员是否齐全。",
            "sample_sql": """
                SELECT deptno,
                       oracle.listagg(job_code, ','::text) AS plugin,
                       string_agg(job_code, ',' ORDER BY job_code) AS native
                FROM ora_demo.emp
                GROUP BY deptno
                ORDER BY deptno
            """,
            "check_sql": """
                SELECT (
                    SELECT array_agg(x ORDER BY x)
                    FROM unnest(string_to_array(
                        (SELECT oracle.listagg(ename, ','::text) FROM ora_demo.emp WHERE deptno = 10),
                        ','
                    )) AS x
                ) = ARRAY['CLARK', 'KING', 'MILLER']::text[]
            """,
            "plugin_bench": _group_bench("oracle.listagg(job_code, ','::text)"),
            "native_bench": _group_bench("string_agg(job_code, ',')"),
        },
        {
            "id": "median",
            "category": "聚合",
            "fn": "oracle.median",
            "what": "按部门求工资中位数",
            "note": "重载是 float8。对照 percentile_cont(0.5)。",
            "sample_sql": """
                SELECT deptno,
                       oracle.median(sal::float8)::text AS plugin,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY sal)::text AS native
                FROM ora_demo.emp
                GROUP BY deptno
                ORDER BY deptno
            """,
            "check_sql": """
                SELECT (SELECT oracle.median(x) FROM (VALUES (1::float8), (3::float8), (10::float8)) v(x)) = 3
                   AND abs(
                        (SELECT oracle.median(sal::float8) FROM ora_demo.emp)
                        - (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY sal)::float8 FROM ora_demo.emp)
                   ) < 0.01
            """,
            "plugin_bench": _group_bench("oracle.median(sal::float8)"),
            "native_bench": _group_bench("percentile_cont(0.5) WITHIN GROUP (ORDER BY sal)"),
        },
        {
            "id": "round",
            "category": "数值",
            "fn": "oracle.round",
            "what": "工资乘提成比例后保留 2 位小数",
            "note": "10.125 四舍五入到 2 位是 10.13。",
            "sample_sql": """
                SELECT empno, ename, sal::text AS sal, commission_rate::text AS commission_rate,
                       oracle.round(sal * commission_rate, 2)::text AS plugin,
                       round(sal * commission_rate, 2)::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.round(10.125::numeric, 2) = 10.13
                   AND bool_and(oracle.round(sal * commission_rate, 2) = round(sal * commission_rate, 2))
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.round(sal * commission_rate, 2)"),
            "native_bench": _expr_bench("round(sal * commission_rate, 2)"),
        },
        {
            "id": "bitand",
            "category": "数值",
            "fn": "oracle.bitand",
            "what": "工号和 7 做按位与",
            "note": "对照 PG 的 & 运算符。",
            "sample_sql": """
                SELECT empno, ename, job_code,
                       oracle.bitand(empno, 7)::text AS plugin,
                       (empno & 7)::text AS native
                FROM ora_demo.emp ORDER BY empno LIMIT 8
            """,
            "check_sql": """
                SELECT oracle.bitand(7, 3) = 3
                   AND bool_and(oracle.bitand(empno, 7) = (empno & 7))
                FROM ora_demo.emp
            """,
            "plugin_bench": _expr_bench("oracle.bitand(empno, 7)"),
            "native_bench": _expr_bench("(empno & 7)"),
        },
    ]


def _cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if value != value:
            return "NaN"
        return value
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _sample(db: Session, sql: str) -> list[dict[str, Any]]:
    with db.begin_nested():
        rows = db.execute(text(sql)).mappings().all()
    return [{key: _cell(val) for key, val in row.items()} for row in rows]


def _check(db: Session, sql: str) -> bool:
    with db.begin_nested():
        value = db.execute(text(sql)).scalar()
    return bool(value)


def _time_sql(db: Session, sql: str) -> float:
    with db.begin_nested():
        db.execute(text(sql)).scalar()
    samples: list[float] = []
    for _ in range(TIMING_REPEATS):
        started = time.perf_counter()
        with db.begin_nested():
            db.execute(text(sql)).scalar()
        samples.append((time.perf_counter() - started) * 1000)
    samples.sort()
    return round(samples[len(samples) // 2], 2)


def _verdict(usable: bool, plugin_ms: float | None, native_ms: float | None) -> str:
    if not usable or plugin_ms is None:
        return "不可用"
    if native_ms is None or native_ms <= 0:
        return "可用" if plugin_ms < 200 else "偏慢"
    ratio = plugin_ms / native_ms
    if plugin_ms < 15 and native_ms < 15:
        return "可接受"
    if ratio <= 2:
        return "可接受"
    if ratio <= 4:
        return "略慢"
    return "偏慢"


def _short_error(exc: Exception) -> str:
    message = str(exc).strip().splitlines()[0]
    return message[:240]


def _norm_sql(sql: str) -> str:
    return str(sql or "").strip()


_FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do|execute|vacuum|reindex|cluster|comment|security|set\s+role|set\s+session)\b",
    re.IGNORECASE,
)


def _assert_readonly_select(sql: str, label: str) -> str:
    cleaned = _norm_sql(sql)
    if not cleaned:
        raise RuntimeError(f"{label} 不能为空")
    if ";" in cleaned.rstrip(";"):
        raise RuntimeError(f"{label} 只允许一条语句")
    body = cleaned.rstrip(";").strip()
    if _FORBIDDEN_SQL.search(body):
        raise RuntimeError(f"{label} 只允许只读 SELECT")
    head = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL).lstrip()
    head = re.sub(r"--.*?$", "", head, flags=re.MULTILINE).lstrip()
    if not re.match(r"^(with|select)\b", head, flags=re.IGNORECASE):
        raise RuntimeError(f"{label} 必须以 SELECT 或 WITH 开头")
    return body


def _case_meta(case_id: str) -> dict[str, Any]:
    for spec in _cases():
        if spec["id"] == case_id:
            return spec
    raise RuntimeError(f"没有这个用例：{case_id}")


def _run_case(db: Session, spec: dict[str, Any]) -> dict[str, Any]:
    sample_sql = _norm_sql(spec["sample_sql"])
    check_sql = _norm_sql(spec["check_sql"])
    plugin_bench = _norm_sql(spec["plugin_bench"])
    native_bench = _norm_sql(spec["native_bench"])
    item: dict[str, Any] = {
        "id": spec["id"],
        "category": spec["category"],
        "fn": spec["fn"],
        "what": spec["what"],
        "note": spec["note"],
        "sample_sql": sample_sql,
        "check_sql": check_sql,
        "plugin_bench": plugin_bench,
        "native_bench": native_bench,
        "usable": False,
        "error": None,
        "sample": [],
        "plugin_ms": None,
        "native_ms": None,
        "ratio": None,
        "verdict": "不可用",
    }
    try:
        item["sample"] = _sample(db, sample_sql)
        item["usable"] = _check(db, check_sql)
        if not item["usable"]:
            item["error"] = "能调用，但结果和预期不一致"
    except Exception as exc:
        item["usable"] = False
        item["error"] = _short_error(exc)
        return item
    try:
        item["plugin_ms"] = _time_sql(db, plugin_bench)
    except Exception as exc:
        item["usable"] = False
        item["error"] = _short_error(exc)
        item["verdict"] = "不可用"
        return item
    try:
        item["native_ms"] = _time_sql(db, native_bench)
    except Exception as exc:
        item["error"] = "对照 SQL 失败: " + _short_error(exc)
    if item["plugin_ms"] is not None and item["native_ms"]:
        item["ratio"] = round(item["plugin_ms"] / item["native_ms"], 2)
    item["verdict"] = _verdict(item["usable"], item["plugin_ms"], item["native_ms"])
    return item


def _summarize(version: str, emp_rows: int, bench_rows: int, cases: list[dict[str, Any]], wall_ms: float) -> dict[str, Any]:
    usable = sum(1 for item in cases if item["usable"])
    summary = {
        "total": len(cases),
        "usable": usable,
        "failed": len(cases) - usable,
        "acceptable": sum(1 for item in cases if item["verdict"] == "可接受"),
        "slowish": sum(1 for item in cases if item["verdict"] == "略慢"),
        "slow": sum(1 for item in cases if item["verdict"] == "偏慢"),
        "plugin_ms": round(sum(item["plugin_ms"] or 0 for item in cases), 2),
        "native_ms": round(sum(item["native_ms"] or 0 for item in cases), 2),
        "wall_ms": wall_ms,
    }
    categories: list[dict[str, Any]] = []
    for name in dict.fromkeys(item["category"] for item in cases):
        group = [item for item in cases if item["category"] == name]
        categories.append(
            {
                "name": name,
                "total": len(group),
                "usable": sum(1 for item in group if item["usable"]),
                "plugin_ms": round(sum(item["plugin_ms"] or 0 for item in group), 2),
                "native_ms": round(sum(item["native_ms"] or 0 for item in group), 2),
            }
        )
    return {
        "summary": summary,
        "categories": categories,
        "analysis": _analysis(version, emp_rows, bench_rows, cases),
    }


def _analysis(version: str, emp_rows: int, bench_rows: int, cases: list[dict[str, Any]]) -> list[str]:
    usable = [item for item in cases if item["usable"]]
    failed = [item for item in cases if not item["usable"]]
    slow = [item for item in cases if item["verdict"] == "偏慢"]
    mild = [item for item in cases if item["verdict"] == "略慢"]
    lines = [
        f"orafce {version}，函数都在 oracle 模式，SQL 写全 oracle.函数名。样例员工 {emp_rows} 行，性能表 {bench_rows} 行。",
        (
            f"可用性：{len(usable)}/{len(cases)} 个按预期返回。"
            + ("失败：" + "、".join(item["fn"] for item in failed) + "。" if failed else "这批函数都可以调用。")
        ),
    ]
    timed = [item for item in usable if item["ratio"] is not None]
    if timed:
        ratios = sorted(item["ratio"] for item in timed)
        median_ratio = ratios[len(ratios) // 2]
        worst = max(timed, key=lambda item: item["ratio"])
        lines.append(
            f"性能：相对同义 PG 写法的耗时倍数中位数是 {median_ratio:.2f}。"
            f"最慢的是 {worst['fn']}，插件 {worst['plugin_ms']} ms，对照 {worst['native_ms']} ms，"
            f"{worst['ratio']:.2f} 倍。"
        )
    if slow:
        lines.append(
            "偏慢（超过 4 倍）："
            + "、".join(item["fn"] for item in slow)
            + "。大批量语句里这些函数要单独看执行时间。"
        )
    elif mild:
        lines.append("没有超过 4 倍的函数。略慢：" + "、".join(item["fn"] for item in mild) + "。")
    else:
        lines.append("在这批行数上，插件耗时相对同义写法可以接受。")
    lines.append(
        "当前扩展没有 oracle.to_char(时间, 格式串)，日期格式化要用 PG 自带 to_char；"
        "本页的 to_char 测的是数值转文本。listagg 能聚合，但不支持 WITHIN GROUP (ORDER BY)。"
    )
    lines.append(
        "计时：每种写法预热 1 次，再跑 3 次取中位数。查询对结果做 hashtext，避免表达式被优化掉。"
        "两边都低于 15 ms 时记为可接受，避免短查询的倍数抖动。"
    )
    return lines


_ROW_TABLES = {
    "emp": ("empno", EMP_FIELDS),
    "emp_bench": ("empno", EMP_FIELDS),
    "dept": ("deptno", DEPT_FIELDS),
}


def list_rows(db: Session, table: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    meta = _ROW_TABLES.get(table)
    if meta is None:
        raise RuntimeError("只能查 emp / emp_bench / dept")
    order_col, fields = meta
    try:
        page_num = max(1, int(page))
        size = max(1, min(100, int(page_size)))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("分页参数无效") from exc
    total = _table_count(db, table)
    items: list[dict[str, Any]] = []
    if total > 0:
        cols = ", ".join(fields)
        sql = (
            f"SELECT {cols} FROM ora_demo.{table} "
            f"ORDER BY {order_col} LIMIT :limit OFFSET :offset"
        )
        with db.begin_nested():
            rows = db.execute(
                text(sql),
                {"limit": size, "offset": (page_num - 1) * size},
            ).mappings().all()
        items = [{key: _cell(val) for key, val in row.items()} for row in rows]
    return {
        "table": table,
        "fields": fields,
        "items": items,
        "total": total,
        "page": page_num,
        "page_size": size,
    }


def run_cases(db: Session) -> dict[str, Any]:
    version = _require_orafce(db)
    emp_rows = _table_count(db, "emp")
    bench_rows = _table_count(db, "emp_bench")
    if emp_rows <= 0 or bench_rows <= 0:
        raise RuntimeError("还没有样例数据，先造数再跑")
    started = time.perf_counter()
    cases = [_run_case(db, spec) for spec in _cases()]
    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    db.commit()
    packed = _summarize(version, emp_rows, bench_rows, cases, wall_ms)
    return {
        "installed": True,
        "version": version,
        "schema": "oracle",
        "emp_rows": emp_rows,
        "bench_rows": bench_rows,
        "emp_fields": EMP_FIELDS,
        "dept_fields": DEPT_FIELDS,
        "cases": cases,
        **packed,
    }


def run_one_case(
    db: Session,
    case_id: str,
    sample_sql: str,
    check_sql: str,
    plugin_bench: str,
    native_bench: str,
) -> dict[str, Any]:
    version = _require_orafce(db)
    emp_rows = _table_count(db, "emp")
    bench_rows = _table_count(db, "emp_bench")
    if emp_rows <= 0 or bench_rows <= 0:
        raise RuntimeError("还没有样例数据，先造数再跑")
    meta = _case_meta(case_id)
    spec = {
        **meta,
        "sample_sql": _assert_readonly_select(sample_sql, "sample_sql"),
        "check_sql": _assert_readonly_select(check_sql, "check_sql"),
        "plugin_bench": _assert_readonly_select(plugin_bench, "plugin_bench"),
        "native_bench": _assert_readonly_select(native_bench, "native_bench"),
    }
    started = time.perf_counter()
    case = _run_case(db, spec)
    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    db.commit()
    return {
        "installed": True,
        "version": version,
        "emp_rows": emp_rows,
        "bench_rows": bench_rows,
        "case": case,
        "wall_ms": wall_ms,
    }


SQL_KINDS = ("sample_sql", "check_sql", "plugin_bench", "native_bench")
EXPLAIN_MAX_LINES = 40


def _explain_text(db: Session, sql: str) -> str:
    with db.begin_nested():
        rows = db.execute(text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}")).all()
    lines = [str(row[0]) for row in rows]
    total = len(lines)
    if total > EXPLAIN_MAX_LINES:
        lines = lines[:EXPLAIN_MAX_LINES] + [f"...（另有 {total - EXPLAIN_MAX_LINES} 行省略）"]
    return "\n".join(lines)


def _analysis_for_kind(
    kind: str,
    *,
    fn: str,
    emp_rows: int,
    bench_rows: int,
    ms: float | None,
    row_count: int | None,
    scalar: Any,
    passed: bool | None,
    error: str | None,
) -> list[str]:
    if error:
        return [f"执行失败：{error}", "请确认是只读 SELECT/WITH，且函数名写成 oracle.xxx。"]
    lines: list[str] = []
    if kind == "sample_sql":
        lines.append(f"职责：展示 {fn} 的 orafce 与同义 PG 写法样例对照，通常扫 emp（约 {emp_rows} 行）。")
        lines.append(f"本次返回 {row_count or 0} 行；对照 plugin / native（或同类）列是否一致。")
        lines.append(f"耗时 {ms} ms（单次查询，不是压测口径）。")
    elif kind == "check_sql":
        lines.append(f"职责：正确性断言。标量为真表示 {fn}「可用」，假表示结果与预期不一致。")
        lines.append(f"本次标量={_cell(scalar)!r}，判定={'通过' if passed else '未通过'}。")
        lines.append(f"耗时 {ms} ms。")
    elif kind == "plugin_bench":
        lines.append(f"职责：在 emp_bench（约 {bench_rows} 行）上量 orafce/{fn} 表达式耗时。")
        lines.append(
            f"计时口径：预热 1 次 + 再跑 {TIMING_REPEATS} 次取中位数 = {ms} ms。"
            "结果常含 count + hashtext，避免表达式被优化掉。"
        )
        lines.append("单独看不能当全面压测；与 native_bench 比倍数更有参考价值。")
    elif kind == "native_bench":
        lines.append(f"职责：在 emp_bench（约 {bench_rows} 行）上量同义 PostgreSQL 写法耗时，作为 {fn} 的对照。")
        lines.append(
            f"计时口径：预热 1 次 + 再跑 {TIMING_REPEATS} 次取中位数 = {ms} ms。"
            "结果常含 count + hashtext，避免表达式被优化掉。"
        )
        lines.append("与 plugin_bench 对比倍数；两边都很快时倍数会抖动，仅作相对参考。")
    return lines


def run_one_sql(db: Session, case_id: str, kind: str, sql: str) -> dict[str, Any]:
    version = _require_orafce(db)
    emp_rows = _table_count(db, "emp")
    bench_rows = _table_count(db, "emp_bench")
    if emp_rows <= 0 or bench_rows <= 0:
        raise RuntimeError("还没有样例数据，先造数再跑")
    if kind not in SQL_KINDS:
        raise RuntimeError("kind 只能是 sample_sql / check_sql / plugin_bench / native_bench")
    meta = _case_meta(case_id)
    cleaned = _assert_readonly_select(sql, kind)
    payload: dict[str, Any] = {
        "kind": kind,
        "case_id": case_id,
        "fn": meta["fn"],
        "what": meta["what"],
        "sql": cleaned,
        "rows": None,
        "scalar": None,
        "passed": None,
        "ms": None,
        "explain": None,
        "analysis": [],
        "error": None,
    }
    try:
        if kind == "sample_sql":
            started = time.perf_counter()
            rows = _sample(db, cleaned)
            ms = round((time.perf_counter() - started) * 1000, 2)
            payload["rows"] = rows
            payload["ms"] = ms
            payload["analysis"] = _analysis_for_kind(
                kind,
                fn=meta["fn"],
                emp_rows=emp_rows,
                bench_rows=bench_rows,
                ms=ms,
                row_count=len(rows),
                scalar=None,
                passed=None,
                error=None,
            )
        elif kind == "check_sql":
            started = time.perf_counter()
            with db.begin_nested():
                value = db.execute(text(cleaned)).scalar()
            ms = round((time.perf_counter() - started) * 1000, 2)
            passed = bool(value)
            payload["scalar"] = _cell(value)
            payload["passed"] = passed
            payload["ms"] = ms
            payload["analysis"] = _analysis_for_kind(
                kind,
                fn=meta["fn"],
                emp_rows=emp_rows,
                bench_rows=bench_rows,
                ms=ms,
                row_count=None,
                scalar=value,
                passed=passed,
                error=None,
            )
        else:
            rows = _sample(db, cleaned)
            ms = _time_sql(db, cleaned)
            explain = _explain_text(db, cleaned)
            payload["rows"] = rows
            payload["ms"] = ms
            payload["explain"] = explain
            payload["analysis"] = _analysis_for_kind(
                kind,
                fn=meta["fn"],
                emp_rows=emp_rows,
                bench_rows=bench_rows,
                ms=ms,
                row_count=len(rows),
                scalar=None,
                passed=None,
                error=None,
            )
    except Exception as exc:
        payload["error"] = _short_error(exc)
        payload["analysis"] = _analysis_for_kind(
            kind,
            fn=meta["fn"],
            emp_rows=emp_rows,
            bench_rows=bench_rows,
            ms=None,
            row_count=None,
            scalar=None,
            passed=None,
            error=payload["error"],
        )
    db.commit()
    return {
        "installed": True,
        "version": version,
        "emp_rows": emp_rows,
        "bench_rows": bench_rows,
        **payload,
    }
