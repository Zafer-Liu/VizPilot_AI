"""
验证完整流程：Excel → 推荐 → 生成 HTML
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.recommend import ChartRecommender
import pandas as pd

# ── 测试1: 推荐功能 ─────────────────────────────────────
df = pd.DataFrame({
    "国家": ["中国", "美国", "日本", "德国", "法国"],
    "GDP": [18, 24, 5, 4, 3],
    "人口": [14, 3, 1, 0.8, 0.7],
})
r = ChartRecommender(df)
charts = r.recommend(limit=5)
print("=" * 60)
print("测试1: ChartRecommender")
print(f"数据: {df.shape[0]}行 x {df.shape[1]}列")
print(f"列: {list(df.columns)}")
print(f"推荐图表 TOP {len(charts)}:")
for i, c in enumerate(charts, 1):
    print(f"  {i}. [{c.name}] {c.title} (适合: {c.data_format})")
    print(f"      库: {c.library} | 输出: {c.output_format}")

# ── 测试2: 各图生成 HTML ────────────────────────────────
print("\n" + "=" * 60)
print("测试2: 各图 generate(excel_path=...)")
charts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "charts")

# 选择几个有代表性的图来测试
test_charts = ["bar_chart", "line_chart", "pie", "histogram_chart",
               "arc_chart", "sankey", "choropleth_map", "wordcloud"]

for name in test_charts:
    chart_py = os.path.join(charts_dir, name, "chart.py")
    result_html = os.path.join(charts_dir, name, "result.html")
    if not os.path.exists(chart_py):
        print(f"  [SKIP] {name}: chart.py 不存在")
        continue
    try:
        # 用 example.xlsx 测试（如果存在）
        example_xlsx = os.path.join(charts_dir, name, "example.xlsx")
        if os.path.exists(example_xlsx):
            # 读取并查看列
            example_df = pd.read_excel(example_xlsx)
            cols = list(example_df.columns)
            print(f"\n  [{name}] example.xlsx 列: {cols}")

            # 动态 import 并调用
            import importlib
            spec = importlib.util.spec_from_file_location(f"charts.{name}.chart", chart_py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # 构建调用参数
            gen = mod.generate
            # 简单策略：传入 excel_path
            gen(excel_path=example_xlsx)

            if os.path.exists(result_html):
                size = os.path.getsize(result_html)
                print(f"    → result.html {size/1024:.1f} KB ✓")
            else:
                print(f"    → result.html 未生成")
        else:
            print(f"\n  [SKIP] {name}: 无 example.xlsx")
    except FileNotFoundError as e:
        print(f"\n  [SKIP] {name}: {e}")
    except Exception as e:
        print(f"\n  [ERROR] {name}: {e}")

print("\n" + "=" * 60)
print("测试完成")
