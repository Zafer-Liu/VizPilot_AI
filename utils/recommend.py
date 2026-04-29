"""
ChartRecommender - 根据用户数据结构自动推荐合适的图表类型
"""
import os
import pandas as pd
from typing import Optional, List, Dict, Any

__all__ = ["ChartRecommender", "ChartInfo"]


class ChartInfo:
    """图表元信息"""
    def __init__(self, name: str, title: str, category: str, min_cols: int,
                 col_keywords: List[str], priority: int,
                 output_format: str, library: str,
                 data_format: str, desc: str):
        self.name = name
        self.title = title
        self.category = category
        self.min_cols = min_cols
        self.col_keywords = col_keywords  # 列名关键词列表（越大越匹配）
        self.priority = priority
        self.output_format = output_format  # "html" | "png" | "both"
        self.library = library
        self.data_format = data_format
        self.desc = desc

    def __repr__(self):
        return f"<ChartInfo {self.name}>"


# 图表注册表（去重+完整化）
_CHART_REGISTRY: List[ChartInfo] = [
    # 比较
    ChartInfo("bar_chart",        "柱状图",    "比较",  2, ["类别","x","y","数值","销量","金额","count","amount"], 5, "png", "matplotlib", "x列(类别) + y列(数值)", "最常用的比较图表，柱高=数值"),
    ChartInfo("stacked_bar",     "堆叠柱状图","比较", 3, ["分类","分类","sub","segment","stack","堆叠"], 4, "png", "matplotlib", "x列(类别) + 分组列 + y列(数值)", "堆叠分段比较"),
    ChartInfo("diverging_bar",   "对比条形图","比较", 2, ["item","项目","diff","偏差","change","变化","diverg"], 4, "png", "matplotlib", "项目列 + 偏差值列", "正负对比"),
    ChartInfo("bullet_chart",    "靶心图",    "比较", 3, ["实际","actual","目标","target","range","区间","级别","级别"], 4, "png", "matplotlib", "实际/目标/区间列", "达成率 vs 目标"),
    ChartInfo("waffle",         "华夫格",    "比较", 2, ["类别","category","value","数值","waffle","比例"], 3, "png", "matplotlib", "类别 + 数值", "类别占比可视化"),
    ChartInfo("marimekko",      "Marimekko图","比较", 3, ["segment","细分","sub","value","数值","份额","mekko"], 3, "png", "matplotlib", "分段 + 子类 + 数值", "Marimekko 瀑布矩阵"),
    ChartInfo("bump_chart",      "凹凸图",    "排名", 4, ["rank","排名","time","时间","group","分组","score","分数"], 4, "html", "matplotlib", "时间 + 分组 + 排名/分数", "随时间变化的排名"),
    ChartInfo("lollipop",       "棒棒糖图",  "比较", 2, ["category","类目","value","数值","lollipop"], 3, "png", "matplotlib", "类别 + 数值", "简洁比较"),
    ChartInfo("dumbbell",         "哑铃图",   "变化", 3, ["start","起点","end","终点","group","分组","diff","差值"], 4, "png", "matplotlib", "起点 + 终点 + 分组", "变化幅度可视化"),

    # 趋势/时间
    ChartInfo("line_chart",      "折线图",   "趋势",  2, ["x","y","日期","time","数值","value","趋势","trend"], 5, "html", "matplotlib", "X列(时间/类别) + Y列(数值)", "时间序列趋势"),
    ChartInfo("area_chart",      "面积图",   "趋势", 2, ["x","y","area","面积","趋势"], 4, "html", "matplotlib", "X列 + Y列(面积值)", "面积堆叠趋势"),
    ChartInfo("horizon_chart",   "地平线图",  "趋势", 2, ["x","y","date","time","value","数值"], 3, "html", "matplotlib", "时间列 + 数值列", "紧凑时间序列"),
    ChartInfo("sparkline",      "迷你图",   "趋势", 1, ["y","数值","value","trend","spark"], 4, "html", "matplotlib", "单列数值序列", "inline迷你趋势"),
    ChartInfo("slope_chart",    "斜率图",   "变化", 3, ["start","起点","end","终点","group","分组","变化量"], 4, "png", "matplotlib", "起点 + 终点 + 分组列", "组间变化对比"),
    ChartInfo("cycle_chart",      "周期图",   "周期", 2, ["phase","angle","value","cycle","周期","星期","hour","hour"], 3, "html", "matplotlib", "相位 + 数值", "周期性模式"),
    ChartInfo("bar_chart",        "柱状图",   "时间", 2, ["date","time","类","y","数值","月","month"], 5, "png", "matplotlib", "时间 + 数值", "时间分组比较"),
    ChartInfo("line_chart",       "折线图",   "时间", 2, ["date","time","y","数值","月","month","年"], 5, "html", "matplotlib", "时间 + 数值", "时间序列"),
    ChartInfo("area_chart",       "面积图",   "时间", 2, ["x","y","area"], 4, "html", "matplotlib", "x(时间) + y(数值)", "累积趋势"),

    # 分布
    ChartInfo("histogram_chart",  "直方图",   "分布", 1, ["x","y","数值","value","count","频率","frequency","分布"], 5, "html", "matplotlib", "数值列", "频次分布"),
    ChartInfo("boxplot_chart",   "箱线图",   "分布", 2, ["value","分组","category","y","数值"], 4, "html", "matplotlib", "数值列 [+分组列]", "分布统计（median/quartile/outlier）"),
    ChartInfo("violin_chart",    "小提琴图", "分布", 2, ["x","y","value","数值","分组","category"], 3, "html", "matplotlib", "X(分组) + Y(数值", "分布密度+中位数"),
    ChartInfo("density_plot",    "密度图",   "分布", 2, ["x","y","density","密度"], 3, "html", "matplotlib", "X列 + Y列", "密度等高线"),
    ChartInfo("stem_leaf",       "茎叶图",   "分布", 1, ["value","数值","stem","leaf"], 2, "text", "matplotlib", "数值列", "文本格式分布"),

    # 占比
    ChartInfo("pie",            "饼图",     "占比", 2, ["label","name","类别","占比","percent","%","比例"], 4, "html", "matplotlib", "标签列 + 数值列", "占比对比"),
    ChartInfo("donut",           "环形图",   "占比", 2, ["label","name","value","数值","占比"], 3, "html", "matplotlib", "标签 + 数值", "环形占比"),
    ChartInfo("treemap",        "矩形树图", "占比", 2, ["path","label","name","value","size","占比"], 4, "html", "plotly", "路径/标签 + 数值", "层级占比"),
    ChartInfo("sunburst",       "旭日图",   "层级占比", 2, ["path","parent","child","root","hier","层级","层次"], 4, "html", "plotly", "父子路径", "多层级占比"),
    ChartInfo("nightingale",    "南丁格尔玫瑰图","占比", 2, ["category","value","angle","月","month","年","year","扇区"], 3, "html", "matplotlib", "分类 + 数值 [+ 时间]", "极坐标占比"),
    ChartInfo("waffle",         "华夫格",   "占比", 2, ["category","value","waffle","占比"], 3, "html", "matplotlib", "类别 + 数值", "单元格占比"),
    ChartInfo("pie",            "饼图",    "占比", 2, ["name","label","value","percent","比例","占比"], 4, "html", "matplotlib", "标签 + 数值", "饼图"),

    # 关系
    ChartInfo("scatter_plot",    "散点图",   "关系", 2, ["x","y","数值","latitude","lat","lon","lng"], 5, "html", "matplotlib", "X列 + Y列 [+ size列 + color列]", "双变量关系"),
    ChartInfo("bubble_chart",    "气泡图",   "关系", 3, ["x","y","size","z","bubble","气泡","经纬度"], 4, "html", "plotly", "X + Y + Size列", "三维关系 scatter x/y/size"),
    ChartInfo("hexbin",         "六边形密度图","关系", 2, ["x","y","density","密度","hexbin"], 3, "html", "matplotlib", "X列 + Y列", "密度散点"),
    ChartInfo("arc_chart",       "弧图",    "关系", 3, ["source","起点","target","终点","flow","流向","流量","migration"], 5, "html", "matplotlib", "起点列 + 终点列 + 流量列", "节点沿轴排列的流向关系"),
    ChartInfo("chord_diagram",   "弦图",    "关系", 2, ["source","target","value","matrix","邻接","chord","国家","country"], 4, "html", "holoviews", "source/target/value 三列或邻接矩阵", "节点环状排列的相互关系"),
    ChartInfo("sankey",         "桑基图",   "流向", 3, ["source","起点","target","终点","value","flow","流量","weight","权重"], 5, "html", "plotly", "source + target + value 三列", "节点间流量流向"),
    ChartInfo("network_diagram",  "网络图",   "关系", 2, ["source","target","node","edge","weight","关系","link"], 3, "html", "matplotlib", "source + target [+ weight] 三列", "网络/图谱关系"),
    ChartInfo("heatmap",        "热力图",   "关系", 2, ["row","col","value","x","y","热力","heatmap"], 4, "html", "matplotlib", "行 + 列 + 值 三列", "矩阵关联系数"),
    ChartInfo("flow_map",        "流向地图", "地理流向", 4, ["source","起点","target","终点","flow","lat","lon","origin","destination"], 4, "html", "plotly", "起点+终点+流量+经纬度四列", "地理流向"),
    ChartInfo("alluvial",        "冲积图",   "流向", 3, ["stage","stage","source","target","value","flow"], 3, "html", "matplotlib", "阶段+分组+数值", "流程变化"),
    ChartInfo("sankey",         "桑基图",   "流向", 3, ["source","起点","target","终点","flow","value","权重"], 5, "html", "plotly", "source + target + value", "流量桑基图"),

    # 地理
    ChartInfo("choropleth_map",  "等值区域图", "地理", 2, ["province","省","city","城市","country","国家","ISO","region","location","地理","geo"], 5, "html", "plotly", "省份/国家列 + 数值列", "按地理区域着色的数值分布"),
    ChartInfo("bubble_map",      "气泡地图",  "地理", 3, ["lat","lon","longitude","latitude","location","城市","数值","value","size","bubble"], 4, "html", "plotly", "经度 + 纬度 + 数值 [+ size列]", "地理位置+数值大小"),
    ChartInfo("dot_density_map", "点密度地图", "地理", 2, ["lat","lon","location","城市","密度","density"], 3, "html", "matplotlib", "经纬度 + 数值", "点密度反映数值"),

    # 金融
    ChartInfo("candlestick",     "K线图",   "金融", 4, ["open","close","high","low","volume","时间","date","OHLC"], 5, "html", "mplfinance", "时间+Open+High+Low+Close+Volume", "OHLCV 金融数据"),
    ChartInfo("ohlc",           "OHLC图",  "金融", 4, ["open","high","low","close","ohlc","金融","日期","date"], 4, "html", "matplotlib", "时间 + Open + High + Low + Close", "OHLC"),
    ChartInfo("trend_line",     "趋势线图", "金融", 2, ["x","y","trend","趋势","回归","regression"], 3, "html", "matplotlib", "X列 + Y列", "带回归线的散点"),

    # 文本
    ChartInfo("wordcloud",      "词云",    "文本", 1, ["word","词语","frequency","freq","频次","count","文本","text","关键词","keyword"], 4, "html", "matplotlib", "词语 + 频次列", "高频词可视化"),
    ChartInfo("word_tree",      "词语树",   "文本", 1, ["root","text","词语","word","tree","树"], 3, "html", "matplotlib", "根词 + 分支词列表", "词语包含关系"),

    # 极坐标
    ChartInfo("radar_chart",     "雷达图",  "多维", 3, ["axis","维度","dimension","score","指标","能力"], 4, "html", "matplotlib", "维度名 + 数值列", "多维指标对比"),
    ChartInfo("polar_bar",       "极坐标柱状图","周期", 2, ["angle","theta","category","类","polar","value","数值"], 3, "html", "matplotlib", "角度/类别列 + 数值列", "周期/方位数据"),
    ChartInfo("polar_area",      "极面积图", "占比", 2, ["angle","theta","category","area","value","数值","极坐标"], 3, "html", "matplotlib", "角度 + 数值", "极坐标面积"),

    # 其他
    ChartInfo("waterfall",       "瀑布图",   "变化", 3, ["start","delta","end","累计","累计值","change","变化","瀑布"], 4, "html", "matplotlib", "起点 + 增量 + 终点 三列", "累计变化分解"),
    ChartInfo("calendarheatmap",  "日历热图", "时间", 2, ["date","日期","day","value","数值","日历","calendar"], 4, "html", "matplotlib", "日期列 + 数值列", "日历热力图"),
    ChartInfo("heatmap",         "热力图",   "矩阵", 2, ["row","col","value","x","y","heatmap"], 4, "html", "matplotlib", "行 + 列 + 值 三列", "关系/相关系数矩阵"),
    ChartInfo("heatmap",         "相关矩阵", "统计", 2, ["corr","相关","correlation","matrix","矩阵","特征","feature"], 3, "html", "matplotlib", "数值列两两配对", "特征相关性"),
    ChartInfo("treemap",         "矩阵树图", "层级", 2, ["parent","child","hier","层级","path","root","sub","parent_id"], 3, "html", "plotly", "父子路径列", "层级结构"),
    ChartInfo("parcoords",       "平行坐标图","多维", 3, ["dim","维度","index","feature","指标","列","column"], 3, "html", "plotly", "多列数值（每列一个维度", "多维平行坐标"),
]


def _load_example_xlsx(chart_name: str) -> pd.DataFrame:
    """加载图表示例 Excel 数据"""
    xlsx = os.path.join(os.path.dirname(__file__), "..", "charts", chart_name, "example.xlsx")
    xlsx = os.path.abspath(xlsx)
    if os.path.exists(xlsx):
        try:
            return pd.read_excel(xlsx)
        except Exception:
            pass
    csv = os.path.join(os.path.dirname(__file__), "..", "charts", chart_name, "example.csv")
    csv = os.path.abspath(csv)
    if os.path.exists(csv):
        try:
            return pd.read_csv(csv, encoding="utf-8-sig")
        except Exception:
            pass
    raise FileNotFoundError(f"未找到 {chart_name} 的示例数据文件 example.xlsx 或 example.csv")


class ChartRecommender:
    """
    根据用户数据结构自动推荐合适的图表类型
    用法：
        recommender = ChartRecommender(df)
        charts = recommender.recommend(limit=5)
        for c in charts:
            print(c.name, c.title)
    """

    def __init__(self, df_or_path: Any = None):
        self.df: Optional[pd.DataFrame] = None
        self._stats: Dict[str, Any] = {}
        if df_or_path is not None:
            self.load(df_or_path)

    def load(self, df_or_path: Any) -> "ChartRecommender":
        """传入 DataFrame 或 Excel 文件路径，自动识别列类型"""
        if isinstance(df_or_path, pd.DataFrame):
            self.df = df_or_path.copy()
        elif isinstance(df_or_path, str) and os.path.exists(df_or_path):
            self.df = pd.read_excel(df_or_path)
        else:
            raise FileNotFoundError(f"文件不存在：{df_or_path}")
        self._analyze()
        return self

    def _analyze(self):
        """分析 DataFrame，缓存统计信息"""
        from numpy import issubdtype
        from pandas import DataFrame
        df = self.df
        num_cols = [c for c in df.columns
                    if issubdtype(df[c].dtype, float) or issubdtype(df[c].dtype, int)]
        cat_cols = [c for c in df.columns
                   if df[c].dtype == object or str(df[c].dtype) == "category"
                   or str(df[c].dtype).startswith("datetime")]
        dt_cols = [c for c in df.columns if str(df[c].dtype).startswith("datetime")]
        geo_cols = [c for c in df.columns
                    if any(k in c.lower()
                           for k in ["lat","lon","lng","经度","纬度","province","city","country","国家","省","city","location","城市"])]
        self._stats = {
            "rows": len(df), "cols": len(df.columns),
            "numeric": num_cols, "categorical": cat_cols, "datetime": dt_cols,
            "geographic": geo_cols,
            "all_cols": list(df.columns),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
        }

    def describe(self) -> dict:
        """返回数据分析摘要"""
        return {
            "总行数": self.df.shape[0],
            "总列数": self.df.shape[1],
            "数值列": self._stats["numeric"],
            "分类型列": self._stats["categorical"],
            "时间列": self._stats["datetime"],
            "地理列": self._stats["geographic"],
            "全部列": self._stats["all_cols"],
        }

    def _match_score(self, chart: ChartInfo) -> int:
        """计算图表与当前数据的匹配分"""
        col_text = " ".join([
            " ".join(self._stats["all_cols"]),
            " ".join(self._stats["numeric"]),
            " ".join(self._stats["geographic"]),
        ]).lower()
        score = 0
        for kw in chart.col_keywords:
            if kw.lower() in col_text:
                score += chart.priority
        # 行数惩罚
        if self.df.shape[0] < 5 and chart.min_cols >= 3:
            score -= 2
        return score

    def recommend(self, limit: int = 5, library: str = None,
                 category: str = None) -> List[ChartInfo]:
        """
        推荐图表列表（按匹配度排序）

        参数：
            limit:    返回数量
            library:   筛选绘图库（如 "matplotlib", "plotly", "holoviews"）
            category:  筛选分类（如 "关系,趋势,地理"）
        """
        candidates = _CHART_REGISTRY
        if library:
            candidates = [c for c in candidates if library == c.library]
        if category:
            cats = [x.strip() for x in category.split(",")]
            candidates = [c for c in candidates
                          if any(cat in c.category for cat in cats)]

        scored = [(self._match_score(c), c) for c in candidates]
        scored.sort(key=lambda x: -x[0])
        return [c for s, c in scored[:limit]]

    @staticmethod
    def chart_info(name: str) -> Dict[str, str]:
        """查看指定图表的输入格式要求"""
        for c in _CHART_REGISTRY:
            if c.name == name:
                return {"format": c.data_format, "desc": c.desc,
                        "library": c.library, "output": c.output_format,
                        "min_cols": c.min_cols,
                        "keywords": c.col_keywords}
        return {}

    def _load_example(self, chart_name: str) -> pd.DataFrame:
        """加载指定图表的示例数据（供 generate(df=None 时自动加载）"""
        return _load_example_xlsx(chart_name)
