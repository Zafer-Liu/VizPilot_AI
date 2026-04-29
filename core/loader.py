"""
ExcelLoader - Excel 文件读取与数据结构感知
支持：xlsx / xls / csv
"""

import warnings
from pathlib import Path
from typing import Literal, Optional

import pandas as pd

__all__ = ["ExcelLoader"]


class ExcelLoader:
    """Excel / CSV 文件加载器，自动感知结构"""

    SUPPORTED_FORMATS = {".xlsx", ".xls", ".csv"}

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        if self.file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不支持的格式: {self.file_path.suffix}，"
                f"支持: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        self._raw: Optional[pd.DataFrame] = None
        self._sheet_names: Optional[list] = None

    # ── 基础属性 ──────────────────────────────────────

    @property
    def sheet_names(self) -> list[str]:
        """返回所有工作表名称"""
        if self._sheet_names is None:
            if self.file_path.suffix.lower() == ".csv":
                self._sheet_names = [self.file_path.stem]
            else:
                xl = pd.ExcelFile(str(self.file_path))
                self._sheet_names = xl.sheet_names
        return self._sheet_names

    @property
    def n_sheets(self) -> int:
        return len(self.sheet_names)

    # ── 加载数据 ──────────────────────────────────────

    def load(
        self,
        sheet: str | int = 0,
        header: Optional[int] = 0,
        index_col: Optional[int | str] = None,
    ) -> pd.DataFrame:
        """
        加载指定 sheet

        Args:
            sheet: 工作表名称或索引（默认第 0 个）
            header: 表头行（默认第 0 行），None 表示无表头
            index_col: 索引列，默认不设
        """
        suffix = self.file_path.suffix.lower()
        kwargs = dict(header=header, index_col=index_col)

        if suffix == ".csv":
            # CSV 自动推断 encoding，避免 utf-8 中文报错
            for enc in ["utf-8-sig", "gbk", "gb2312", "latin1"]:
                try:
                    self._raw = pd.read_csv(str(self.file_path), encoding=enc, **kwargs)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise UnicodeDecodeError(
                    "无法识别 CSV 编码，请确认文件编码"
                )
        else:
            xl = pd.ExcelFile(str(self.file_path))
            if isinstance(sheet, int):
                sheet = xl.sheet_names[sheet]
            self._raw = xl.parse(sheet, **kwargs)

        return self._raw

    def reload(self, **kwargs) -> pd.DataFrame:
        """用新参数重新加载当前文件"""
        return self.load(**kwargs)

    # ── 数据结构感知 ──────────────────────────────────

    @property
    def shape(self) -> tuple[int, int]:
        """(行数, 列数)"""
        if self._raw is None:
            raise RuntimeError("请先调用 load() 加载数据")
        return self._raw.shape

    @property
    def columns(self) -> list[str]:
        """列名列表"""
        if self._raw is None:
            raise RuntimeError("请先调用 load() 加载数据")
        return list(self._raw.columns)

    @property
    def dtypes(self) -> pd.Series:
        """每列数据类型"""
        if self._raw is None:
            raise RuntimeError("请先调用 load() 加载数据")
        return self._raw.dtypes

    def column_types(self) -> dict[str, Literal["number", "text", "datetime", "bool", "empty", "mixed"]]:
        """
        返回每列的类型分类
        """
        if self._raw is None:
            raise RuntimeError("请先调用 load() 加载数据")

        result = {}
        for col in self._raw.columns:
            dtype = self._raw[col].dtype
            non_null = self._raw[col].dropna()

            if len(non_null) == 0:
                result[str(col)] = "empty"
            elif pd.api.types.is_bool_dtype(dtype):
                result[str(col)] = "bool"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                result[str(col)] = "datetime"
            elif pd.api.types.is_numeric_dtype(dtype):
                result[str(col)] = "number"
            elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
                # 进一步判断：纯数字字符串也归为 number
                try:
                    coerced = pd.to_numeric(non_null, errors="coerce")
                    if coerced.notna().sum() / len(non_null) > 0.8:
                        result[str(col)] = "number"
                    else:
                        result[str(col)] = "text"
                except Exception:
                    result[str(col)] = "text"
            else:
                result[str(col)] = "mixed"

        return result

    # ── 快捷概览 ─────────────────────────────────────

    def profile(self) -> dict:
        """
        返回数据概览字典，供 recommend 和 validator 使用
        """
        if self._raw is None:
            raise RuntimeError("请先调用 load() 加载数据")

        n_rows, n_cols = self.shape
        col_types = self.column_types()

        num_cols = [c for c, t in col_types.items() if t == "number"]
        txt_cols = [c for c, t in col_types.items() if t == "text"]
        dt_cols  = [c for c, t in col_types.items() if t == "datetime"]

        return {
            "file": str(self.file_path),
            "sheet": self.sheet_names[0] if self.n_sheets == 1 else self.sheet_names,
            "n_sheets": self.n_sheets,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "column_types": col_types,
            "numeric_cols": num_cols,
            "text_cols": txt_cols,
            "datetime_cols": dt_cols,
            "has_index": self._raw.index.name is not None or self._raw.index.nlevels > 1,
        }

    def __repr__(self) -> str:
        if self._raw is None:
            return f"<ExcelLoader: {self.file_path.name} (not loaded)>"
        n, m = self.shape
        return f"<ExcelLoader: {self.file_path.name} [{n}行 × {m}列]>"
