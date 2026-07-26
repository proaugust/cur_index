"""验证 Insight AI 分析算法（纯函数 + 可选本地 API）。

用法:
  .\\.venv\\Scripts\\python.exe scripts\\verify_insight_algo.py
  .\\.venv\\Scripts\\python.exe scripts\\verify_insight_algo.py --api http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

PASSED = 0
FAILED = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"[PASS] {name}")
    else:
        FAILED += 1
        suffix = f" — {detail}" if detail else ""
        print(f"[FAIL] {name}{suffix}")


def _user(**kwargs):
    base = dict(
        user_id="U1",
        region_l1="东京都",
        region_l2="千代田区",
        age_group="30-39",
        plan_id="199元套餐",
        vip_level="普通",
        age=35,
        monthly_fee=199,
        fee_drift_rate=0.1,
        satisfaction_net=3,
        satisfaction_srv=3,
        join_date=date.today() - timedelta(days=400),
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _feature(**kwargs):
    from app.services.modules.insight.ml.feature_labels import FEATURE_NAMES
    from app.services.modules.insight.ml.types import UserFeatureRow

    values = [0.0] * len(FEATURE_NAMES)
    row = UserFeatureRow(
        user_id="U1",
        has_sample=True,
        complaint_cnt=0,
        avg_satisfaction=3.0,
        dominant_type=None,
        values=values,
    )
    for key, val in kwargs.items():
        if hasattr(row, key):
            setattr(row, key, val)
    if "loyalty" in kwargs and "survey_loyalty_retention" in FEATURE_NAMES:
        row.values[FEATURE_NAMES.index("survey_loyalty_retention")] = float(kwargs["loyalty"])
    return row


def verify_pure() -> None:
    from app.services.modules.insight.ai_risk_engine import (
        _downgrade_unexplained_high,
        _direct_tags,
        _select_shap_ids,
    )
    from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
    from app.services.modules.insight.ml.feature_labels import FEATURE_NAMES
    from app.services.modules.insight.ml.mock_scorer import mock_score, risk_level
    from app.services.modules.insight.ml.weak_label import weak_label
    from app.services.modules.insight.seed.churn_label_generator import (
        default_as_of_dates,
        sample_churn_label,
        synthetic_churn_prob,
    )

    # 1) 特征维数自洽
    user = _user()
    stat = {
        "sample_cnt": 2,
        "complaint_cnt": 1,
        "complaint_cnt_30d": 1,
        "avg_satisfaction": 2.0,
        "dominant_type": "网络质量",
        "ctype_counts": {"网络质量": 1},
        "survey_scores": {"loyalty_retention": 2.0},
    }
    vec = InsightFeatureBuilder._build_vector(None, user, stat, date.today())  # type: ignore[arg-type]
    check("特征维数 FEATURE_NAMES == vector", len(FEATURE_NAMES) == len(vec), f"{len(FEATURE_NAMES)} vs {len(vec)}")

    # 2) 风险分档
    check("risk_level high", risk_level(Decimal("0.55")) == "high")
    check("risk_level medium", risk_level(Decimal("0.35")) == "medium")
    check("risk_level low", risk_level(Decimal("0.34")) == "low")

    # 3) mock 分对投诉/低满意度单调不降
    base_f = _feature(complaint_cnt=0, avg_satisfaction=4.0)
    hi_f = _feature(complaint_cnt=3, avg_satisfaction=1.5)
    s0 = mock_score(user, base_f)
    s1 = mock_score(user, hi_f)
    check("mock_score 高风险信号升高", s1 > s0, f"{s0} -> {s1}")

    # 4) 弱标签规则
    check("weak_label 多次投诉", weak_label(user, _feature(complaint_cnt=2)) == 1)
    check("weak_label 低满意度", weak_label(user, _feature(complaint_cnt=0, avg_satisfaction=2.0)) == 1)
    check("weak_label 资费漂移", weak_label(_user(fee_drift_rate=0.3), _feature()) == 1)
    check("weak_label 正常用户", weak_label(user, _feature(complaint_cnt=0, avg_satisfaction=4.0, loyalty=4.0)) == 0)

    # 5) 合成标签概率与采样
    risky = _feature(complaint_cnt=4, avg_satisfaction=1.0, loyalty=1.0)
    calm = _feature(complaint_cnt=0, avg_satisfaction=5.0, loyalty=5.0)
    p_hi = synthetic_churn_prob(_user(fee_drift_rate=0.4), risky)
    p_lo = synthetic_churn_prob(_user(fee_drift_rate=0.0), calm)
    check("synthetic_churn_prob 风险用户更高", p_hi > p_lo, f"{p_hi:.3f} vs {p_lo:.3f}")
    churn, cancel = sample_churn_label(user, risky, date(2026, 1, 1))
    check("sample_churn_label 返回合法二元", churn in (0, 1))
    check("正样本必有 cancel_date", (churn == 0 and cancel is None) or (churn == 1 and cancel is not None))

    # 6) as_of 锚定样本日且含当天
    as_ofs = default_as_of_dates(today=date(2026, 7, 26))
    check("as_of 含锚定日", as_ofs[0] == date(2026, 7, 26), str(as_ofs))
    check("as_of 递减", as_ofs == sorted(as_ofs, reverse=True), str(as_ofs))

    # 7) 无 SHAP 高风险降级
    rows = [
        {
            "user_id": "A",
            "churn_risk_level": "high",
            "shap_values": {},
            "tags": ["多次投诉"],
        }
    ]
    _downgrade_unexplained_high(rows)
    check("无归因高风险降为 medium", rows[0]["churn_risk_level"] == "medium")
    check("无归因打证据不足", "证据不足" in rows[0]["tags"])

    # 8) SHAP 策略与标签
    scores = {"a": Decimal("0.7"), "b": Decimal("0.2")}
    check(
        "shap high_only 只取高风险",
        _select_shap_ids(["a", "b"], scores, "high_only") == ["a"],
    )
    tags = _direct_tags(_user(fee_drift_rate=0.3, vip_level="金卡"), _feature(complaint_cnt=2, avg_satisfaction=2.0))
    check("direct_tags 含多次投诉/低满意度/资费敏感/高价值", {"多次投诉", "低满意度", "资费敏感", "高价值客户"} <= set(tags))


def verify_api(base: str, username: str, password: str) -> None:
    import json
    import urllib.error
    import urllib.request

    def probe_prefix() -> str:
        for prefix in ("", "/api"):
            try:
                urllib.request.urlopen(base + prefix + "/openapi.json", timeout=10).read(20)
                return prefix
            except Exception:
                continue
        return ""

    prefix = probe_prefix()
    print(f"       api_prefix={prefix or '(none)'}")

    def req(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 180):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(base + prefix + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                raw = resp.read().decode()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode(errors="replace")
            try:
                payload = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                payload = {"detail": raw}
            return exc.code, payload

    code, login = req("POST", "/auth/login", body={"username": username, "password": password})
    token = login.get("access_token") or login.get("token")
    check("API 登录", code == 200 and bool(token), str(login)[:200])
    if not token:
        return

    code, status = req("GET", "/insight/seed/status", token=token)
    check("seed/status", code == 200, str(status)[:200])
    users = int(status.get("users") or 0)
    samples = int(status.get("samples") or 0)
    labels = int(status.get("churn_labels") or 0)
    print(f"       status users={users} samples={samples} churn_labels={labels}")

    if users < 30:
        code, _ = req("POST", "/insight/seed/users?preset=mini", token=token, timeout=300)
        check("seed users mini", code == 200, f"status={code}")
    else:
        check("seed users 已有数据跳过", True)

    if samples < 30 or labels < 30:
        if samples > 0:
            code, _ = req("POST", "/insight/seed/reset-samples", token=token, timeout=180)
            check("reset samples", code == 200, f"status={code}")
        code, seeded = req("POST", "/insight/seed/samples?preset=mini", token=token, timeout=600)
        detail = seeded if isinstance(seeded, dict) else {}
        ok = code == 200 and int(detail.get("churn_labels_inserted") or 0) > 0
        check(
            "seed samples + churn labels",
            ok,
            f"status={code} body={str(seeded)[:240]}",
        )
    else:
        check("seed samples 已有标签跳过", True)

    code, train = req("POST", "/insight/models/train", token=token, timeout=600)
    train_ok = code == 200 and int(train.get("train_rows") or 0) >= 30
    check(
        "models/train",
        train_ok,
        f"status={code} body={str(train)[:240]}",
    )
    if train_ok:
        print(
            f"       train_rows={train.get('train_rows')} label_source={train.get('label_source')} "
            f"version={train.get('model_version')}"
        )

    code, job = req("POST", "/insight/jobs/nightly-run?mode=full&with_prev_day=false", token=token, timeout=60)
    log_id = job.get("analysis_log_id") or job.get("id")
    check("nightly-run 受理", code in (200, 202) and bool(log_id), f"status={code} body={str(job)[:240]}")
    if not log_id:
        return

    final = None
    for _ in range(60):
        code, logs = req("GET", "/insight/jobs/logs?page=1&page_size=5", token=token, timeout=60)
        items = logs.get("list") or logs.get("items") or []
        hit = next((x for x in items if str(x.get("id")) == str(log_id)), items[0] if items else None)
        if hit and hit.get("status") in ("completed", "failed", "error"):
            final = hit
            break
        time.sleep(5)
    check("nightly 完成", bool(final) and final.get("status") == "completed", str(final)[:300] if final else "timeout")

    code, dash = req("GET", "/insight/decision/dashboard", token=token)
    version = str(dash.get("model_version") or "")
    check("dashboard 可读", code == 200, str(dash)[:200])
    check("非纯 mock 模型", bool(dash.get("has_trained_model")) and "mock" not in version.lower(), version)
    print(
        f"       dashboard model={version} high_risk={dash.get('high_risk_total')} "
        f"label_source={dash.get('label_source')} has_model={dash.get('has_trained_model')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="", help="如 http://127.0.0.1:8000，空则只跑纯函数")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123456")
    args = parser.parse_args()

    print("=== Insight AI 算法纯函数验证 ===")
    verify_pure()
    if args.api:
        print(f"\n=== API 端到端验证 ({args.api}) ===")
        verify_api(args.api.rstrip("/"), args.username, args.password)

    print(f"\n合计 PASS={PASSED} FAIL={FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
