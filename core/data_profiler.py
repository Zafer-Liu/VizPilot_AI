# core/data_profiler.py
"""
DataProfiler - Excel/CSV 数据结构感知层
独立模块，不和图表耦合
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any, Union

import pandas as pd


class DataProfiler:
    """
    统一数据感知接口
    输出标准 profile，供推荐引擎和验证器使用
    """

    def __init__(self, file_path: Optional[str] = None, df: Optional[pd.DataFrame] = None):
        self._df: Optional[pd.DataFrame] = None
        self._profile: Optional[Dict[str, Any]] = None
        self._file_path = file_path
        if df is not None:
            self.load(df)
        elif file_path is not None and isinstance(file_path, str):
            self.load_file(file_path)

    def load_file(self, path: str, sheet: Union[str, int] = 0) -> "DataProfiler":
        """从文件加载"""
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix == ".csv":
            for enc in ["utf-8-sig", "gbk", "gb2312", "latin1"]:
                try:
                    self._df = pd.read_csv(str(p), encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
        elif suffix in (".xlsx", ".xls"):
            xl = pd.ExcelFile(str(p))
            if isinstance(sheet, int):
                sheet = xl.sheet_names[sheet]
            self._df = xl.parse(sheet)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
        self._file_path = path
        self._profile = None
        return self

    def load(self, df: pd.DataFrame) -> "DataProfiler":
        """直接传入 DataFrame"""
        self._df = df.copy()
        self._profile = None
        return self

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            raise RuntimeError("No data loaded. Call load() or load_file() first.")
        return self._df

    @property
    def columns(self) -> List[str]:
        return list(self.df.columns)

    @property
    def shape(self) -> tuple:
        return self.df.shape

    # ── 类型推断 ──────────────────────────────────────────

    def infer_column_type(
        self, col: str
    ) -> Literal["number", "string", "datetime", "bool", "empty", "mixed", "id"]:
        """
        推断单列类型
        """
        series = self.df[col].dropna()
        if len(series) == 0:
            return "empty"

        dtype = self.df[col].dtype

        # bool
        if pd.api.types.is_bool_dtype(dtype):
            return "bool"
        # datetime
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "datetime"
        # 显式datetime列名
        col_lower = col.lower()
        if any(k in col_lower for k in ["date", "time", "日期", "时间", "datetime"]):
            if pd.api.types.is_numeric_dtype(dtype):
                return "datetime"  # 可能是时间戳
        # numeric
        if pd.api.types.is_numeric_dtype(dtype):
            return "number"
        # string / object
        if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
            # 纯数字字符串
            try:
                coerced = pd.to_numeric(series, errors="coerce")
                if coerced.notna().sum() / len(series) > 0.8:
                    return "number"
            except Exception:
                pass
            # ID类（高唯一性，低文本熵）
            n_unique = series.nunique()
            if n_unique > len(series) * 0.9 and n_unique > 20:
                return "id"
            return "string"
        return "mixed"

    def column_types(self) -> Dict[str, Literal["number", "string", "datetime", "bool", "empty", "mixed", "id"]]:
        """返回所有列的类型"""
        return {col: self.infer_column_type(col) for col in self.columns}

    # ── 统计信息 ──────────────────────────────────────────

    def column_stats(self, col: str) -> Dict[str, Any]:
        """
        返回单列统计信息
        """
        series = self.df[col]
        non_null = series.dropna()
        col_type = self.infer_column_type(col)
        stats: Dict[str, Any] = {
            "dtype": str(series.dtype),
            "type": col_type,
            "count": len(series),
            "non_null": len(non_null),
            "null": series.isna().sum(),
            "missing_rate": round(series.isna().sum() / len(series), 4),
            "unique": series.nunique(),
        }
        if col_type == "number":
            stats.update({
                "min": series.min(),
                "max": series.max(),
                "mean": round(float(series.mean()), 4) if len(non_null) else None,
                "median": round(float(series.median()), 4) if len(non_null) else None,
                "sum": round(float(series.sum()), 4) if len(non_null) else None,
            })
        if col_type == "string" and len(non_null) > 0:
            # 最常见值
            vc = non_null.value_counts()
            stats.update({
                "top_values": [{"value": str(v), "count": int(c)} for v, c in vc.head(5).items()],
                "avg_len": round(float(non_null.astype(str).str.len().mean()), 2),
            })
        return stats

    def profile(self) -> Dict[str, Any]:
        """
        返回完整数据概览
        """
        if self._profile is not None:
            return self._profile

        n_rows, n_cols = self.shape
        col_types = self.column_types()

        numeric_cols = [c for c, t in col_types.items() if t == "number"]
        string_cols  = [c for c, t in col_types.items() if t == "string"]
        datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
        bool_cols    = [c for c, t in col_types.items() if t == "bool"]
        id_cols      = [c for c, t in col_types.items() if t == "id"]
        geo_cols     = [c for c in self.columns
                        if any(k in c.lower() for k in ["lat","lon","lng","经度","纬度","province","省","city","城市","country","国家","geo"])]
        time_cols    = [c for c in self.columns
                        if any(k in c.lower() for k in ["date","time","日期","时间","year","年","month","月","day","日"])]

        # 示例值（每列取前3个非空）
        sample_values: Dict[str, List[Any]] = {}
        for col in self.columns:
            vals = self.df[col].dropna().head(3).tolist()
            sample_values[col] = [str(v) for v in vals]

        self._profile = {
            "file": self._file_path or "memory",
            "n_rows": n_rows,
            "n_cols": n_cols,
            "columns": self.columns,
            "column_types": col_types,
            "numeric_cols": numeric_cols,
            "string_cols": string_cols,
            "datetime_cols": datetime_cols,
            "bool_cols": bool_cols,
            "id_cols": id_cols,
            "geo_cols": geo_cols,
            "time_cols": time_cols,
            "can_aggregate": len(numeric_cols) > 0,
            "has_hierarchy": any(k in str(self.columns).lower() for k in ["parent","child","path","层级"]),
            "has_flow": all(k in col_types for k in ["source","target","value"]) if False else bool(set(["source","target"]).intersection(set(self.columns))),
            "sample_values": sample_values,
            "column_stats": {col: self.column_stats(col) for col in self.columns},
        }
        return self._profile

    def suggest_mapping(self) -> Dict[str, List[str]]:
        """
        根据列名推断可能的字段映射
        Returns: {role: [possible_column_names]}
        """
        p = self.profile()
        result: Dict[str, List[str]] = {}
        role_hints = {
            "x": ["x", "日期", "date", "时间", "time", "月份", "month", "年", "year", "季度", "category"],
            "y": ["y", "数值", "value", "销量", "金额", "count", "amount", "金额", "收入", "人口"],
            "label": ["name", "名称", "label", "类别", "category", "产品", "城市", "国家", "country", "省"],
            "value": ["value", "数值", "销量", "金额", "count", "amount", "frequency", "频次"],
            "source": ["source", "起点", "from", "origin", "start"],
            "target": ["target", "终点", "to", "destination", "end"],
            "lat": ["lat", "latitude", "纬度", "y"],
            "lon": ["lon", "lng", "longitude", "经度", "x"],
            "geo": ["province", "省", "city", "城市", "country", "国家", "region", "地区"],
            "series": ["series", "分组", "group", "type", "category", "分类"],
            "size": ["size", "大小", "bubble", "bubble_size"],
            "color": ["color", "颜色", "类别", "category"],
            "date": ["date", "日期", "time", "时间", "datetime"],
            "open_": ["open", "开盘"],
            "high": ["high", "最高"],
            "low": ["low", "最低"],
            "close_": ["close", "收盘"],
            "volume": ["volume", "vol", "成交量", "volume"],
            "text": ["word", "text", "词语", "关键词", "keyword"],
            "frequency": ["frequency", "freq", "频次", "count", "次数"],
            "parent": ["parent", "父", "parent_id"],
            "child": ["child", "子", "child_id"],
            "path": ["path", "路径", "hierarchy", "层级"],
            "rank": ["rank", "排名", "position"],
            "actual": ["actual", "实际", "real"],
            "target_val": ["target", "目标", "goal"],
        }
        for role, hints in role_hints.items():
            matches = []
            for col in self.columns:
                col_lower = col.lower()
                for h in hints:
                    if h.lower() in col_lower:
                        matches.append(col)
                        break
            if matches:
                result[role] = matches
        return result

    def __repr__(self) -> str:
        if self._df is None:
            return "<DataProfiler: no data>"
        n, m = self.shape
        return f"<DataProfiler: {n}行 × {m}列 | 类型: {self.column_types()}>"
