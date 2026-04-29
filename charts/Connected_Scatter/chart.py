"""
连线散点图 Connected Scatter - 演变过程图表
图表分类: 演变 Evolution
感知排名: ★★★★☆

统一接口:
    generate(df, mapping, options) -> ChartResult

使用示例:
    from charts.connected_scatter import generate
    from charts import ChartResult

    result = generate(
        df=df,
        mapping={"x": "销售额", "y": "利润", "order": "年份"},
        options={"title": "销售与利润演变"}
    )
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from charts.base import ChartResult

__all__ = ["generate"]

_DATA_FMT = "x列(数值) + y列(数值) + 可选order列(排序) + 可选size列(标记大小)"
_DESC = "在散点基础上用线段连接各点，展示数据的演变过程或轨迹。适合展示有序路径、时间序列或因果关系。"

MCKINSEY_COLORS = [
    "#003D7A", "#0084D1", "#00A4EF", "#7FBA00", "#FFB81C",
    "#F7630C", "#DA3B01", "#A4373A", "#6B2C91", "#00B4EF",
]


def _norm(s: str) -> str:
    return str(s).strip().lower().replace("_", "").replace(" ", "")


def _auto_col(df: pd.DataFrame, role: str, exclude: set = None) -> Optional[str]:
    """根据角色自动查找匹配的列名（支持大小写/中英文/包含匹配）。"""
    exclude = exclude or set()
    cols = [c for c in df.columns if c not in exclude]
    nums = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    objs = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c])]

    hints_map = {
        "x": ["x", "value", "amount", "sales", "数值", "销售额", "金额"],
        "y": ["y", "profit", "利润", "value", "amount", "数值"],
        "order": ["order", "time", "date", "year", "month", "sequence", "排序", "时间", "日期", "年份"],
        "size": ["size", "value", "amount", "大小", "数值", "权重", "volume"],
    }
    hints = [_norm(h) for h in hints_map.get(role, [])]

    # 1) 完全匹配
    norm_to_col = {_norm(c): c for c in cols}
    for h in hints:
        if h in norm_to_col:
            return norm_to_col[h]

    # 2) 包含匹配
    for c in cols:
        nc = _norm(c)
        if any(h in nc or nc in h for h in hints):
            return c

    # 3) 回退策略
    if role in ("x", "y", "size"):
        if nums:
            if role == "y" and len(nums) > 1:
                return nums[1]
            return nums[0]
        if objs:
            return objs[0]
    elif role == "order":
        # order 优先时间/字符串/数值都可
        if objs:
            return objs[0]
        if nums:
            return nums[0]
    return None


def _build_html(title: str, chart_name: str, library: str,
                data_fmt: str, desc: str, embed: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>{title}</title>
<style>
body{{font-family:"Heiti SC","Microsoft YaHei",sans-serif;margin:40px;background:#fafafa}}
.chart-wrap{{background:white;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);padding:24px;margin-bottom:32px}}
h1{{color:#222;font-size:22px;margin-bottom:6px}}
.subtitle{{color:#888;font-size:13px;margin-bottom:24px}}
.desc{{color:#555;font-size:14px;line-height:1.7;margin-top:20px}}
</style></head>
<body><div class="chart-wrap">
<h1>{title}</h1><div class="subtitle">{chart_name} | {library}</div>
{embed}
</div><div class="desc">
<strong>数据格式：</strong>{data_fmt}<br>
<strong>说明：</strong>{desc}
</div></body></html>"""


def generate(
    df: pd.DataFrame = None,
    mapping: Dict[str, str] = None,
    options: Dict[str, Any] = None,
    excel_path: str = None,
    x: str = "x",
    y: str = "y",
    order: str = None,
    size: str = None,
    title: str = "连线散点图",
    **kwargs
) -> ChartResult:
    warnings: list = []
    options = options or {}
    mapping = mapping or {}

    if df is None:
        if excel_path:
            try:
                df = pd.read_excel(excel_path)
            except Exception as e:
                return ChartResult(warnings=[f"读取Excel失败: {e}"])
        else:
            return ChartResult(warnings=["请提供 df 或 excel_path"])

    # 清理列名空白，避免 "年份 " 这类问题
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    x_col = mapping.get("x") or x
    y_col = mapping.get("y") or y
    order_col = mapping.get("order") or order
    size_col = mapping.get("size") or size
    title = options.get("title", title)

    exclude_set = set()
    _x = x_col if x_col and x_col != "x" and x_col in df.columns else _auto_col(df, "x", exclude_set)
    if _x:
        exclude_set.add(_x)

    _y = y_col if y_col and y_col != "y" and y_col in df.columns else _auto_col(df, "y", exclude_set)
    if _y:
        exclude_set.add(_y)

    _order = order_col if order_col and order_col in df.columns else _auto_col(df, "order", exclude_set)
    if _order:
        exclude_set.add(_order)

    _size = size_col if size_col and size_col in df.columns else _auto_col(df, "size", exclude_set)

    if _x is None or _x not in df.columns:
        return ChartResult(warnings=["找不到x列（数值）"])
    if _y is None or _y not in df.columns:
        return ChartResult(warnings=["找不到y列（数值）"])

    try:
        cols_to_use = [_x, _y]
        if _order and _order in df.columns:
            cols_to_use.append(_order)
        if _size and _size in df.columns:
            cols_to_use.append(_size)

        df_plot = df[cols_to_use].copy()
        df_plot[_x] = pd.to_numeric(df_plot[_x], errors='coerce')
        df_plot[_y] = pd.to_numeric(df_plot[_y], errors='coerce')
        if _size and _size in df_plot.columns:
            df_plot[_size] = pd.to_numeric(df_plot[_size], errors='coerce')

        # order 不强制转 numeric，允许年份字符串
        df_plot = df_plot.dropna(subset=[_x, _y])

        if df_plot.empty:
            return ChartResult(warnings=["无有效数据"])

        if _order and _order in df_plot.columns:
            # 尝试按数值排序，失败则按原值排序
            order_num = pd.to_numeric(df_plot[_order], errors='coerce')
            if order_num.notna().sum() == len(df_plot):
                df_plot = df_plot.assign(__order_num=order_num).sort_values("__order_num").drop(columns="__order_num")
            else:
                df_plot = df_plot.sort_values(_order)
            df_plot = df_plot.reset_index(drop=True)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_plot[_x],
            y=df_plot[_y],
            mode='lines',
            line=dict(color=MCKINSEY_COLORS[0], width=4),
            hoverinfo='skip',
            showlegend=False
        ))

        if _size and _size in df_plot.columns and df_plot[_size].notna().any():
            min_val, max_val = df_plot[_size].min(), df_plot[_size].max()
            if pd.notna(min_val) and pd.notna(max_val) and max_val > min_val:
                marker_sizes = (12 + 18 * (df_plot[_size] - min_val) / (max_val - min_val)).tolist()
            else:
                marker_sizes = [16] * len(df_plot)
        else:
            marker_sizes = [16] * len(df_plot)

        customdata = df_plot[[_order]].values if _order and _order in df_plot.columns else None
        hovertemplate = f"<b>数据点</b><br>{_x}: %{{x:.2f}}<br>{_y}: %{{y:.2f}}"
        if customdata is not None:
            hovertemplate += f"<br>{_order}: %{{customdata[0]}}"
        hovertemplate += "<extra></extra>"

        fig.add_trace(go.Scatter(
            x=df_plot[_x],
            y=df_plot[_y],
            mode='markers',
            marker=dict(
                size=marker_sizes,
                color=MCKINSEY_COLORS[0],
                line=dict(color='white', width=2.5),
                opacity=0.9
            ),
            customdata=customdata,
            hovertemplate=hovertemplate,
            showlegend=False
        ))

        fig.update_layout(
            title=title,
            xaxis_title=_x,
            yaxis_title=_y,
            font_family="Heiti SC, Microsoft YaHei, sans-serif",
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=50, r=50, t=70, b=50),
            hovermode="closest",
            title_font_size=16,
            showlegend=False
        )

        chart_html = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
        if not chart_html or len(chart_html) < 100:
            return ChartResult(warnings=["图表生成失败"])

    except Exception as e:
        return ChartResult(warnings=[f"图表生成失败: {e}"])

    html = _build_html(title, "connected_scatter", "plotly", _DATA_FMT, _DESC, chart_html)


    meta = {
        "chart_id": "connected_scatter",
        "n_rows": len(df),
        "x_col": _x,
        "y_col": _y,
        "order_col": _order,
        "size_col": _size,
    }

    return ChartResult(html=html, spec={}, warnings=warnings, meta=meta)