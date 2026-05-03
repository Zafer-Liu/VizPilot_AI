#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import pandas as pd
from pathlib import Path
import sys
from charts.registry import list_charts
import os
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHART_PROJECT = Path(__file__).parent
sys.path.insert(0, str(CHART_PROJECT))
sys.path.insert(0, str(CHART_PROJECT / "LLM"))
import llm_config_manager as lcm

try:
    from chart_generate import generate_chart
    from llm_recommender import analyze_data_with_llm
    from llm_config_manager import LLMConfigManager
    from charts.registry import REGISTRY
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.template_folder = str(CHART_PROJECT / 'templates')

UPLOAD_FOLDER = CHART_PROJECT / "uploads"
OUTPUT_FOLDER = CHART_PROJECT / "outputs"
CHART_MAPPING_FILE = CHART_PROJECT / "chart_mapping.json"
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

llm_manager = LLMConfigManager()

# 加载或初始化图表映射（记录每个 chart_id 最后生成的文件）
def load_chart_mapping():
    if CHART_MAPPING_FILE.exists():
        try:
            with open(CHART_MAPPING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_chart_mapping(mapping):
    with open(CHART_MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

chart_mapping = load_chart_mapping()

def get_all_charts():
    """从 registry.py 获取所有图表元数据"""
    return [
        {
            "chart_id": c.chart_id,
            "name": c.name,
            "category": c.category,
            "desc": c.desc,
            "data_format": c.data_format
        }
        for c in list_charts()
    ]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/charts')
def get_charts():
    try:
        charts = get_all_charts()
        return jsonify({"charts": charts})
    except Exception as e:
        logger.error(f"Get charts error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        logger.info("Upload request received")
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file"}), 400
        
        filename = file.filename
        filepath = UPLOAD_FOLDER / filename
        file.save(str(filepath))
        logger.info(f"File saved: {filepath}")
        
        try:
            if filename.endswith('.xlsx'):
                df = pd.read_excel(filepath, engine='openpyxl')
            else:
                df = pd.read_csv(filepath)
        except Exception as e:
            logger.warning(f"Read failed: {e}, trying fallback")
            if 'openpyxl' in str(e) or 'NoneType' in str(e):
                try:
                    df = pd.read_excel(filepath, engine='xlrd')
                except:
                    df = pd.read_excel(filepath)
            else:
                raise
        
        logger.info(f"File read: {len(df)} rows, {len(df.columns)} columns")
        return jsonify({
            "success": True,
            "filepath": str(filepath),
            "rows": len(df),
            "columns": list(df.columns)
        })
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        filepath = data.get('filepath')
        query = data.get('query', '')
        provider = data.get('provider', 'deepseek')
        
        logger.info(f"Analyze: {filepath}, provider={provider}")
        
        if not Path(filepath).exists():
            return jsonify({"error": f"File not found: {filepath}"}), 400
        
        try:
            if filepath.endswith('.xlsx'):
                df = pd.read_excel(filepath, engine='openpyxl')
            else:
                df = pd.read_csv(filepath)
        except Exception as e:
            if 'openpyxl' in str(e) or 'NoneType' in str(e):
                try:
                    df = pd.read_excel(filepath, engine='xlrd')
                except:
                    df = pd.read_excel(filepath)
            else:
                raise
        
        config = llm_manager.get_config(provider)
        if config:
            analysis = analyze_data_with_llm(df, query, provider=config.provider, api_key=config.api_key, base_url=config.base_url, model=config.model)
        else:
            analysis = analyze_data_with_llm(df, query)
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "recommendations": analysis.get('recommendations', [])
        })
    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        return jsonify({"error": str(e), "analysis": {"summary": "Analysis failed"}, "recommendations": []}), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        filepath = data.get('filepath')
        chart_type = data.get('chart_type')
        
        logger.info(f"Generate request: chart_type={chart_type}, filepath={filepath}")
        
        if not chart_type:
            logger.error("chart_type is empty")
            return jsonify({"error": "chart_type is required"}), 400
        
        if filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath, engine='openpyxl')
        else:
            df = pd.read_csv(filepath)
        
        logger.info(f"Calling generate_chart with chart_type={chart_type}")
        result = generate_chart(df, chart_type=chart_type)
        logger.info(f"generate_chart returned: {result}")
        
        if isinstance(result, dict):
            if result.get('success'):
                output_file = OUTPUT_FOLDER / f"{chart_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result.get('html', '<html><body>Chart generated</body></html>'))
                logger.info(f"Chart saved to {output_file}")
                
                # 记录映射：chart_id -> 最新生成的文件路径
                chart_mapping[chart_type] = str(output_file)
                save_chart_mapping(chart_mapping)
                logger.info(f"Updated chart mapping: {chart_type} -> {output_file}")
                
                return jsonify({"success": True, "download_url": f"/api/download/{output_file.name}"})
            else:
                logger.error(f"Chart generation failed: {result}")
                return jsonify({"error": result.get('error', 'Unknown error')}), 400
        else:
            logger.error(f"Invalid result type: {type(result)}")
            return jsonify({"error": "Invalid result type"}), 400
    except Exception as e:
        logger.error(f"Generate error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>')
def download(filename):
    try:
        file_path = OUTPUT_FOLDER / filename
        if file_path.exists():
            return send_file(str(file_path), as_attachment=True)
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chart-detail')
def chart_detail_page():
    return render_template('chart-detail.html')

# ==================== LLM 配置管理接口 ====================

@app.route('/api/llm/list', methods=['GET'])
def llm_list():
    """获取所有 LLM 配置列表"""
    try:
        # 建议每次 list 前强制从磁盘重载，避免内存残留
        llm_manager.load_configs(load_from_env=False)

        logger.info(f"[LLM LIST] configs={list(llm_manager.configs.keys())}")
        logger.info(f"[LLM LIST] file={lcm.LLM_CONFIG_FILE.resolve()}")
        logger.info(f"[LLM LIST] manager_module={lcm.__file__}")

        configs = llm_manager.list_configs()
        default = llm_manager.get_default_provider()
        custom = llm_manager.get_custom_models()

        return jsonify({
            "success": True,
            "configs": configs,
            "default_provider": default,
            "custom_models": custom,
            "config_file": str(lcm.LLM_CONFIG_FILE.resolve()),   # 方便前端也看到真实路径
            "manager_module": lcm.__file__
        })
    except Exception as e:
        logger.error(f"LLM list error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/add-custom', methods=['POST'])
def llm_add_custom():
    """添加自定义 OpenAI SDK 兼容的模型"""
    try:
        data = request.json
        name = data.get('name', '').strip()
        base_url = data.get('base_url', '').strip()
        model_name = data.get('model_name', '').strip()
        api_key = data.get('api_key', '').strip()
        
        if not all([name, base_url, model_name, api_key]):
            return jsonify({
                "success": False,
                "error": "缺少必要参数：name, base_url, model_name, api_key"
            }), 400
        
        success, message = llm_manager.add_custom_model(
            name=name,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key
        )
        
        if success:
            provider_id = f"custom_{name.lower().replace(' ', '_')}"
            return jsonify({
                "success": True,
                "message": message,
                "provider_id": provider_id
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 400
    
    except Exception as e:
        logger.error(f"LLM add custom error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/delete/<provider>', methods=['DELETE'])
def llm_delete(provider):
    """删除自定义模型配置"""
    try:
        success, message = llm_manager.delete_config(provider)
        
        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 400
    
    except Exception as e:
        logger.error(f"LLM delete error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/test/<provider>', methods=['POST'])
def llm_test(provider):
    """测试 LLM 配置是否有效"""
    try:
        result = llm_manager.test_config(provider)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"LLM test error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/config', methods=['POST'])
def llm_config():
    """
    保存 LLM 配置（仅用于内置提供商）
    自定义模型请使用 /api/llm/add-custom
    """
    try:
        data = request.json
        provider = data.get('provider', '').strip()
        api_key = data.get('api_key', '').strip()
        
        if not provider or not api_key:
            return jsonify({
                "success": False,
                "error": "缺少必要参数：provider, api_key"
            }), 400
        
        # 检查是否是自定义模型
        config = llm_manager.get_config(provider)
        if config and config.is_custom:
            return jsonify({
                "success": False,
                "error": f"自定义模型 '{provider}' 不能使用此接口修改，请使用 /api/llm/delete 删除后重新添加"
            }), 400
        
        # 保存内置提供商配置
        success = llm_manager.set_config(
            provider=provider,
            api_key=api_key
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": f"配置已保存: {provider}"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"不支持的提供商: {provider}"
            }), 400
    
    except Exception as e:
        logger.error(f"LLM config error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/llm/clear/<provider>', methods=['POST'])
def llm_clear(provider):
    try:
        success, message = llm_manager.clear_builtin_config(provider)
        if success:
            return jsonify({"success": True, "message": message})
        return jsonify({"success": False, "error": message}), 400
    except Exception as e:
        logger.error(f"LLM clear error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/chart-detail/<chart_id>')
def chart_detail(chart_id):
    try:
        chart_dir = CHART_PROJECT / 'charts' / chart_id
        if not chart_dir.exists():
            return jsonify({"error": "Chart not found"}), 404
        
        # 读取 README
        readme_file = chart_dir / 'README.md'
        readme_content = ""
        if readme_file.exists():
            with open(readme_file, 'r', encoding='utf-8') as f:
                readme_content = f.read()
        
        # 始终返回图表目录下的 result.html（示例文件）
        result_html = ""
        result_file = chart_dir / 'result.html'
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                result_html = f.read()
            logger.info(f"Returning chart example: {result_file}")
        else:
            logger.warning(f"Example file not found: {result_file}")
        
        return jsonify({
            "success": True,
            "chart_id": chart_id,
            "readme": readme_content,
            "example_html": result_html
        })
    except Exception as e:
        logger.error(f"Chart detail error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("Chart Generate Pro")
    print("=" * 60)
    print(f"Server: http://localhost:5017")
    print(f"Upload: {UPLOAD_FOLDER}")
    print(f"Output: {OUTPUT_FOLDER}")
    print("=" * 60)
    print(f"[APP] llm_config_manager module: {lcm.__file__}")
    print(f"[APP] llm config file: {lcm.LLM_CONFIG_FILE.resolve()}")
    app.run(host='0.0.0.0', port=5017, debug=True)
