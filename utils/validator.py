"""
DataValidator - 数据质量检测
检测：空值、异常值、类型冲突、分布异常、数据稀疏等
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

__all__ = ["DataValidator", "ValidationResult", "IssueLevel"]


class IssueLevel(Enum):
    """问题严重等级"""
    OK = "ok"
    WARNING = "warning"   # 可用但影响图表质量
    ERROR = "error"        # 无法生成正确图表


@dataclass
class Issue:
    column: str
    level: IssueLevel
    code: str                       # 如 "MISSING_RATE_HIGH"
    message: str
    detail: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """检测结果容器"""
    df: pd.DataFrame
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """是否有 ERROR 级别问题"""
        return not any(i.level == IssueLevel.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == IssueLevel.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.level == IssueLevel.WARNING)

    def get_issues(self, level: IssueLevel) -> list[Issue]:
        return [i for i in self.issues if i.level == level]

    def summary(self) -> dict:
        """人类可读的摘要"""
        return {
            "total_rows": len(self.df),
            "total_cols": len(self.df.columns),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "ok": self.ok,
            "issue_list": [
                {"col": i.column, "level": i.level.value, "code": i.code, "msg": i.message}
                for i in self.issues
            ],
        }


class DataValidator:
    """
    数据质量检测器
    用法：
        result = DataValidator(df).validate()
        if not result.ok:
            print(result.summary())
    """

    # 各检测项的阈值
    THRESHOLDS = {
        "missing_rate_warn": 0.05,    # 空值率 > 5% → warning
        "missing_rate_error": 0.40,  # 空值率 > 40% → error
        "outlier_rate_warn": 0.01,    # 异常值比例 > 1% → warning
        "outlier_rate_error": 0.20,   # 异常值比例 > 20% → error
        "n_unique_low": 3,            # 唯一值过少（分类列）
        "n_unique_high": 100,          # 唯一值过多（分类列）
        "n_rows_min": 3,               # 行数太少
        "n_rows_max": 500_000,         # 行数太多（性能）
    }

    def __init__(self, df: pd.DataFrame, thresholds: Optional[dict] = None):
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df 必须是 pandas.DataFrame")
        self.df = df.copy()
        self.thresholds = {**self.THRESHOLDS, **(thresholds or {})}
        self._result: Optional[ValidationResult] = None

    def validate(self) -> ValidationResult:
        """执行全部检测"""
        issues: list[Issue] = []

        issues += self._check_row_count()
        issues += self._check_missing_values()
        issues += self._check_outliers()
        issues += self._check_text_columns()
        issues += self._check_datetime_columns()
        issues += self._check_duplicates()

        self._result = ValidationResult(df=self.df, issues=issues)
        return self._result

    # ── 检测规则 ──────────────────────────────────────

    def _check_row_count(self) -> list[Issue]:
        issues = []
        n = len(self.df)
        if n < self.thresholds["n_rows_min"]:
            issues.append(Issue(
                column="__global__",
                level=IssueLevel.ERROR,
                code="TOO_FEW_ROWS",
                message=f"数据行数过少（{n} 行），无法生成有效图表",
                detail={"n_rows": n, "min_required": self.thresholds["n_rows_min"]},
            ))
        elif n > self.thresholds["n_rows_max"]:
            issues.append(Issue(
                column="__global__",
                level=IssueLevel.WARNING,
                code="TOO_MANY_ROWS",
                message=f"数据行数过多（{n} 行），可能会影响渲染性能",
                detail={"n_rows": n, "max_suggested": self.thresholds["n_rows_max"]},
            ))
        return issues

    def _check_missing_values(self) -> list[Issue]:
        issues = []
        total = len(self.df)

        for col in self.df.columns:
            missing = self.df[col].isna().sum()
            missing_rate = missing / total if total > 0 else 0

            if missing_rate >= self.thresholds["missing_rate_error"]:
                level = IssueLevel.ERROR
            elif missing_rate >= self.thresholds["missing_rate_warn"]:
                level = IssueLevel.WARNING
            else:
                continue

            issues.append(Issue(
                column=str(col),
                level=level,
                code="MISSING_RATE_HIGH",
                message=f"列「{col}」空值率 {missing_rate:.1%}（{missing}/{total}）",
                detail={"missing": missing, "total": total, "rate": missing_rate},
            ))
        return issues

    def _check_outliers(self) -> list[Issue]:
        """
        使用 IQR × 1.5 法则检测数值列异常值
        """
        issues = []
        numeric_cols = self.df.select_dtypes(include="number").columns

        for col in numeric_cols:
            if self.df[col].dropna().empty:
                continue

            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            if IQR == 0:
                continue  # 无差异，跳过

            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = ((self.df[col] < lower) | (self.df[col] > upper)).sum()
            total = self.df[col].notna().sum()
            rate = outliers / total if total > 0 else 0

            if rate >= self.thresholds["outlier_rate_error"]:
                level = IssueLevel.ERROR
            elif rate >= self.thresholds["outlier_rate_warn"]:
                level = IssueLevel.WARNING
            else:
                continue

            issues.append(Issue(
                column=str(col),
                level=level,
                code="OUTLIER_HIGH",
                message=f"列「{col}」异常值比例 {rate:.1%}（{outliers}/{total} 个）",
                detail={
                    "outliers": int(outliers),
                    "total": int(total),
                    "rate": float(rate),
                    "boundaries": (float(lower), float(upper)),
                },
            ))
        return issues

    def _check_text_columns(self) -> list[Issue]:
        """
        文本/类别列检测：唯一值数量、稀疏类、长文本
        """
        issues = []
        obj_cols = self.df.select_dtypes(include=["object", "string"]).columns

        for col in obj_cols:
            n_unique = self.df[col].dropna().nunique()
            n_total = len(self.df)
            sample_vals = self.df[col].dropna().head(5).tolist()

            # 唯一值过少
            if n_unique < self.thresholds["n_unique_low"]:
                issues.append(Issue(
                    column=str(col),
                    level=IssueLevel.WARNING,
                    code="CARDINALITY_LOW",
                    message=f"列「{col}」唯一值过少（{n_unique} 个），可能适合做分类映射",
                    detail={"n_unique": n_unique},
                ))

            # 唯一值过多（高基数）
            if n_unique > self.thresholds["n_unique_high"]:
                issues.append(Issue(
                    column=str(col),
                    level=IssueLevel.WARNING,
                    code="CARDINALITY_HIGH",
                    message=f"列「{col}」唯一值过多（{n_unique} 个），图表可能会过于密集",
                    detail={"n_unique": n_unique, "n_rows": n_total},
                ))

            # 长文本检测
            avg_len = self.df[col].dropna().astype(str).str.len().mean()
            if avg_len > 50:
                issues.append(Issue(
                    column=str(col),
                    level=IssueLevel.WARNING,
                    code="TEXT_TOO_LONG",
                    message=f"列「{col}」文本平均长度过长（{avg_len:.0f} 字），建议截断或聚合",
                    detail={"avg_length": float(avg_len)},
                ))
        return issues

    def _check_datetime_columns(self) -> list[Issue]:
        """日期列：检测无效/混乱日期"""
        issues = []
        dt_cols = self.df.select_dtypes(include="datetime").columns

        for col in dt_cols:
            vals = self.df[col].dropna()
            if vals.empty:
                continue
            span = (vals.max() - vals.min()).days
            if span > 365 * 30:  # 跨度超过 30 年 → warning
                issues.append(Issue(
                    column=str(col),
                    level=IssueLevel.WARNING,
                    code="DATETIME_SPAN_LONG",
                    message=f"列「{col}」时间跨度极大（{span} 天 ≈ {span/365:.0f} 年）",
                    detail={"span_days": int(span)},
                ))
        return issues

    def _check_duplicates(self) -> list[Issue]:
        """重复行检测"""
        issues = []
        n_dup = self.df.duplicated().sum()
        n_total = len(self.df)
        if n_dup > 0:
            rate = n_dup / n_total
            level = IssueLevel.WARNING if rate < 0.1 else IssueLevel.ERROR
            issues.append(Issue(
                column="__global__",
                level=level,
                code="DUPLICATE_ROWS",
                message=f"发现 {n_dup} 行重复数据（{rate:.1%}）",
                detail={"duplicates": int(n_dup), "total": int(n_total)},
            ))
        return issues

    # ── 快速入口 ──────────────────────────────────────

    @staticmethod
    def quick(df: pd.DataFrame) -> bool:
        """
        快速检查：是否有 ERROR 级别问题
        返回 True = 通过，False = 有错误
        """
        return DataValidator(df).validate().ok
