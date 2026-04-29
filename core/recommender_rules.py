# core/recommender_rules.py
"""
规则推荐引擎 - Rule-based Chart Recommender
基于数据结构的确定性规则推荐图表
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .data_profiler import DataProfiler


@dataclass
class Recommendation:
    chart_id: str
    score: float          # 0-10
    reasons: List[str] = field(default_factory=list)
    suggested_mapping: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class RuleRecommender:
    """
    规则推荐引擎

    推荐逻辑：
    1. 先推断数据结构（几列、什么类型、是否层次、是否流向）
    2. 套规则模板匹配图表
    3. 排序输出

    使用：
        recommender = RuleRecommender(df)
        recs = recommender.recommend(limit=5)
    """

    # 角色组合 → 图表ID列表（按优先级排序）
    ROLE_RULES: List[Dict[str, Any]] = [
        # ── 流向/关系 ──────────────────────────────────────
        {
            "condition": lambda p: len(p["source"]) and len(p["target"]) and len(p["numeric_cols"]) and not p["has_hierarchy"],
            "charts": ["arc_chart", "sankey", "chord_diagram", "network_diagram"],
            "reason": "数据包含起点终点和数值，适合流向关系图"
        },
        {
            "condition": lambda p: len(p["geo_cols"]) >= 2 and len(p["numeric_cols"]) >= 1,
            "charts": ["choropleth_map", "bubble_map", "proportional_symbol", "dot_density_map"],
            "reason": "数据含地理字段+数值，适合地理图表"
        },
        {
            "condition": lambda p: len(p["geo_cols"]) >= 2 and len(p["source"]) and len(p["target"]),
            "charts": ["flow_map"],
            "reason": "数据含地理流向字段，适合流向地图"
        },
        {
            "condition": lambda p: p["has_flow"] and len(p["source"]) and len(p["target"]) and len(p["geo_cols"]) >= 2,
            "charts": ["flow_map", "sankey", "arc_chart"],
            "reason": "地理流向数据"
        },
        # ── 时间序列 ───────────────────────────────────────
        {
            "condition": lambda p: (len(p["time_cols"]) or len(p["datetime_cols"])) and len(p["numeric_cols"]) >= 1 and not p["has_hierarchy"],
            "charts": ["line_chart", "area_chart", "horizon_chart", "sparkline"],
            "reason": "含时间字段+数值列，适合趋势图"
        },
        # ── 层级结构 ───────────────────────────────────────
        {
            "condition": lambda p: p["has_hierarchy"] and len(p["numeric_cols"]) >= 1,
            "charts": ["treemap", "sunburst", "pie", "waffle"],
            "reason": "数据含层级结构，适合占比类图表"
        },
        # ── 分布 ──────────────────────────────────────────
        {
            "condition": lambda p: len(p["numeric_cols"]) == 1 and len(p["string_cols"]) == 0,
            "charts": ["histogram_chart", "boxplot_chart", "violin_chart"],
            "reason": "单数值列，适合分布图"
        },
        {
            "condition": lambda p: len(p["numeric_cols"]) >= 2 and len(p["string_cols"]) == 0,
            "charts": ["scatter_plot", "heatmap", "parcoords"],
            "reason": "多数值列无分类，适合关系/散点图"
        },
        # ── 金融 ──────────────────────────────────────────
        {
            "condition": lambda p: all(k in [c.lower() for c in p["columns"]] for k in ["open","close","high","low"]),
            "charts": ["candlestick"],
            "reason": "OHLC金融数据，适合K线图"
        },
        # ── 文本 ──────────────────────────────────────────
        {
            "condition": lambda p: len(p["string_cols"]) >= 1 and len(p["numeric_cols"]) >= 1 and any("word" in c.lower() or "text" in c.lower() for c in p["columns"]),
            "charts": ["wordcloud", "word_tree"],
            "reason": "文本+频次数据，适合词云"
        },
        # ── 排名 ──────────────────────────────────────────
        {
            "condition": lambda p: "rank" in [c.lower() for c in p["columns"]] and len(p["string_cols"]) >= 1,
            "charts": ["bump_chart", "slope_chart", "bar_chart"],
            "reason": "含排名字段，适合排名变化图"
        },
        # ── 占比 ──────────────────────────────────────────
        {
            "condition": lambda p: len(p["string_cols"]) >= 1 and len(p["numeric_cols"]) >= 1 and not p.get("has_time"),
            "charts": ["pie", "waffle", "nightingale", "treemap"],
            "reason": "分类+数值，适合占比类图表"
        },
        # ── 比较 ───────────────────────────────────────────
        {
            "condition": lambda p: len(p["string_cols"]) >= 1 and len(p["numeric_cols"]) >= 1,
            "charts": ["bar_chart", "stacked_bar", "grouped_bar", "bullet_chart", "waffle"],
            "reason": "分类+数值，适合比较类图表"
        },
    ]

    def __init__(self, df_or_profiler=None):
        self._profiler: Optional[DataProfiler] = None
        if df_or_profiler is not None:
            self.load(df_or_profiler)

    def load(self, df_or_profiler) -> "RuleRecommender":
        if isinstance(df_or_profiler, DataProfiler):
            self._profiler = df_or_profiler
        else:
            import pandas as pd
            self._profiler = DataProfiler(df=df_or_profiler if not isinstance(df_or_profiler, str) else None)
            if isinstance(df_or_profiler, str):
                self._profiler.load_file(df_or_profiler)
        return self

    def recommend(self, limit: int = 5) -> List[Recommendation]:
        """
        返回推荐列表
        """
        if self._profiler is None:
            raise RuntimeError("No data loaded. Call load() first.")

        p = self._profiler.profile()
        recommendations: List[Recommendation] = []
        used_charts: set = set()

        for rule in self.ROLE_RULES:
            try:
                if rule["condition"](p):
                    for chart_id in rule["charts"]:
                        if chart_id in used_charts:
                            continue
                        used_charts.add(chart_id)
                        rec = Recommendation(
                            chart_id=chart_id,
                            score=7.0 + (rule["charts"].index(chart_id) == 0) * 2,
                            reasons=[rule["reason"]],
                            suggested_mapping=self._suggest_mapping(chart_id, p),
                        )
                        recommendations.append(rec)
            except Exception:
                continue

        # 兜底：如果没有任何推荐
        if not recommendations:
            recommendations.append(Recommendation(
                chart_id="bar_chart",
                score=5.0,
                reasons=["默认推荐：柱状图适用性最广"],
                suggested_mapping=self._suggest_mapping("bar_chart", p),
            ))

        recommendations.sort(key=lambda r: -r.score)
        return recommendations[:limit]

    def _suggest_mapping(self, chart_id: str, p: Dict) -> Dict[str, str]:
        """为指定图表建议字段映射"""
        mapping: Dict[str, str] = {}
        s = self._profiler.suggest_mapping()

        chart_role_map = {
            "bar_chart": [("x", "x"), ("y", "y"), ("series", "series")],
            "line_chart": [("x", "x"), ("y", "y"), ("series", "series")],
            "pie": [("label", "label"), ("value", "value")],
            "scatter_plot": [("x", "x"), ("y", "y"), ("size", "size")],
            "arc_chart": [("source", "source"), ("target", "target"), ("value", "value")],
            "sankey": [("source", "source"), ("target", "target"), ("value", "value")],
            "choropleth_map": [("geo", "geo"), ("value", "value")],
            "bubble_map": [("lat", "lat"), ("lon", "lon"), ("size", "size")],
            "heatmap": [("x", "x"), ("y", "y"), ("value", "value")],
            "histogram_chart": [("value", "value")],
            "boxplot_chart": [("x", "x"), ("value", "value")],
            "treemap": [("label", "label"), ("value", "value"), ("parent", "parent")],
            "sunburst": [("path", "path"), ("value", "value")],
            "wordcloud": [("text", "text"), ("frequency", "frequency")],
            "candlestick": [("date", "date"), ("open_", "open_"), ("high", "high"), ("low", "low"), ("close_", "close_"), ("volume", "volume")],
        }

        role_list = chart_role_map.get(chart_id, [])
        for role, key in role_list:
            if role in s and s[role]:
                # 选第一个匹配的
                mapping[key] = s[role][0]

        return mapping

    def explain(self) -> Dict[str, Any]:
        """返回当前数据的分析摘要"""
        if self._profiler is None:
            raise RuntimeError("No data loaded.")
        p = self._profiler.profile()
        return {
            "n_rows": p["n_rows"],
            "n_cols": p["n_cols"],
            "numeric_cols": p["numeric_cols"],
            "string_cols": p["string_cols"],
            "datetime_cols": p["datetime_cols"],
            "geo_cols": p["geo_cols"],
            "has_hierarchy": p["has_hierarchy"],
            "has_flow": p["has_flow"],
            "suggested_mapping": self._profiler.suggest_mapping(),
        }
