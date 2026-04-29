#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chart Generate - 调用 charts 目录中的实际图表生成模块"""
import sys
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Any
import logging
import importlib

logger = logging.getLogger(__name__)

CHART_PROJECT = Path(__file__).parent
sys.path.insert(0, str(CHART_PROJECT))

try:
    from charts.base import ChartResult, FieldMapping
except ImportError as e:
    logger.error(f"Failed to import charts.base: {e}")
    # 定义备用类
    class ChartResult:
        def __init__(self, html="", spec=None, warnings=None, meta=None):
            self.html = html
            self.spec = spec or {}
            self.warnings = warnings or []
            self.meta = meta or {}
        def is_valid(self):
            return bool(self.html.strip()) and len(self.html) > 500
    
    class FieldMapping:
        pass


def generate_chart(
    df: pd.DataFrame = None,
    excel_path: str = None,
    chart_type: str = "bar_chart",
    mapping: Dict[str, str] = None,
    options: Dict[str, Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """生成图表 - 调用 charts 目录中的实际模块"""
    try:
        if df is None and excel_path:
            df = pd.read_excel(excel_path)
        
        if df is None or df.empty:
            return {"error": "No data"}
        
        logger.info(f"Generating {chart_type} with {len(df)} rows, {len(df.columns)} columns")

        # ✅ 统一列名类型：避免 heatmap 等图表里对列名做 .lower() 时遇到 int
        df = df.copy()
        df.columns = df.columns.map(str)
        
        # 动态导入图表模块
        try:
            module = importlib.import_module(f"charts.{chart_type}")
            generate_func = getattr(module, "generate", None)
            
            if not generate_func:
                logger.error(f"Module charts.{chart_type} has no generate function")
                return {"error": f"Chart type {chart_type} not found"}
        except ImportError as e:
            logger.error(f"Failed to import charts.{chart_type}: {e}")
            return {"error": f"Chart type {chart_type} not found"}
        
        # 自动检测字段映射
        if not mapping:
            mapping = _auto_detect_mapping(df, chart_type)

        # 统一 mapping 中的列名为字符串（mapping 的 value 通常是列名）
        if mapping:
            mapping = {k: (str(v) if v is not None else v) for k, v in mapping.items()}
        
        # 调用图表生成函数
        result = generate_func(df=df, mapping=mapping, options=options or {})
        
        # 检查返回类型
        if isinstance(result, ChartResult):
            if result.is_valid():
                return {
                    "success": True,
                    "html": result.html,
                    "chart_type": chart_type,
                    "warnings": result.warnings,
                    "meta": result.meta
                }
            else:
                return {"error": "Generated chart is invalid"}
        elif isinstance(result, dict):
            if result.get("html"):
                return {
                    "success": True,
                    "html": result.get("html"),
                    "chart_type": chart_type
                }
            else:
                return {"error": result.get("error", "Unknown error")}
        else:
            return {"error": f"Unexpected result type: {type(result)}"}
    
    except Exception as e:
        logger.error(f"Chart generation error: {e}", exc_info=True)
        return {"error": str(e)}


def _auto_detect_mapping(df: pd.DataFrame, chart_type: str) -> Dict[str, str]:
    """自动检测字段映射"""
    try:
        df = df.copy()
        df.columns = df.columns.map(str)
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        string_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        mapping = {}
        
        # 根据图表类型推荐映射
        if chart_type in ["bar_chart", "grouped_bar", "stacked_bar"]:
            if string_cols and numeric_cols:
                mapping["x"] = string_cols[0]
                mapping["y"] = numeric_cols[0]
                if len(string_cols) > 1:
                    mapping["series"] = string_cols[1]
                elif len(numeric_cols) > 1:
                    mapping["series"] = numeric_cols[1]
        
        elif chart_type == "line_chart":
            if string_cols and numeric_cols:
                mapping["x"] = string_cols[0]
                mapping["y"] = numeric_cols[0]
            elif len(numeric_cols) >= 2:
                mapping["x"] = numeric_cols[0]
                mapping["y"] = numeric_cols[1]
        
        elif chart_type == "scatter_plot":
            if len(numeric_cols) >= 2:
                mapping["x"] = numeric_cols[0]
                mapping["y"] = numeric_cols[1]
                if len(numeric_cols) >= 3:
                    mapping["size"] = numeric_cols[2]
        
        elif chart_type == "pie":
            if string_cols and numeric_cols:
                mapping["label"] = string_cols[0]
                mapping["value"] = numeric_cols[0]
        
        elif chart_type == "heatmap":
            if len(numeric_cols) >= 2:
                mapping["x"] = numeric_cols[0]
                mapping["y"] = numeric_cols[1]
                if len(numeric_cols) >= 3:
                    mapping["value"] = numeric_cols[2]
        
        elif chart_type == "histogram_chart":
            if numeric_cols:
                mapping["value"] = numeric_cols[0]
        
        elif chart_type == "boxplot_chart":
            if string_cols and numeric_cols:
                mapping["x"] = string_cols[0]
                mapping["y"] = numeric_cols[0]
            elif numeric_cols:
                mapping["y"] = numeric_cols[0]
        
        elif chart_type == "violin_chart":
            if string_cols and numeric_cols:
                mapping["x"] = string_cols[0]
                mapping["y"] = numeric_cols[0]
            elif numeric_cols:
                mapping["y"] = numeric_cols[0]
        
        elif chart_type == "waterfall":
            if string_cols and numeric_cols:
                mapping["x"] = string_cols[0]
                mapping["y"] = numeric_cols[0]
        
        elif chart_type == "sunburst":
            if len(string_cols) >= 2 and numeric_cols:
                mapping["labels"] = string_cols[0]
                mapping["parents"] = string_cols[1]
                mapping["values"] = numeric_cols[0]
        
        elif chart_type == "treemap":
            if len(string_cols) >= 1 and numeric_cols:
                mapping["labels"] = string_cols[0]
                mapping["values"] = numeric_cols[0]
                if len(string_cols) >= 2:
                    mapping["parents"] = string_cols[1]
        
        logger.debug(f"Auto-detected mapping for {chart_type}: {mapping}")
        return mapping
    
    except Exception as e:
        logger.warning(f"Failed to auto-detect mapping: {e}")
        return {}


def recommend_charts(df: pd.DataFrame = None, excel_path: str = None, limit: int = 5) -> List[Dict]:
    """推荐图表"""
    try:
        if df is None and excel_path:
            df = pd.read_excel(excel_path)
        
        if df is None:
            return []
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        string_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        recommendations = []
        
        # 基于数据特征推荐
        if string_cols and numeric_cols:
            recommendations.append({"chart_id": "bar_chart", "score": 0.95})
            recommendations.append({"chart_id": "grouped_bar", "score": 0.90})
            recommendations.append({"chart_id": "line_chart", "score": 0.85})
        
        if len(numeric_cols) >= 2:
            recommendations.append({"chart_id": "scatter_plot", "score": 0.80})
            recommendations.append({"chart_id": "heatmap", "score": 0.75})
        
        if string_cols and numeric_cols:
            recommendations.append({"chart_id": "pie", "score": 0.70})
        
        return recommendations[:limit]
    
    except Exception as e:
        logger.error(f"Recommend error: {e}")
        return []
