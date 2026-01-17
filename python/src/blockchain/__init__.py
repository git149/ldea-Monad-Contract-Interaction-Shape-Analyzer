
"""
区块链交互模块

包含:
- Web3Client: 标准 Web3 RPC 客户端 (BlockPi)
- ContractReader: ERC20 合约读取器
- ScoreRegistry: 链上评分注册合约交互
- BlockvisionClient: Blockvision 增强 API 客户端 (持有者/转账查询)
"""

from .web3_client import Web3Client
from .contract_reader import ContractReader
from .score_registry import ScoreRegistry
from .blockvision_client import (
    BlockvisionClient,
    BlockvisionError,
    BlockvisionAPIError,
    BlockvisionNetworkError,
    BlockvisionRateLimitError,
    TokenHolder,
    TokenTransfer,
)

__all__ = [
    # 标准 RPC (BlockPi)
    "Web3Client",
    "ContractReader",
    "ScoreRegistry",
    # Blockvision 增强 API
    "BlockvisionClient",
    "BlockvisionError",
    "BlockvisionAPIError",
    "BlockvisionNetworkError",
    "BlockvisionRateLimitError",
    "TokenHolder",
    "TokenTransfer",
]
