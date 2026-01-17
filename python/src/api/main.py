# -*- coding: utf-8 -*-
"""
评分系统 API
提供代币评分查询接口，供前端调用
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.blockchain.web3_client import Web3Client
from src.blockchain.nansen_client import NansenClient
from src.blockchain.score_registry import ScoreRegistry
from src.scoring.total_scorer import TotalScorer

# 创建 FastAPI 应用
app = FastAPI(
    title="Token Score API",
    description="代币风险评分系统 API (Nansen)",
    version="1.1.0"
)

# CORS 配置 - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局客户端实例
client: Optional[Web3Client] = None
nansen: Optional[NansenClient] = None
scorer: Optional[TotalScorer] = None
registry: Optional[ScoreRegistry] = None


def get_client() -> Optional[Web3Client]:
    """获取 Web3 客户端（懒加载，可能失败）"""
    global client
    if client is None:
        try:
            client = Web3Client(network="monad_mainnet")
        except Exception as e:
            print(f"[!] Web3 client init failed: {e}")
            return None
    return client


def get_nansen() -> Optional[NansenClient]:
    """获取 Nansen 客户端（懒加载，可能失败）"""
    global nansen
    if nansen is None:
        try:
            nansen = NansenClient()
        except Exception as e:
            print(f"[!] Nansen init failed: {e}")
            return None
    return nansen


def get_scorer() -> TotalScorer:
    """获取评分器（懒加载，支持 Nansen）"""
    global scorer
    if scorer is None:
        scorer = TotalScorer(get_client(), nansen=get_nansen())
    return scorer


def get_registry() -> ScoreRegistry:
    """获取合约实例（懒加载）"""
    global registry
    if registry is None:
        registry = ScoreRegistry(get_client())
    return registry


# ============ 请求/响应模型 ============

class ScoreRequest(BaseModel):
    """评分请求"""
    token_address: str
    time_window_hours: int = 1
    mode: str = "auto"  # auto, fast, deep


class OnChainScoreResponse(BaseModel):
    """链上评分响应"""
    total_score: int
    eoa_score: int
    holder_score: int
    permission_score: int
    risk_level: int
    risk_level_str: str
    timestamp: int
    block_number: int
    scorer: str
    has_score: bool


# ============ API 路由 ============

@app.get("/")
async def root():
    """健康检查"""
    return {
        "status": "ok",
        "service": "Token Score API",
        "version": "1.0.0"
    }


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    try:
        c = get_client()
        r = get_registry()
        ns = get_nansen()

        result = {
            "nansen_available": ns is not None,
            "recommended_mode": "fast" if ns else "deep"
        }

        # Web3 连接可能失败
        if c:
            result.update({
                "connected": c.is_connected(),
                "chain_id": c.get_chain_id(),
                "block_number": c.get_block_number(),
                "contract_address": r.contract_address if r else None,
                "total_scored_projects": r.get_scored_project_count() if r else 0,
                "total_score_count": r.get_total_score_count() if r else 0,
            })
        else:
            result.update({
                "connected": False,
                "chain_id": None,
                "block_number": None,
                "contract_address": None,
                "total_scored_projects": 0,
                "total_score_count": 0,
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_token(request: ScoreRequest):
    """
    分析代币并返回评分数据

    前端拿到数据后，用户可以选择提交到链上

    参数:
    - token_address: 代币合约地址
    - time_window_hours: EOA 分析时间窗口 (默认 1 小时)
    - mode: 分析模式 (auto/fast/deep)
    """
    try:
        s = get_scorer()
        result = s.score_token(
            token_address=request.token_address,
            mode=request.mode,
            time_window_hours=request.time_window_hours
        )

        # 添加链上提交所需的数据格式
        result["submit_data"] = {
            "target": request.token_address,
            "totalScore": int(result["overview"]["total_score"]),
            "eoaScore": int(result["scores"]["eoa"]["score"]),
            "holderScore": int(result["scores"]["holder"]["score"]),
            "permissionScore": int(result["scores"]["permission"]["score"]),
            "riskLevel": _risk_level_to_int(result["overview"]["risk_level"])
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/score/{token_address}")
async def get_onchain_score(token_address: str):
    """
    查询链上已有的评分
    """
    try:
        r = get_registry()

        # 检查是否已评分
        has_score = r.has_been_scored(token_address)

        if not has_score:
            return OnChainScoreResponse(
                total_score=0,
                eoa_score=0,
                holder_score=0,
                permission_score=0,
                risk_level=0,
                risk_level_str="NOT_SCORED",
                timestamp=0,
                block_number=0,
                scorer="0x0000000000000000000000000000000000000000",
                has_score=False
            )

        # 获取链上评分
        score = r.get_latest_score(token_address)

        return OnChainScoreResponse(
            total_score=score["total_score"],
            eoa_score=score["eoa_score"],
            holder_score=score["holder_score"],
            permission_score=score["permission_score"],
            risk_level=score["risk_level"],
            risk_level_str=score["risk_level_str"],
            timestamp=score["timestamp"],
            block_number=score["block_number"],
            scorer=score["scorer"],
            has_score=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contract-info")
async def get_contract_info():
    """获取合约信息（供前端连接使用）"""
    from src.blockchain.score_registry import SCORE_REGISTRY_ABI

    r = get_registry()
    return {
        "address": r.contract_address,
        "abi": SCORE_REGISTRY_ABI,
        "chain_id": get_client().get_chain_id(),
        "network": "monad_mainnet"
    }


def _risk_level_to_int(risk_level: str) -> int:
    """将风险等级字符串转为整数"""
    mapping = {
        "low_risk": 0,
        "medium_risk": 1,
        "high_risk": 2,
        "extreme_risk": 3
    }
    return mapping.get(risk_level, 1)


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
