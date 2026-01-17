# -*- coding: utf-8 -*-
"""
Monad Contract Analyzer HTTP API Server

提供 HTTP 接口用于分析合约交互形态

API 使用方法:
    POST /api/analyze
    Headers: X-API-Key: your_api_key_here
    Body: {"contract_address": "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A"}
"""

from flask import Flask, request, jsonify
from functools import wraps
import os
import sys

# 设置编码
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from src.analyzers.interaction_shape import analyze_interaction_shape, generate_profile_report
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 从环境变量读取 API Key
API_KEY = os.getenv("API_KEY", "")

if not API_KEY:
    print("⚠️  WARNING: API_KEY not set in .env file!")
    print("⚠️  Please add API_KEY=your_secret_key to .env")


def require_api_key(f):
    """
    API 密钥认证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求头获取 API Key
        provided_key = request.headers.get('X-API-Key')

        if not provided_key:
            return jsonify({
                "success": False,
                "error": "Missing API Key",
                "message": "Please provide X-API-Key in request headers"
            }), 401

        if provided_key != API_KEY:
            return jsonify({
                "success": False,
                "error": "Invalid API Key",
                "message": "The provided API key is not valid"
            }), 403

        return f(*args, **kwargs)

    return decorated_function


@app.route('/health', methods=['GET'])
def health():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "service": "Monad Contract Analyzer API"
    })


@app.route('/api/analyze', methods=['POST'])
@require_api_key
def analyze_contract():
    """
    分析合约交互形态

    Request Body:
        {
            "contract_address": "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A",
            "limit": 500,  // 可选，默认 500
            "fetch_all": false  // 可选，默认 false
        }

    Response:
        {
            "success": true,
            "data": {
                "token_address": "0x...",
                "health_score": 75,
                "shape": "CONCENTRATED",
                "risk_level": "MEDIUM",
                ...
            },
            "report": "格式化的报告文本"
        }
    """
    try:
        # 获取请求参数
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid Request",
                "message": "Request body must be JSON"
            }), 400

        contract_address = data.get('contract_address')

        if not contract_address:
            return jsonify({
                "success": False,
                "error": "Missing Parameter",
                "message": "contract_address is required"
            }), 400

        # 验证地址格式
        if not contract_address.startswith('0x') or len(contract_address) != 42:
            return jsonify({
                "success": False,
                "error": "Invalid Address",
                "message": "contract_address must be a valid Ethereum address (0x...)"
            }), 400

        # 获取可选参数
        limit = data.get('limit', 500)
        fetch_all = data.get('fetch_all', False)

        # 执行分析
        print(f"\n[API] Analyzing contract: {contract_address}")
        print(f"[API] Limit: {limit}, Fetch all: {fetch_all}")

        result = analyze_interaction_shape(
            contract_address,
            limit=limit,
            fetch_all=fetch_all
        )

        if not result:
            return jsonify({
                "success": False,
                "error": "Analysis Failed",
                "message": "Failed to analyze contract. Please check the address and try again."
            }), 500

        # 计算健康度评分
        health_score = calculate_health_score(result)

        # 生成报告
        report = generate_profile_report(result)

        # 返回结果
        return jsonify({
            "success": True,
            "data": {
                "token_address": result["token_address"],
                "health_score": health_score,
                "total_addresses": result["total_addresses"],
                "total_interaction_volume": result["total_interaction_volume"],
                "shape": result["shape"],
                "shape_description": result["shape_cn"],
                "risk_level": result["risk_level"],
                "concentration": {
                    "top_1_percent": result["top_1_ratio"],
                    "top_10_percent": result["top_10_percent_ratio"]
                },
                "bot_analysis": {
                    "warning_level": result["bot_warning"],
                    "warning_description": result["bot_warning_cn"],
                    "bot_count_ratio": result["bot_ratio"],
                    "bot_volume_ratio": result["bot_volume_ratio"]
                },
                "address_distribution": {
                    "bot": result["type_distribution"]["bot"]["count"],
                    "dex": result["type_distribution"]["dex"]["count"],
                    "cex": result["type_distribution"]["cex"]["count"],
                    "smart_money": result["type_distribution"]["smart_money"]["count"],
                    "contract": result["type_distribution"]["contract"]["count"],
                    "eoa": result["type_distribution"]["eoa_unlabeled"]["count"]
                },
                "eoa_ratio": result["eoa_ratio"],
                "top_interactors": result["top_interactors"][:5]
            },
            "report": report
        })

    except Exception as e:
        print(f"[API ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "error": "Internal Server Error",
            "message": str(e)
        }), 500


def calculate_health_score(result: dict) -> int:
    """
    计算健康度评分 (0-100)
    与 generate_profile_report 中的逻辑保持一致
    """
    score = 100

    # 集中度扣分
    if result["top_10_percent_ratio"] >= 80:
        score -= 30
    elif result["top_10_percent_ratio"] >= 60:
        score -= 20
    elif result["top_10_percent_ratio"] >= 40:
        score -= 10

    # Bot 活动扣分
    if result["bot_volume_ratio"] >= 50:
        score -= 25
    elif result["bot_volume_ratio"] >= 20:
        score -= 10

    # EOA 比例高是健康信号
    if result["eoa_ratio"] >= 50:
        score += 5

    # Smart Money 参与加分
    ts = result["type_distribution"]
    total_addr = result["total_addresses"]
    smart_money_ratio = (ts["smart_money"]["count"] / total_addr * 100) if total_addr > 0 else 0

    if smart_money_ratio >= 10:
        score += 10
    elif smart_money_ratio >= 5:
        score += 5

    return max(0, min(100, score))


@app.route('/', methods=['GET'])
def index():
    """API 文档"""
    return jsonify({
        "service": "Monad Contract Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "/health": {
                "method": "GET",
                "description": "Health check endpoint",
                "auth_required": False
            },
            "/api/analyze": {
                "method": "POST",
                "description": "Analyze contract interaction shape",
                "auth_required": True,
                "headers": {
                    "X-API-Key": "Your API key"
                },
                "body": {
                    "contract_address": "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A",
                    "limit": 500,
                    "fetch_all": False
                }
            }
        },
        "usage_example": {
            "curl": "curl -X POST http://localhost:5000/api/analyze -H 'Content-Type: application/json' -H 'X-API-Key: your_api_key' -d '{\"contract_address\": \"0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A\"}'"
        }
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print("=" * 60)
    print("  Monad Contract Analyzer API Server")
    print("=" * 60)
    print(f"\n  Server: http://{host}:{port}")
    print(f"  Debug: {debug}")
    print(f"  API Key: {'✓ Set' if API_KEY else '✗ Not Set'}")
    print("\n" + "=" * 60)
    print("\n  API Endpoints:")
    print(f"    GET  /health         - Health check")
    print(f"    GET  /               - API documentation")
    print(f"    POST /api/analyze    - Analyze contract (requires API key)")
    print("\n" + "=" * 60)
    print("\n  Usage Example:")
    print(f"    curl -X POST http://localhost:{port}/api/analyze \\")
    print(f"         -H 'Content-Type: application/json' \\")
    print(f"         -H 'X-API-Key: your_api_key' \\")
    print(f"         -d '{{\"contract_address\": \"0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A\"}}'")
    print("\n" + "=" * 60 + "\n")

    app.run(host=host, port=port, debug=debug)
