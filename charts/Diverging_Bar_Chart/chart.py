"""
对比条形图 Diverging Bar - 比较图表
图表分类: 比较 Comparison
感知排名: ★★★★☆

统一接口:
    generate(df, mapping, options) -> ChartResult
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from charts.base import ChartResult

__all__ = ["generate"]

_DATA_FMT = "单列模式: item列 + value列 | 多列模式: item列 + 负值列(多个) + 正值列(多个)"
_DESC = "以零点为基准左右展开，正值向右（蓝色），负值向左（红色）。支持单列模式和李克特量表多列模式。"


def _auto_col(df: pd.DataFrame, *hints: str) -> Optional[str]:
    """根据提示自动查找匹配的列名。"""
    if not hints or not df.columns.size:
        return None

    col_lower = {c.lower(): c for c in df.columns}

    # 1. 精确匹配
    for h in hints:
        h_lower = h.lower()
        if h_lower in col_lower:
            return col_lower[h_lower]

    # 2. 模糊匹配
    for h in hints:
        h_lower = h.lower()
        for col in df.columns:
            col_lower_name = col.lower()
            if h_lower in col_lower_name or col_lower_name in h_lower:
                return col

    # 3. 类型匹配
    hint = hints[0].lower() if hints else ""
    strs = [c for c in df.columns if df[c].dtype == object]
    nums = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if any(kw in hint for kw in ["label", "name", "item", "category", "group", "国家", "地区", "名称", "项目"]):
        return strs[0] if strs else (nums[0] if nums else None)

    if any(kw in hint for kw in ["value", "score", "diff", "change"]):
        return nums[0] if nums else (strs[0] if strs else None)

    return None


def _build_html(title: str, chart_name: str, library: str, data_fmt: str, desc: str, embed: str) -> str:
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


def _detect_format(df: pd.DataFrame, item_col: str) -> str:
    """检测数据格式：单列 or 多列"""
    # 多列模式：除了 item 列外，还有多个数值列
    num_cols = [c for c in df.columns if c != item_col and pd.api.types.is_numeric_dtype(df[c])]
    
    if len(num_cols) > 1:
        return "multi"
    else:
        return "single"


def generate(
    df: pd.DataFrame = None,
    mapping: Dict[str, str] = None,
    options: Dict[str, Any] = None,
    excel_path: str = None,
    item: str = "item",
    value: str = "value",
    negative_cols: Optional[List[str]] = None,
    positive_cols: Optional[List[str]] = None,
    title: str = "对比条形图",
    **kwargs
) -> ChartResult:
    warnings = []
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

    item_col = mapping.get("item") or item
    value_col = mapping.get("value") or value
    title = options.get("title", title)

    _item = _auto_col(df,
    item_col,
    "item", "label", "name", "category",
    "国家", "地区", "城市", "名称", "项目", "维度"
)
    
    if _item is None or _item not in df.columns:
        return ChartResult(warnings=[f"找不到必填字段 [item]"])

    # 检测数据格式
    fmt = _detect_format(df, _item)

    if fmt == "multi":
        # 多列模式（李克特量表）
        return _generate_multi_column(df, _item, title, warnings)
    else:
        # 单列模式
        _value = _auto_col(df, value_col, "value", "score", "diff", "change")
        
        if _value is None or _value not in df.columns:
            return ChartResult(warnings=[f"找不到必填字段 [value]"])

        return _generate_single_column(df, _item, _value, title, warnings)


def _generate_single_column(df: pd.DataFrame, item_col: str, value_col: str, title: str, warnings: list) -> ChartResult:
    """单列模式：item + value"""
    
    d = df[[item_col, value_col]].copy()
    d = d.dropna()
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d = d[d[value_col].notna()]

    if len(d) == 0:
        return ChartResult(warnings=warnings + ["处理后无有效数据"])

    # 按绝对值排序
    d = d.sort_values(value_col, key=abs)

    # 创建 Plotly 图表
    fig = go.Figure()

    # 分离正值和负值
    positive = d[d[value_col] >= 0]
    negative = d[d[value_col] < 0]

    # 添加正值（蓝色）
    if len(positive) > 0:
        fig.add_trace(go.Bar(
            y=positive[item_col],
            x=positive[value_col],
            orientation='h',
            marker=dict(color='#005B9A'),
            name='正值',
            hovertemplate='<b>%{y}</b><br>%{x:.2f}<extra></extra>'
        ))

    # 添加负值（红色）
    if len(negative) > 0:
        fig.add_trace(go.Bar(
            y=negative[item_col],
            x=negative[value_col],
            orientation='h',
            marker=dict(color='#E74C3C'),
            name='负值',
            hovertemplate='<b>%{y}</b><br>%{x:.2f}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title='数值',
        yaxis_title='项目',
        barmode='relative',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font_family="Heiti SC, Microsoft YaHei, sans-serif",
        margin=dict(l=120, r=40, t=60, b=40),
        height=max(400, len(d) * 30),
        showlegend=True,
        hovermode='closest',
        yaxis=dict(
            tickfont=dict(size=11),
            showticklabels=True
        )
    )

    # 添加零线
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)

    chart_html = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    html = _build_html(title, "diverging_bar", "plotly", _DATA_FMT, "单列模式", chart_html)


    meta = {
        "chart_id": "diverging_bar",
        "format": "single",
        "n_rows": len(d),
        "item_col": item_col,
        "value_col": value_col,
        "positive_count": len(positive),
        "negative_count": len(negative),
    }

    return ChartResult(html=html, spec={}, warnings=warnings, meta=meta)


def _generate_multi_column(df: pd.DataFrame, item_col: str, title: str, warnings: list) -> ChartResult:
    """多列模式：李克特量表（堆叠正负值）"""
    
    d = df.copy()
    d = d.dropna()

    # 获取所有数值列（除了 item 列）
    num_cols = [c for c in d.columns if c != item_col and pd.api.types.is_numeric_dtype(d[c])]
    
    if len(num_cols) < 2:
        return ChartResult(warnings=["多列模式需要至少2个数值列"])

    # 转换为数值
    for col in num_cols:
        d[col] = pd.to_numeric(d[col], errors="coerce")

    # 分离负值列和正值列
    negative_cols = [c for c in num_cols if (d[c] < 0).any()]
    positive_cols = [c for c in num_cols if (d[c] > 0).any()]

    if not negative_cols or not positive_cols:
        return ChartResult(warnings=["需要同时包含负值列和正值列"])

    # 计算累积值
    d['negative_sum'] = d[negative_cols].sum(axis=1)
    d['positive_sum'] = d[positive_cols].sum(axis=1)

    # 按正值排序
    d = d.sort_values('positive_sum', ascending=True)

    # 创建 Plotly 图表
    fig = go.Figure()

    # 配色
    neg_colors = ['#E74C3C', '#C0392B', '#A93226', '#922B21']
    pos_colors = ['#005B9A', '#1E88E5', '#2E7D32', '#43A047']

    # 添加负值列（从右到左堆叠）
    for idx, col in enumerate(sorted(negative_cols, reverse=True)):
        fig.add_trace(go.Bar(
            y=d[item_col],
            x=d[col],
            orientation='h',
            marker=dict(color=neg_colors[idx % len(neg_colors)]),
            name=col,
            text=d[col].round(0).astype(str),
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate='<b>%{y}</b><br>' + col + ': %{x:.0f}<extra></extra>'
        ))

    # 添加正值列（从左到右堆叠）
    for idx, col in enumerate(sorted(positive_cols)):
        fig.add_trace(go.Bar(
            y=d[item_col],
            x=d[col],
            orientation='h',
            marker=dict(color=pos_colors[idx % len(pos_colors)]),
            name=col,
            text=d[col].round(0).astype(str),
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate='<b>%{y}</b><br>' + col + ': %{x:.0f}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        xaxis_title='数值',
        yaxis_title='项目',
        barmode='relative',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font_family="Heiti SC, Microsoft YaHei, sans-serif",
        margin=dict(l=120, r=40, t=60, b=40),
        height=max(400, len(d) * 30),
        showlegend=True,
        hovermode='closest',
        yaxis=dict(
            tickfont=dict(size=11),
            showticklabels=True
        )
    )

    # 添加零线
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)

    chart_html = pio.to_html(fig, full_html=False, include_plotlyjs="cdn")
    html = _build_html(title, "diverging_bar", "plotly", _DATA_FMT, "多列模式（李克特量表）", chart_html)


    meta = {
        "chart_id": "diverging_bar",
        "format": "multi",
        "n_rows": len(d),
        "item_col": item_col,
        "negative_cols": negative_cols,
        "positive_cols": positive_cols,
    }

    return ChartResult(html=html, spec={}, warnings=warnings, meta=meta)
