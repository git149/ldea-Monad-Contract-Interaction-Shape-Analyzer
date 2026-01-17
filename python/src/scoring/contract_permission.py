"""
合约权限分析模块
检测代币合约是否具有 Rug Pull 能力（权限风险）

评分权重: 30分
核心逻辑: 检测合约是否可以被 owner 滥用（mint、修改税率、升级等）
"""

from typing import Dict, List, Optional, Any
from web3 import Web3
from web3.exceptions import ContractLogicError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.blockchain.web3_client import Web3Client
from src.utils.simple_db import SimpleDB


# 常见的危险函数签名
DANGEROUS_FUNCTIONS = {
    "mint": ["mint(address,uint256)", "mint(uint256)"],
    "burn": ["burn(address,uint256)", "burn(uint256)"],
    "setTax": ["setTaxFee(uint256)", "setTax(uint256)", "setFee(uint256)"],
    "setMaxTx": ["setMaxTxAmount(uint256)", "setMaxTransaction(uint256)"],
    "upgradeTo": ["upgradeTo(address)", "upgradeToAndCall(address,bytes)"],
    "setPause": ["pause()", "unpause()"],
    "blacklist": ["blacklist(address)", "addToBlacklist(address)", "setBlacklist(address,bool)"],
    "setRouter": ["setRouter(address)", "setDexRouter(address)"],
}

# EIP-1967 代理合约的存储槽位
EIP1967_IMPLEMENTATION_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
EIP1967_ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"


class ContractPermissionAnalyzer:
    """合约权限分析器"""

    def __init__(self, client: Web3Client, use_cache: bool = True):
        """
        初始化权限分析器

        Args:
            client: Web3 客户端实例
            use_cache: 是否使用缓存（默认 True）
        """
        self.client = client
        self.cache = SimpleDB() if use_cache else None

    def check_owner(self, contract_address: str) -> Dict[str, Any]:
        """
        检查合约 owner 状态

        Args:
            contract_address: 合约地址

        Returns:
            owner 信息字典，包含：
            - has_owner: 是否有 owner 函数
            - owner_address: owner 地址
            - is_renounced: 是否已放弃 owner 权限
            - is_multisig: 是否是多签地址（简化判断）
        """
        checksum_address = Web3.to_checksum_address(contract_address)

        # 先检查缓存
        if self.cache:
            cache_key = f"owner_{checksum_address.lower()}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        result = {
            "has_owner": False,
            "owner_address": None,
            "is_renounced": False,
            "is_multisig": False
        }

        # 尝试读取 owner
        owner_abi = [{
            "constant": True,
            "inputs": [],
            "name": "owner",
            "outputs": [{"name": "", "type": "address"}],
            "type": "function"
        }]

        try:
            contract = self.client.w3.eth.contract(
                address=checksum_address,
                abi=owner_abi
            )
            owner_address = contract.functions.owner().call()

            result["has_owner"] = True
            result["owner_address"] = owner_address

            # 判断是否已放弃权限（地址为 0x0）
            zero_address = "0x0000000000000000000000000000000000000000"
            if owner_address.lower() == zero_address.lower():
                result["is_renounced"] = True
            else:
                # 判断 owner 是否是合约（可能是多签或DAO）
                result["is_multisig"] = self.client.is_contract(owner_address)

        except (ContractLogicError, Exception) as e:
            # 合约没有 owner 函数
            result["has_owner"] = False

        # 缓存结果
        if self.cache:
            self.cache.set(cache_key, result)

        return result

    def check_dangerous_functions(self, contract_address: str) -> Dict[str, Any]:
        """
        检查合约中是否存在危险函数

        Args:
            contract_address: 合约地址

        Returns:
            危险函数检测结果，包含：
            - has_dangerous_functions: 是否有危险函数
            - dangerous_functions: 检测到的危险函数列表
            - risk_categories: 风险类别
        """
        checksum_address = Web3.to_checksum_address(contract_address)

        # 获取合约字节码
        bytecode = self.client.w3.eth.get_code(checksum_address).hex()

        if bytecode == "0x":
            return {
                "has_dangerous_functions": False,
                "dangerous_functions": [],
                "risk_categories": []
            }

        # 检测函数签名
        detected_functions = []
        risk_categories = set()

        for category, function_sigs in DANGEROUS_FUNCTIONS.items():
            for func_sig in function_sigs:
                # 计算函数选择器（前4字节）
                selector = Web3.keccak(text=func_sig)[:4].hex()

                # 在字节码中查找选择器
                if selector[2:] in bytecode:  # 去掉 '0x' 前缀
                    detected_functions.append({
                        "category": category,
                        "signature": func_sig,
                        "selector": selector
                    })
                    risk_categories.add(category)

        return {
            "has_dangerous_functions": len(detected_functions) > 0,
            "dangerous_functions": detected_functions,
            "risk_categories": list(risk_categories)
        }

    def check_proxy_pattern(self, contract_address: str) -> Dict[str, Any]:
        """
        检查是否是代理合约（EIP-1967）

        Args:
            contract_address: 合约地址

        Returns:
            代理合约信息，包含：
            - is_proxy: 是否是代理合约
            - implementation: 实现合约地址
            - admin: 管理员地址
        """
        checksum_address = Web3.to_checksum_address(contract_address)

        result = {
            "is_proxy": False,
            "implementation": None,
            "admin": None
        }

        try:
            # 读取 EIP-1967 实现槽位
            impl_slot = self.client.w3.eth.get_storage_at(
                checksum_address,
                EIP1967_IMPLEMENTATION_SLOT
            )

            # 如果槽位不为空，说明是代理合约
            if impl_slot != b'\x00' * 32:
                result["is_proxy"] = True
                # 提取地址（最后20字节）
                result["implementation"] = Web3.to_checksum_address(
                    "0x" + impl_slot[-20:].hex()
                )

            # 读取管理员槽位
            admin_slot = self.client.w3.eth.get_storage_at(
                checksum_address,
                EIP1967_ADMIN_SLOT
            )

            if admin_slot != b'\x00' * 32:
                result["admin"] = Web3.to_checksum_address(
                    "0x" + admin_slot[-20:].hex()
                )

        except Exception as e:
            print(f"Error checking proxy pattern: {e}")

        return result

    def analyze_contract(self, contract_address: str) -> Dict[str, Any]:
        """
        全面分析合约权限风险

        Args:
            contract_address: 合约地址

        Returns:
            完整的权限分析结果，包含：
            - owner_info: owner 信息
            - dangerous_functions: 危险函数信息
            - proxy_info: 代理合约信息
            - risk_score: 风险评分（0-30）
            - risk_level: 风险等级
            - risk_summary: 风险摘要
        """
        print(f"Analyzing contract permissions: {contract_address}")

        # 1. 检查 owner
        print("  [1/3] Checking owner...")
        owner_info = self.check_owner(contract_address)

        # 2. 检查危险函数
        print("  [2/3] Checking dangerous functions...")
        dangerous_functions = self.check_dangerous_functions(contract_address)

        # 3. 检查代理模式
        print("  [3/3] Checking proxy pattern...")
        proxy_info = self.check_proxy_pattern(contract_address)

        # 计算风险评分
        score, risk_level, risk_summary = self._calculate_risk_score(
            owner_info,
            dangerous_functions,
            proxy_info
        )

        return {
            "contract_address": contract_address,
            "owner_info": owner_info,
            "dangerous_functions": dangerous_functions,
            "proxy_info": proxy_info,
            "score": score,
            "risk_level": risk_level,
            "risk_summary": risk_summary
        }

    def _calculate_risk_score(
        self,
        owner_info: Dict,
        dangerous_functions: Dict,
        proxy_info: Dict
    ) -> tuple:
        """
        计算权限风险评分

        评分标准（30分满分）:
        1. Owner 已放弃 (20分)
        2. 无危险函数 (10分)
        3. 额外加分项:
           - 非代理合约 (+5分，最多30)
           - Owner 是多签 (+5分，最多30)

        Args:
            owner_info: owner 信息
            dangerous_functions: 危险函数信息
            proxy_info: 代理合约信息

        Returns:
            (score, risk_level, risk_summary) 元组
        """
        score = 0
        risk_factors = []

        # 1. Owner 检查（20分）
        if not owner_info["has_owner"]:
            score += 20
            risk_factors.append("[OK] No owner function")
        elif owner_info["is_renounced"]:
            score += 20
            risk_factors.append("[OK] Owner renounced")
        elif owner_info["is_multisig"]:
            score += 15
            risk_factors.append("[!] Owner is multisig/DAO")
        else:
            score += 0
            risk_factors.append("[X] Owner still has control")

        # 2. 危险函数检查（10分）
        if not dangerous_functions["has_dangerous_functions"]:
            score += 10
            risk_factors.append("[OK] No dangerous functions")
        else:
            dangerous_count = len(dangerous_functions["dangerous_functions"])
            if dangerous_count <= 2:
                score += 5
                risk_factors.append(f"[!] {dangerous_count} dangerous functions found")
            else:
                score += 0
                risk_factors.append(f"[X] {dangerous_count} dangerous functions found")

        # 3. 代理合约检查（额外风险）
        if proxy_info["is_proxy"]:
            if proxy_info["admin"]:
                zero_address = "0x0000000000000000000000000000000000000000"
                if proxy_info["admin"].lower() == zero_address.lower():
                    risk_factors.append("[OK] Proxy admin renounced")
                else:
                    score = max(0, score - 5)  # 扣5分
                    risk_factors.append("[X] Upgradeable proxy with admin")
        else:
            risk_factors.append("[OK] Not a proxy contract")

        # 限制最高分
        score = min(30, score)

        # 确定风险等级
        if score >= 25:
            risk_level = "low_risk"
        elif score >= 15:
            risk_level = "medium_risk"
        else:
            risk_level = "high_risk"

        return score, risk_level, risk_factors


# 使用示例
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # 创建 Web3 客户端
    client = Web3Client(network="monad_testnet")

    # 创建权限分析器
    analyzer = ContractPermissionAnalyzer(client)

    # 测试分析（替换为真实的代币地址）
    test_token = "0xdf5b718d8fcc173335185a2a1513ee8151e3c027"

    print(f"Analyzing token: {test_token}\n")

    # 执行分析
    result = analyzer.analyze_contract(test_token)

    print("\n=== Analysis Result ===")
    print(f"\nOwner Info:")
    print(f"  Has Owner: {result['owner_info']['has_owner']}")
    print(f"  Owner Address: {result['owner_info']['owner_address']}")
    print(f"  Is Renounced: {result['owner_info']['is_renounced']}")
    print(f"  Is Multisig: {result['owner_info']['is_multisig']}")

    print(f"\nDangerous Functions:")
    print(f"  Has Dangerous: {result['dangerous_functions']['has_dangerous_functions']}")
    if result['dangerous_functions']['dangerous_functions']:
        print(f"  Found Functions:")
        for func in result['dangerous_functions']['dangerous_functions']:
            print(f"    - {func['category']}: {func['signature']}")

    print(f"\nProxy Info:")
    print(f"  Is Proxy: {result['proxy_info']['is_proxy']}")
    print(f"  Implementation: {result['proxy_info']['implementation']}")
    print(f"  Admin: {result['proxy_info']['admin']}")

    print(f"\nRisk Assessment:")
    print(f"  Score: {result['score']}/30")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"\nRisk Summary:")
    for factor in result['risk_summary']:
        print(f"  {factor}")
