"""
ChartStyle - 统一图表风格配置
支持 matplotlib / seaborn 参数预设
"""

from dataclasses import dataclass
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

__all__ = ["ChartStyle"]


@dataclass
class StylePreset:
    name: str
    palette: str
    font_family: str
    spine_visible: bool
    grid_alpha: float
    title_size: int
    label_size: int
    tick_size: int
    figure_dpi: int


PRESETS = {
    # 学术风格：简洁、黑白为主
    "academic": StylePreset(
        name="academic",
        palette="Greys",
        font_family="Times New Roman",
        spine_visible=True,
        grid_alpha=0.3,
        title_size=14,
        label_size=12,
        tick_size=10,
        figure_dpi=150,
    ),
    # 商业风格：蓝绿为主，干净
    "business": StylePreset(
        name="business",
        palette="Blues",
        font_family="Microsoft YaHei",
        spine_visible=False,
        grid_alpha=0.2,
        title_size=14,
        label_size=12,
        tick_size=10,
        figure_dpi=150,
    ),
    # 深色科技风格
    "tech": StylePreset(
        name="tech",
        palette="coolwarm",
        font_family="Consolas",
        spine_visible=False,
        grid_alpha=0.15,
        title_size=14,
        label_size=12,
        tick_size=10,
        figure_dpi=150,
    ),
    # 暖色调演示风格
    "warm": StylePreset(
        name="warm",
        palette="Oranges",
        font_family="Microsoft YaHei",
        spine_visible=True,
        grid_alpha=0.25,
        title_size=14,
        label_size=12,
        tick_size=10,
        figure_dpi=150,
    ),
}


class ChartStyle:
    """
    全局样式管理器

    用法：
        ChartStyle.apply("business")
        # 之后所有 matplotlib/seaborn 图表都会使用该风格
    """

    _current: Optional[StylePreset] = None

    @classmethod
    def apply(cls, preset_name: str = "business") -> StylePreset:
        """
        应用预设风格
        """
        preset = PRESETS.get(preset_name)
        if preset is None:
            raise ValueError(
                f"未知预设: {preset_name}，可用: {list(PRESETS.keys())}"
            )

        # matplotlib 全局设置
        plt.rcParams.update({
            "font.family": preset.font_family,
            "font.size": preset.label_size,
            "axes.titlesize": preset.title_size,
            "axes.labelsize": preset.label_size,
            "xtick.labelsize": preset.tick_size,
            "ytick.labelsize": preset.tick_size,
            "axes.spines.top": preset.spine_visible,
            "axes.spines.right": preset.spine_visible,
            "axes.grid": True,
            "grid.alpha": preset.grid_alpha,
            "figure.dpi": preset.figure_dpi,
            "savefig.dpi": preset.figure_dpi,
        })

        # seaborn 风格
        sns.set_style("whitegrid" if preset.grid_alpha > 0 else "white")
        sns.set_palette(preset.palette)

        cls._current = preset
        return preset

    @classmethod
    def current(cls) -> Optional[StylePreset]:
        return cls._current

    @classmethod
    def available(cls) -> list[str]:
        return list(PRESETS.keys())
