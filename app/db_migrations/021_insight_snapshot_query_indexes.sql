-- 按 user_id 取最新快照 / 用户列表窗口函数（PK 前缀是 snapshot_date，无法覆盖）
CREATE INDEX IF NOT EXISTS ix_insight_snapshot_user_date
    ON insight_user_profile_snapshot (user_id, snapshot_date DESC);

-- 决策看板：当日 high 风险计数 + 推荐列表 ORDER BY risk_score
CREATE INDEX IF NOT EXISTS ix_insight_snapshot_date_risk_score
    ON insight_user_profile_snapshot (snapshot_date, churn_risk_level, risk_score DESC);

-- 批处理日志：按 question 收口 running / 列表排序
CREATE INDEX IF NOT EXISTS ix_insight_analysis_logs_question_created
    ON insight_analysis_logs (question, created_at DESC);
