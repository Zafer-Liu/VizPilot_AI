#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 增强推荐 - 支持任意字段角色（不仅仅是 x/y）"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import json
import re

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

CHART_PROJECT = Path(__file__).parent.parent
sys.path.insert(0, str(CHART_PROJECT))

logger.info(f"CHART_PROJECT: {CHART_PROJECT}")

try:
    from charts.registry import REGISTRY, get_chart

    logger.info(f"Successfully imported REGISTRY with {len(REGISTRY)} charts")
except Exception as e:
    logger.error(f"Failed to import REGISTRY: {e}", exc_info=True)
    raise


def build_charts_definition():
    """从注册表构建图表定义文本"""
    logger.debug("Building charts definition...")
    try:
        lines = ["AVAILABLE CHART TYPES (ONLY use these chart_id values):"]
        lines.append("")

        categories = sorted({c.category for c in REGISTRY})
        for category in categories:
            charts = [c for c in REGISTRY if c.category == category]
            lines.append(f"[{category}]")
            for chart in sorted(charts, key=lambda x: -x.priority):
                lines.append(f"  chart_id: {chart.chart_id}")
                lines.append(f"  name: {chart.name}")
                lines.append(f"  desc: {chart.desc}")
                lines.append(f"  required_fields: {', '.join(chart.required_roles)}")
                lines.append("")

        definition = "\n".join(lines)
        logger.debug(f"Charts definition built, length: {len(definition)}")
        return definition
    except Exception as e:
        logger.error(f"Failed to build charts definition: {e}", exc_info=True)
        return "AVAILABLE CHART TYPES:\n  chart_id: bar_chart\n  chart_id: line_chart\n  chart_id: scatter"


def extract_and_parse_json(response: str) -> Optional[List[Dict]]:
    """从 LLM 响应中提取并解析 JSON 数组"""
    logger.debug(f"Extracting JSON from response (length: {len(response)})")

    def _try_load(s: str):
        try:
            obj = json.loads(s)
            logger.debug(f"Successfully parsed JSON, type: {type(obj)}")
            return obj
        except Exception as e:
            logger.debug(f"JSON parse failed: {e}")
            return None

    try:
        if not response or not response.strip():
            logger.warning("Response is empty")
            return None

        text = response.strip()
        logger.debug(f"Response preview (first 300 chars): {repr(text[:300])}")

        # 直接解析
        logger.debug("Attempting direct JSON parse...")
        obj = _try_load(text)
        if isinstance(obj, list):
            logger.info(f"Direct parse succeeded, got {len(obj)} items")
            return obj

        # 提取 fenced code
        logger.debug("Attempting to extract fenced code...")
        for p in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
            m = re.search(p, text, flags=re.DOTALL | re.IGNORECASE)
            if m:
                logger.debug(f"Found fenced code with pattern: {p}")
                candidate = m.group(1).strip()
                obj = _try_load(candidate)
                if isinstance(obj, list):
                    logger.info(f"Fenced code parse succeeded, got {len(obj)} items")
                    return obj

        # 截取最外层方括号
        logger.debug("Attempting to extract brackets...")
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            logger.debug(f"Found brackets at positions {start}-{end}")
            candidate = text[start:end + 1].strip()
            candidate = re.sub(r",(\s*[\]}])", r"\1", candidate)
            obj = _try_load(candidate)
            if isinstance(obj, list):
                logger.info(f"Bracket extraction succeeded, got {len(obj)} items")
                return obj

        logger.warning("Failed to extract valid JSON array from response")
        return None

    except Exception as e:
        logger.error(f"Exception during JSON extraction: {e}", exc_info=True)
        return None


def get_allowed_chart_ids():
    """获取注册表中所有允许的 chart_id"""
    return {c.chart_id for c in REGISTRY}


def sanitize_and_validate_recommendations(
        recommendations: List[Dict[str, Any]],
        columns: List[str]
) -> List[Dict[str, Any]]:
    """
    严格清洗 + 校验（支持非xy图）：
    - 仅保留 chart_id 在 REGISTRY 白名单中的项
    - field_mapping 必须覆盖 required_roles
    - columns_to_keep 仅保留真实列
    """
    allowed_ids = get_allowed_chart_ids()
    valid_stars = {"五星推荐", "四星推荐", "三星推荐", "二星推荐", "一星推荐"}
    col_set = set(columns)

    cleaned = []
    for rec in recommendations or []:
        chart_id = str(rec.get("chart_id", "")).strip()
        if chart_id not in allowed_ids:
            logger.warning(f"[INVALID] chart_id not in REGISTRY: {chart_id}")
            continue

        chart = get_chart(chart_id)
        if not chart:
            logger.warning(f"[INVALID] chart_id cannot get_chart: {chart_id}")
            continue

        stars = rec.get("stars", "三星推荐")
        if stars not in valid_stars:
            stars = "三星推荐"

        # field_mapping（新主字段）
        fm = rec.get("field_mapping", {})
        if not isinstance(fm, dict):
            fm = {}

        # 兼容旧字段：xy 图可从 x_label/y_label 回填到 field_mapping
        if "x" in chart.required_roles and "x" not in fm and rec.get("x_label"):
            fm["x"] = rec.get("x_label")
        if "y" in chart.required_roles and "y" not in fm and rec.get("y_label"):
            fm["y"] = rec.get("y_label")

        # 只允许注册表角色
        allowed_roles = set(chart.required_roles + (chart.optional_roles or []))
        fm = {k: v for k, v in fm.items() if k in allowed_roles and isinstance(v, str) and v.strip()}

        # 必填角色必须齐全
        missing = [r for r in chart.required_roles if r not in fm]
        if missing:
            logger.warning(f"[INVALID] chart_id={chart_id} missing required roles: {missing}")
            continue

        # columns_to_keep
        columns_to_keep = rec.get("columns_to_keep", [])
        if not isinstance(columns_to_keep, list):
            columns_to_keep = []
        columns_to_keep = [c for c in columns_to_keep if c in col_set]

        # 自动吸收 mapping 中是"真实列名"的值
        mapped_cols = [v for v in fm.values() if v in col_set]
        columns_to_keep = list(dict.fromkeys(columns_to_keep + mapped_cols))

        item = {
            "chart_id": chart_id,
            "name": chart.name,
            "name_zh": chart.name,
            "name_en": chart_id,
            "display_name": f"{chart_id} | {chart.name}",
            "stars": stars,
            "reason": str(rec.get("reason", "")),
            "required_fields": chart.required_roles,
            "field_mapping": fm,
            # 为前端兼容保留xy（仅xy图有意义）
            "x_label": fm.get("x", rec.get("x_label", "")),
            "y_label": fm.get("y", rec.get("y_label", "")),
            "columns_to_keep": columns_to_keep,
            "data_processing": rec.get("data_processing", "无需特殊处理")
        }
        cleaned.append(item)

    return cleaned


def analyze_data_with_llm(
        df,
        query: str = "",
        provider: str = "deepseek",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
) -> Dict[str, Any]:
    """使用 LLM 分析数据并推荐图表"""
    logger.info("=== analyze_data_with_llm called ===")
    logger.info(f"Provider: {provider}")

    try:
        if df is None or df.empty:
            return {"success": False, "error": "No data"}

        logger.info(f"Data shape: {df.shape[0]} rows x {df.shape[1]} columns")
        
        # 统一把列名转成字符串，避免 join 报错，也避免后续校验列名匹配失败
        df = df.copy()
        df.columns = df.columns.map(str)
       
        # 数据分析
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        string_cols = df.select_dtypes(include=['object']).columns.tolist()
        logger.info(f"Column types: {len(numeric_cols)} numeric, {len(string_cols)} string, 0 datetime")

        # 构建 prompt
        charts_def = build_charts_definition()
        
        prompt = f"""你是数据可视化专家。根据以下数据特征，推荐最合适的图表。

数据特征：
- 总行数：{df.shape[0]}
- 总列数：{df.shape[1]}
- 数值列（{len(numeric_cols)}）：{', '.join(numeric_cols[:10])}{'...' if len(numeric_cols) > 10 else ''}
- 文本列（{len(string_cols)}）：{', '.join(string_cols[:10])}{'...' if len(string_cols) > 10 else ''}

用户查询：{query or '请推荐最合适的图表'}

{charts_def}

请返回 JSON 数组，每个推荐包含：
{{
  "chart_id": "图表ID",
  "stars": "五星推荐/四星推荐/三星推荐/二星推荐/一星推荐",
  "reason": "推荐理由",
  "field_mapping": {{"role1": "列名1", "role2": "列名2", ...}},
  "columns_to_keep": ["需要保留的列"],
  "data_processing": "数据处理建议"
}}

注意：
1. field_mapping 必须包含所有 required_fields
2. 列名必须是数据中真实存在的列
3. 只推荐注册表中存在的图表
4. 最多推荐 5 个图表
"""

        logger.info("Calling LLM...")
        from llm_config_manager import get_config_manager, get_llm_client
        
        manager = get_config_manager()
        config = manager.get_config(provider)
        
        if not config:
            return {"success": False, "error": f"Provider '{provider}' not configured"}
        
        client = get_llm_client(provider)
        
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        
        llm_response = response.choices[0].message.content
        logger.info(f"LLM response received: {len(llm_response)} characters")
        
        # 解析 JSON
        recommendations = extract_and_parse_json(llm_response)
        if not recommendations:
            logger.warning("Failed to extract recommendations from LLM response")
            recommendations = []
        
        logger.info(f"Extracted {len(recommendations)} recommendations from JSON")
        
        # 清洗和验证
        validated = sanitize_and_validate_recommendations(recommendations, df.columns.tolist())
        logger.info(f"Validated recommendations: {[r['chart_id'] for r in validated]}")
        
        return {
            "success": True,
            "analysis": {
                "summary": f"分析完成：{df.shape[0]} 行 × {df.shape[1]} 列数据，推荐 {len(validated)} 个图表"
            },
            "recommendations": validated
        }

    except Exception as e:
        logger.error(f"analyze_data_with_llm error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
