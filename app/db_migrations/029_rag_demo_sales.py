"""NL2SQL 演示库：区域 / 产品 / 销售明细（只读查询用）。"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        if "rag_demo_regions" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE rag_demo_regions (
                        id SERIAL PRIMARY KEY,
                        code VARCHAR(16) UNIQUE NOT NULL,
                        name VARCHAR(64) NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO rag_demo_regions (code, name) VALUES
                    ('east', '华东'),
                    ('north', '华北'),
                    ('south', '华南')
                    """
                )
            )
        if "rag_demo_products" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE rag_demo_products (
                        id SERIAL PRIMARY KEY,
                        sku VARCHAR(32) UNIQUE NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        category VARCHAR(64) NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO rag_demo_products (sku, name, category) VALUES
                    ('P-A1', '智能音箱 Pro', '硬件'),
                    ('P-B2', '会议平板 X', '硬件'),
                    ('P-C3', '知识库订阅年费', '软件'),
                    ('P-D4', '客服坐席包月', '软件')
                    """
                )
            )
        if "rag_demo_sales" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE rag_demo_sales (
                        id SERIAL PRIMARY KEY,
                        sold_at DATE NOT NULL,
                        region_code VARCHAR(16) NOT NULL,
                        product_sku VARCHAR(32) NOT NULL,
                        amount NUMERIC(12, 2) NOT NULL,
                        qty INT NOT NULL DEFAULT 1
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO rag_demo_sales (sold_at, region_code, product_sku, amount, qty) VALUES
                    ('2026-07-05', 'east', 'P-A1', 12800.00, 4),
                    ('2026-07-12', 'east', 'P-B2', 25600.00, 2),
                    ('2026-07-18', 'east', 'P-C3', 9800.00, 10),
                    ('2026-07-08', 'north', 'P-A1', 6400.00, 2),
                    ('2026-07-22', 'north', 'P-D4', 15000.00, 5),
                    ('2026-07-03', 'south', 'P-B2', 12800.00, 1),
                    ('2026-07-28', 'east', 'P-A1', 19200.00, 6),
                    ('2026-06-15', 'east', 'P-C3', 4900.00, 5),
                    ('2026-08-02', 'east', 'P-D4', 9000.00, 3),
                    ('2026-08-05', 'south', 'P-A1', 9600.00, 3)
                    """
                )
            )
    logger.info("rag_demo_sales 演示表已就绪")
