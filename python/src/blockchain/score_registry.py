"""
ScoreRegistry 合约交互模块
用于向链上提交评分和查询评分数据
"""

import os
from typing import Dict, Optional, Any
from web3 import Web3
from web3.contract import Contract
from dotenv import load_dotenv
from .web3_client import Web3Client


# ScoreRegistry 合约 ABI
SCORE_REGISTRY_ABI = [
    # submitScore - 提交评分
    {
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "totalScore", "type": "uint8"},
            {"name": "eoaScore", "type": "uint8"},
            {"name": "holderScore", "type": "uint8"},
            {"name": "permissionScore", "type": "uint8"},
            {"name": "riskLevel", "type": "uint8"}
        ],
        "name": "submitScore",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # getLatestScore - 获取最新评分
    {
        "inputs": [{"name": "target", "type": "address"}],
        "name": "getLatestScore",
        "outputs": [
            {
                "components": [
                    {"name": "totalScore", "type": "uint8"},
                    {"name": "eoaScore", "type": "uint8"},
                    {"name": "holderScore", "type": "uint8"},
                    {"name": "permissionScore", "type": "uint8"},
                    {"name": "riskLevel", "type": "uint8"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "blockNumber", "type": "uint256"},
                    {"name": "scorer", "type": "address"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # getRiskLevel - 获取风险等级
    {
        "inputs": [{"name": "target", "type": "address"}],
        "name": "getRiskLevel",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    # getScoreCount - 获取评分次数
    {
        "inputs": [{"name": "target", "type": "address"}],
        "name": "getScoreCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # getScoredProjectCount - 获取已评分项目数量
    {
        "inputs": [],
        "name": "getScoredProjectCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # totalScoreCount - 总评分次数
    {
        "inputs": [],
        "name": "totalScoreCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # hasBeenScored - 是否已被评分
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "hasBeenScored",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    # riskLevelToString - 风险等级转字符串
    {
        "inputs": [{"name": "level", "type": "uint8"}],
        "name": "riskLevelToString",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "pure",
        "type": "function"
    },
    # ScoreSubmitted 事件
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "target", "type": "address"},
            {"indexed": False, "name": "totalScore", "type": "uint8"},
            {"indexed": False, "name": "riskLevel", "type": "uint8"},
            {"indexed": False, "name": "timestamp", "type": "uint256"},
            {"indexed": True, "name": "scorer", "type": "address"}
        ],
        "name": "ScoreSubmitted",
        "type": "event"
    }
]

# 风险等级映射
RISK_LEVELS = {
    0: "LOW_RISK",
    1: "MEDIUM_RISK",
    2: "HIGH_RISK",
    3: "EXTREME_RISK"
}


class ScoreRegistry:
    """ScoreRegistry 合约交互类"""

    def __init__(
        self,
        client: Web3Client,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        """
        初始化 ScoreRegistry

        Args:
            client: Web3 客户端实例
            contract_address: 合约地址（不提供则从环境变量读取）
            private_key: 私钥（用于写入操作，不提供则从环境变量读取）
        """
        load_dotenv()

        self.client = client

        # 获取合约地址
        if not contract_address:
            contract_address = os.getenv("SCORE_REGISTRY_ADDRESS")
            if not contract_address:
                raise ValueError("SCORE_REGISTRY_ADDRESS not found in .env")

        self.contract_address = Web3.to_checksum_address(contract_address)

        # 获取私钥（可选，仅写入时需要）
        self.private_key = private_key or os.getenv("PRIVATE_KEY")

        # 创建合约实例
        self.contract: Contract = client.w3.eth.contract(
            address=self.contract_address,
            abi=SCORE_REGISTRY_ABI
        )

    # ============ 读取函数 ============

    def get_latest_score(self, target: str) -> Dict[str, Any]:
        """
        获取项目最新评分

        Args:
            target: 项目地址

        Returns:
            评分数据字典
        """
        target = Web3.to_checksum_address(target)
        result = self.contract.functions.getLatestScore(target).call()

        return {
            "total_score": result[0],
            "eoa_score": result[1],
            "holder_score": result[2],
            "permission_score": result[3],
            "risk_level": result[4],
            "risk_level_str": RISK_LEVELS.get(result[4], "UNKNOWN"),
            "timestamp": result[5],
            "block_number": result[6],
            "scorer": result[7]
        }

    def get_risk_level(self, target: str) -> int:
        """获取项目风险等级"""
        target = Web3.to_checksum_address(target)
        return self.contract.functions.getRiskLevel(target).call()

    def get_score_count(self, target: str) -> int:
        """获取项目评分次数"""
        target = Web3.to_checksum_address(target)
        return self.contract.functions.getScoreCount(target).call()

    def get_scored_project_count(self) -> int:
        """获取已评分项目数量"""
        return self.contract.functions.getScoredProjectCount().call()

    def get_total_score_count(self) -> int:
        """获取总评分次数"""
        return self.contract.functions.totalScoreCount().call()

    def has_been_scored(self, target: str) -> bool:
        """检查项目是否已被评分"""
        target = Web3.to_checksum_address(target)
        return self.contract.functions.hasBeenScored(target).call()

    # ============ 写入函数 ============

    def submit_score(
        self,
        target: str,
        total_score: int,
        eoa_score: int,
        holder_score: int,
        permission_score: int,
        risk_level: int,
        gas_limit: int = 500000
    ) -> Dict[str, Any]:
        """
        提交项目评分

        Args:
            target: 项目地址
            total_score: 总分 (0-100)
            eoa_score: EOA评分 (0-40)
            holder_score: 持有者评分 (0-30)
            permission_score: 权限评分 (0-30)
            risk_level: 风险等级 (0-3)
            gas_limit: Gas 限制

        Returns:
            交易结果
        """
        if not self.private_key:
            raise ValueError("Private key required for write operations")

        # 参数验证
        if not (0 <= total_score <= 100):
            raise ValueError("total_score must be 0-100")
        if not (0 <= eoa_score <= 40):
            raise ValueError("eoa_score must be 0-40")
        if not (0 <= holder_score <= 30):
            raise ValueError("holder_score must be 0-30")
        if not (0 <= permission_score <= 30):
            raise ValueError("permission_score must be 0-30")
        if not (0 <= risk_level <= 3):
            raise ValueError("risk_level must be 0-3")

        target = Web3.to_checksum_address(target)

        # 获取账户信息
        account = self.client.w3.eth.account.from_key(self.private_key)
        nonce = self.client.w3.eth.get_transaction_count(account.address)

        # 构建交易
        tx = self.contract.functions.submitScore(
            target,
            total_score,
            eoa_score,
            holder_score,
            permission_score,
            risk_level
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": self.client.w3.eth.gas_price
        })

        # 签名交易
        signed_tx = self.client.w3.eth.account.sign_transaction(tx, self.private_key)

        # 发送交易
        tx_hash = self.client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # 等待交易确认
        receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "success": receipt["status"] == 1,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "gas_used": receipt["gasUsed"],
            "target": target,
            "total_score": total_score,
            "risk_level": risk_level
        }

    def __repr__(self) -> str:
        return f"ScoreRegistry(address={self.contract_address})"


# 使用示例
if __name__ == "__main__":
    load_dotenv()

    print("=" * 50)
    print("ScoreRegistry 合约交互测试")
    print("=" * 50)

    # 创建客户端（连接 Monad 主网）
    client = Web3Client(network="monad_mainnet")
    print(f"Connected: {client}")
    print(f"Chain ID: {client.get_chain_id()}")
    print(f"Block Number: {client.get_block_number()}")

    # 创建 ScoreRegistry 实例
    registry = ScoreRegistry(client)
    print(f"Registry: {registry}")

    # 查询统计信息
    print("\n--- 链上统计 ---")
    print(f"已评分项目数: {registry.get_scored_project_count()}")
    print(f"总评分次数: {registry.get_total_score_count()}")

    # 测试代币地址
    test_token = os.getenv("TEST_TOKEN_ADDRESS", "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A")
    print(f"\n--- 查询代币: {test_token} ---")
    print(f"是否已评分: {registry.has_been_scored(test_token)}")

    if registry.has_been_scored(test_token):
        score = registry.get_latest_score(test_token)
        print(f"最新评分: {score}")
