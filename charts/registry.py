# charts/registry.py
"""
Chart Registry - 图表元数据中心
从各图表 README 中提取的详细信息
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ChartMetadata:
    """图表元信息注册条目"""
    chart_id: str
    name: str
    category: str
    min_fields: int
    required_roles: List[str]
    optional_roles: List[str] = field(default_factory=list)
    field_type_req: Dict[str, str] = field(default_factory=dict)
    supports_aggregation: bool = True
    supports_time: bool = False
    render_backend: str = "plotly"
    interactive: bool = True
    output_format: str = "html"
    keywords: List[str] = field(default_factory=list)
    priority: int = 5
    desc: str = ""
    data_format: str = ""
    constraints: str = ""
    case_yaml: str = ""


# ── 图表注册表 ──────────────────────────────────────────────
REGISTRY: List[ChartMetadata] = [
    # 对比类 COMPARING
    ChartMetadata(chart_id="Marimekko_ABS", name="马里美科_ABS", category="对比类 COMPARING", min_fields=3,
                  required_roles=["x", "y", "group"],
                  desc="柱宽表示第一维度占比，柱内高度表示第二维度绝对值。适合对比不同品牌的规模和内部构成",
                  data_format="x列(品牌) + y列(销售额) + group列(产品类别)", constraints="双维占比；柱内高度为绝对值"),
    ChartMetadata(chart_id="Marimekko_PCT", name="马里美科_PCT", category="对比类 COMPARING", min_fields=3,
                  required_roles=["x", "y", "group"],
                  desc="柱宽表示第一维度占比，柱内高度表示第二维度占比。适合展示相对构成关系",
                  data_format="x列(品牌) + y列(销售额) + group列(产品类别)", constraints="双维占比；柱内高度为百分比"),
    ChartMetadata(chart_id="Bar_Chart", name="柱状图", category="对比类 COMPARING", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["series", "color"], desc="通过矩形高度编码数值，最常用的比较图表",
                  data_format="x列(类别) + y列(数值)", constraints="数值列≥0，y轴从零开始"),
    ChartMetadata(chart_id="Grouped_Bar_Chart", name="分组柱状图", category="对比类 COMPARING", min_fields=3,
                  required_roles=["x", "y", "series"], optional_roles=["color"], desc="同类别多分组并排显示，便于对比",
                  data_format="x列(类别) + 分组列 + y列(数值)", constraints="分组数≤5"),
    ChartMetadata(chart_id="Stacked_Bar_Chart", name="堆叠柱状图", category="对比类 COMPARING", min_fields=3,
                  required_roles=["x", "y", "series"], optional_roles=["color"], desc="堆叠分段比较，展示部分与整体关系",
                  data_format="x列(类别) + 分组列 + y列(数值)", constraints="数值≥0"),
    ChartMetadata(chart_id="Diverging_Bar_Chart", name="对比条形图", category="对比类 COMPARING", min_fields=2,
                  required_roles=["label", "value"], desc="正负对比展示", data_format="标签 + 正负值",
                  constraints="支持正负值"),
    ChartMetadata(chart_id="dot_plot", name="点图", category="对比类 COMPARING", min_fields=2, required_roles=["x", "y"],
                  desc="点的位置展示数值", data_format="x列 + y列", constraints="适合小数据集"),
    ChartMetadata(chart_id="waffle", name="华夫饼图", category="对比类 COMPARING", min_fields=2,
                  required_roles=["category", "value"], desc="网格占比展示", data_format="类别 + 数值",
                  constraints="总和=100"),
    ChartMetadata(chart_id="Bullet_Chart", name="靶心图", category="对比类 COMPARING", min_fields=3,
                  required_roles=["label", "actual", "target"], optional_roles=["low", "medium", "high"],
                  desc="目标达成率展示", data_format="类别+实际值 + 目标值 + 可选范围", constraints="KPI展示"),
    ChartMetadata(chart_id="Sankey_Chart", name="桑基图", category="对比类 COMPARING", min_fields=3,
                  required_roles=["source", "target", "value"], desc="展示流向和流量", data_format="源 + 目标 + 流量",
                  constraints="适合流程展示"),
    ChartMetadata(chart_id="Heatmap", name="热力图", category="对比类 COMPARING", min_fields=3, required_roles=["x", "y", "value"],
                  desc="通过颜色深浅展示数值大小，适合多维数据", data_format="x列 + y列 + 数值列",
                  constraints="支持大量数据点"),
    ChartMetadata(chart_id="Waterfall", name="瀑布图", category="对比类 COMPARING", min_fields=2, required_roles=["x", "y"],
                optional_roles=["type"], desc="展示从起点到终点的累积变化过程，适合分析各阶段增减贡献。",
                data_format="x列(阶段) + y列(数值；首行为起始值，中间为增减值，末行可为总计值) [+ type列(可选：absolute/relative/total)]",
                constraints="支持正负值；至少2行数据；默认首行为absolute、末行为total；中间默认relative"),


    # 时间趋势类 TIME
    ChartMetadata(chart_id="Line_Chart", name="折线图", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["series"], desc="展示数据随时间或其他连续变量的变化趋势",
                  data_format="x列(时间/连续) + y列(数值)", constraints="适合时间序列", supports_time=True),
    ChartMetadata(chart_id="Circular_Line_Chart", name="环形线图ongoing", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["series"], desc="展示数据随时间或其他连续变量的变化趋势",
                  data_format="x列(时间/连续) + y列(数值)", constraints="适合时间序列", supports_time=True),
    ChartMetadata(chart_id="Slope_Chart", name="斜率图", category="时间趋势类 TIME", min_fields=3,
                  required_roles=["group", "start", "end"],
                  desc="通过连线斜率展示两个时间点间的变化幅度和方向，用颜色编码增长(绿)与下降(红)，自动按变化幅度排序",
                  data_format="group列(实体名称) + start列(起始值) + end列(终止值)",
                  constraints="实体数≤30；仅支持两个时间点对比", supports_time=True),
    ChartMetadata(chart_id="Sparkline", name="迷你图", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"], desc="极简的趋势线条图，专为表格嵌入设计。它为每一行数据生成一个紧凑的趋势迷你图，通过颜色编码快速传达数据的整体趋势方向", data_format="x列(时间) + y列(数值)", constraints="节省空间", supports_time=True),
    ChartMetadata(chart_id="Bump_Chart", name="凹凸图", category="时间趋势类 TIME", min_fields=3,
                  required_roles=["x", "y", "group"], optional_roles=["highlight"],
                  desc="展示多个实体的排名随时间的变化。通过相对排名而非绝对值来展示数据，适合识别黑马和掉队者。",
                  data_format="x列(时间) + y列(排名/分数) + group列(实体名称)",
                  constraints="实体数≤15个，自动检测，支持高亮", supports_time=True, ),
    ChartMetadata(chart_id="Cycle_Chart", name="周期图", category="时间趋势类 TIME", min_fields=2, required_roles=["time", "value"], desc="用于展示周期性模式。支持宽格式（首列为周期，如年份；其余列为相位，如月份/类别）和长格式（time + value + group），可自动识别并绘制多条周期线及均值参考线。", data_format="宽格式: period列 + 多个phase列；或 长格式: time列 + value列 + group列(可选)",
                  constraints="至少1列时间/周期字段与1列数值字段；若为宽格式建议首列可解析为年份/时间；其余列需可数值化"),
    ChartMetadata(chart_id="Area_Chart", name="面积图", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["series"], desc="折线图的填充版本", data_format="x列(时间) + y列(数值)",
                  constraints="适合时间序列", supports_time=True),
    ChartMetadata(chart_id="Stacked_Area_Chart", name="堆积面积图ongooing", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["series"], desc="折线图的填充版本", data_format="x列(时间) + y列(数值)",
                  constraints="适合时间序列", supports_time=True),
    ChartMetadata(chart_id="Streamgraph", name="河流图ongooing", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["series"], desc="折线图的填充版本", data_format="x列(时间) + y列(数值)",
                  constraints="适合时间序列", supports_time=True),
    ChartMetadata(
            chart_id="Horizon_Chart", name="地平线图", category="时间趋势类 TIME", min_fields=2, required_roles=["x", "y"],
            optional_roles=["series"],
            desc="将时间序列按幅度分层并折叠叠加的紧凑趋势图，适合在有限空间比较多条序列",
            data_format="x列(时间/顺序) + y列(数值，支持单列或多列；可选series分组)",
            constraints="需要有序x轴；y需为数值；分层(bands)越多细节越高但识别成本上升",
            supports_time=True),
    ChartMetadata(chart_id="Connected_Scatterplot", name="连线散点图", category="时间趋势类 TIME", min_fields=2,
                  required_roles=["x", "y"], optional_roles=["order", "size"],
                  desc="在散点基础上用线段连接各点，展示数据的演变过程或轨迹。适合展示有序路径、时间序列或因果关系。",
                  data_format="x列(数值) + y列(数值) + 可选order列(排序) + 可选size列(标记大小)",
                  constraints="支持自动排序"),

    # 分布类 DISTRIBUTION
    ChartMetadata(chart_id="histogram_chart", name="直方图", category="分布类 DISTRIBUTION", min_fields=1, required_roles=["value"],
                  desc="展示数值分布情况", data_format="数值列", constraints="自动分组"),
    ChartMetadata(chart_id="pyramid_chart", name="金字塔图", category="分布类 DISTRIBUTION", min_fields=2,
                  required_roles=["label", "value"], desc="金字塔形占比展示", data_format="标签 + 数值",
                  constraints="创意展示"),
    ChartMetadata(chart_id="error_bar_chart", name="误差条形图", category="分布类 DISTRIBUTION", min_fields=2,
                  required_roles=["label", "value"], desc="金字塔形占比展示", data_format="标签 + 数值",
                  constraints="创意展示"),
    ChartMetadata(chart_id="boxplot_chart", name="箱线图", category="分布类 DISTRIBUTION", min_fields=1, required_roles=["y"],
                  optional_roles=["x"], desc="展示数据的四分位数和异常值", data_format="数值列 + 可选分组列",
                  constraints="适合对比分布"),
    ChartMetadata(chart_id="candlestick", name="蜡烛图", category="分布类 DISTRIBUTION", min_fields=5,
                  required_roles=["date", "open", "high", "low", "close"], desc="股票价格展示",
                  data_format="日期 + 开盘 + 最高 + 最低 + 收盘", constraints="金融数据专用", supports_time=True),
    ChartMetadata(chart_id="violin_chart", name="小提琴图", category="分布类 DISTRIBUTION", min_fields=1, required_roles=["y"],
                  optional_roles=["x"], desc="展示数据分布的密度", data_format="数值列 + 可选分组列",
                  constraints="数据量≥20"),
    ChartMetadata(chart_id="Ridgeline_Plot", name="山脊线图ongoing", category="分布类 DISTRIBUTION", min_fields=1, required_roles=["y"],
                  optional_roles=["x"], desc="展示数据分布的密度", data_format="数值列 + 可选分组列",
                  constraints="数据量≥20"),
    ChartMetadata(chart_id="BEESWARM_PLOT", name="分簇散点图ongoing", category="分布类 DISTRIBUTION", min_fields=1, required_roles=["y"],
                  optional_roles=["x"], desc="展示数据分布的密度", data_format="数值列 + 可选分组列",
                  constraints="数据量≥20"),
    ChartMetadata(chart_id="stem_leaf", name="茎叶图", category="分布类 DISTRIBUTION", min_fields=1, required_roles=["value"], desc="数据分布的详细展示", data_format="数值列", constraints="适合小数据集"),

    # 地理类 GEOSPATIAL
    ChartMetadata(chart_id="bubble_map", name="气泡地图", category="地理类 GEOSPATIAL", min_fields=3,
                  required_roles=["lat", "lon", "value"], optional_roles=["color"], desc="地理位置上的气泡大小表示数值",
                  data_format="纬度 + 经度 + 数值", constraints="需要地理坐标"),
    ChartMetadata(chart_id="choropleth_map", name="地图", category="地理类 GEOSPATIAL", min_fields=2,
                  required_roles=["region", "value"], desc="地理区域着色展示", data_format="地区 + 数值",
                  constraints="需要地理数据"),
    ChartMetadata(chart_id="dot_density_map", name="点密度图", category="地理类 GEOSPATIAL", min_fields=2,
                  required_roles=["lat", "lon"], desc="地理分布密度展示", data_format="纬度 + 经度",
                  constraints="需要地理坐标"),
    ChartMetadata(chart_id="flow_map", name="流向图", category="地理类 GEOSPATIAL", min_fields=4,
                  required_roles=["source_lat", "source_lon", "target_lat", "target_lon"], optional_roles=["value"],
                  desc="地理流向展示", data_format="源坐标 + 目标坐标 + 可选流量", constraints="需要地理坐标"),

    # 关系类 RELATIONSHIP
    ChartMetadata(chart_id="scatter_plot", name="散点图", category="关系类 RELATIONSHIP", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["size", "color"], desc="展示两个数值变量之间的相关性",
                  data_format="x列(数值) + y列(数值)", constraints="至少需要两个数值列"),
    ChartMetadata(chart_id="Parallel_Coordinates_Plot", name="平行坐标图ongoing", category="关系类 RELATIONSHIP", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["size", "color"], desc="展示两个数值变量之间的相关性",
                  data_format="x列(数值) + y列(数值)", constraints="至少需要两个数值列"),
    ChartMetadata(chart_id="Radar_Charts", name="雷达图ongoing", category="关系类 RELATIONSHIP", min_fields=2, required_roles=["x", "y"],
                  optional_roles=["size", "color"], desc="展示两个数值变量之间的相关性",
                  data_format="x列(数值) + y列(数值)", constraints="至少需要两个数值列"),
    ChartMetadata(chart_id="chord_diagram", name="弦图", category="关系类 RELATIONSHIP", min_fields=3,
                  required_roles=["source", "target", "value"], desc="展示多个实体之间的关系强度",
                  data_format="源 + 目标 + 权重", constraints="适合网络关系"),
    ChartMetadata(chart_id="Arc_Chart", name="弧图", category="关系类 RELATIONSHIP", min_fields=3, required_roles=["x", "y", "z"],
                  desc="弧形展示路径，数据标签半圆展示流出值", data_format="流出x + 流入y + 流出值Z",
                  constraints="关系图表"),
    ChartMetadata(chart_id="Network_Diagram", name="网络图", category="关系类 RELATIONSHIP", min_fields=3,
                  required_roles=["source", "target"], optional_roles=["weight"], desc="展示节点和连接关系",
                  data_format="源 + 目标 + 可选权重", constraints="适合网络分析"),

    # 占比图 PART-TO-WHOLE
    ChartMetadata(chart_id="treemap", name="树图ongoing", category="占比图 PART-TO-WHOLE", min_fields=2, required_roles=["labels", "values"], optional_roles=["parents"], desc="矩形面积表示数值大小", data_format="标签 + 数值 + 可选父级", constraints="支持多层级"),
    ChartMetadata(chart_id="sunburst", name="旭日图", category="占比图 PART-TO-WHOLE", min_fields=3, required_roles=["labels", "parents", "values"], desc="多层级占比展示", data_format="标签 + 父级 + 数值", constraints="支持多层级"),
    ChartMetadata(chart_id="nightingale", name="南丁格尔玫瑰图", category="占比图 PART-TO-WHOLE", min_fields=2,
                  required_roles=["category", "value"], desc="极坐标占比展示", data_format="类别 + 数值",
                  constraints="创意展示"),
    ChartMetadata(chart_id="pie", name="饼图", category="占比图 PART-TO-WHOLE", min_fields=2, required_roles=["label", "value"],
                  optional_roles=["color"], desc="展示各部分占整体的比例", data_format="标签列 + 数值列",
                  constraints="类别数≤8，总和=100%"),
    ChartMetadata(chart_id="voronoi", name="沃罗诺伊图", category="占比图 PART-TO-WHOLE", min_fields=2, required_roles=["lat", "lon"],
                  optional_roles=["value"], desc="地理分割展示", data_format="纬度 + 经度 + 可选数值",
                  constraints="需要地理坐标"),
]


# 可选但推荐：建立索引，提高 get_chart 性能
_REGISTRY_DICT: Dict[str, ChartMetadata] = {c.chart_id: c for c in REGISTRY}


def get_chart(chart_id: str) -> Optional[ChartMetadata]:
    """根据 chart_id 获取图表元数据"""
    return _REGISTRY_DICT.get(chart_id)


def list_charts(category: str = None) -> List[ChartMetadata]:
    """列出图表；可按分类过滤"""
    if category:
        return [c for c in REGISTRY if c.category == category]
    return list(REGISTRY)


def list_categories() -> List[str]:
    """列出所有分类"""
    return sorted({c.category for c in REGISTRY})
