"""
合约权限分析器测试
"""

import pytest
from unittest.mock import Mock, patch
from web3 import Web3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.scoring.contract_permission import ContractPermissionAnalyzer
from src.blockchain.web3_client import Web3Client


class TestContractPermissionAnalyzer:
    """测试合约权限分析器"""

    @pytest.fixture
    def mock_client(self):
        """创建模拟的 Web3 客户端"""
        client = Mock(spec=Web3Client)
        client.w3 = Mock()
        client.w3.eth = Mock()
        return client

    @pytest.fixture
    def analyzer(self, mock_client):
        """创建分析器实例"""
        return ContractPermissionAnalyzer(mock_client, use_cache=False)

    def test_check_owner_renounced(self, analyzer, mock_client):
        """测试检测已放弃 owner 权限的合约"""
        # 模拟合约返回零地址
        mock_contract = Mock()
        mock_contract.functions.owner.return_value.call.return_value = (
            "0x0000000000000000000000000000000000000000"
        )
        mock_client.w3.eth.contract.return_value = mock_contract

        result = analyzer.check_owner("0x1234567890123456789012345678901234567890")

        assert result["has_owner"] is True
        assert result["is_renounced"] is True
        assert result["owner_address"] == "0x0000000000000000000000000000000000000000"

    def test_check_owner_active(self, analyzer, mock_client):
        """测试检测有活跃 owner 的合约"""
        owner_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"

        mock_contract = Mock()
        mock_contract.functions.owner.return_value.call.return_value = owner_address
        mock_client.w3.eth.contract.return_value = mock_contract
        mock_client.is_contract.return_value = False

        result = analyzer.check_owner("0x1234567890123456789012345678901234567890")

        assert result["has_owner"] is True
        assert result["is_renounced"] is False
        assert result["owner_address"] == owner_address
        assert result["is_multisig"] is False

    def test_check_owner_multisig(self, analyzer, mock_client):
        """测试检测多签 owner"""
        owner_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"

        mock_contract = Mock()
        mock_contract.functions.owner.return_value.call.return_value = owner_address
        mock_client.w3.eth.contract.return_value = mock_contract
        mock_client.is_contract.return_value = True  # owner 是合约

        result = analyzer.check_owner("0x1234567890123456789012345678901234567890")

        assert result["has_owner"] is True
        assert result["is_multisig"] is True

    def test_check_owner_no_owner_function(self, analyzer, mock_client):
        """测试没有 owner 函数的合约"""
        mock_contract = Mock()
        mock_contract.functions.owner.return_value.call.side_effect = Exception("No owner")
        mock_client.w3.eth.contract.return_value = mock_contract

        result = analyzer.check_owner("0x1234567890123456789012345678901234567890")

        assert result["has_owner"] is False
        assert result["owner_address"] is None

    def test_check_dangerous_functions_found(self, analyzer, mock_client):
        """测试检测到危险函数"""
        # 模拟包含 mint 函数的字节码
        # mint(address,uint256) 的选择器是 0x40c10f19
        bytecode = "0x608060405234801561001040c10f1956"  # 包含 mint 选择器

        mock_client.w3.eth.get_code.return_value.hex.return_value = bytecode

        result = analyzer.check_dangerous_functions("0x1234567890123456789012345678901234567890")

        assert result["has_dangerous_functions"] is True
        assert len(result["dangerous_functions"]) > 0
        assert "mint" in result["risk_categories"]

    def test_check_dangerous_functions_none(self, analyzer, mock_client):
        """测试没有危险函数的合约"""
        # 模拟不包含危险函数的字节码
        bytecode = "0x6080604052348015610010576000"

        mock_client.w3.eth.get_code.return_value.hex.return_value = bytecode

        result = analyzer.check_dangerous_functions("0x1234567890123456789012345678901234567890")

        assert result["has_dangerous_functions"] is False
        assert len(result["dangerous_functions"]) == 0

    def test_check_proxy_pattern_not_proxy(self, analyzer, mock_client):
        """测试非代理合约"""
        # 模拟空存储槽
        mock_client.w3.eth.get_storage_at.return_value = b'\x00' * 32

        result = analyzer.check_proxy_pattern("0x1234567890123456789012345678901234567890")

        assert result["is_proxy"] is False
        assert result["implementation"] is None

    def test_check_proxy_pattern_is_proxy(self, analyzer, mock_client):
        """测试代理合约"""
        # 模拟实现地址在存储槽中
        impl_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        impl_bytes = bytes.fromhex(impl_address[2:].zfill(64))

        mock_client.w3.eth.get_storage_at.side_effect = [
            impl_bytes,  # 实现槽位
            b'\x00' * 32  # 管理员槽位
        ]

        result = analyzer.check_proxy_pattern("0x1234567890123456789012345678901234567890")

        assert result["is_proxy"] is True
        assert result["implementation"] is not None

    def test_calculate_risk_score_safe_contract(self, analyzer):
        """测试安全合约的评分"""
        owner_info = {
            "has_owner": True,
            "is_renounced": True,
            "is_multisig": False
        }
        dangerous_functions = {
            "has_dangerous_functions": False,
            "dangerous_functions": []
        }
        proxy_info = {
            "is_proxy": False
        }

        score, risk_level, risk_summary = analyzer._calculate_risk_score(
            owner_info,
            dangerous_functions,
            proxy_info
        )

        assert score == 30  # 满分
        assert risk_level == "low_risk"

    def test_calculate_risk_score_risky_contract(self, analyzer):
        """测试高风险合约的评分"""
        owner_info = {
            "has_owner": True,
            "is_renounced": False,
            "is_multisig": False
        }
        dangerous_functions = {
            "has_dangerous_functions": True,
            "dangerous_functions": [
                {"category": "mint", "signature": "mint(address,uint256)"},
                {"category": "setTax", "signature": "setTaxFee(uint256)"},
                {"category": "upgradeTo", "signature": "upgradeTo(address)"}
            ]
        }
        proxy_info = {
            "is_proxy": True,
            "admin": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
        }

        score, risk_level, risk_summary = analyzer._calculate_risk_score(
            owner_info,
            dangerous_functions,
            proxy_info
        )

        assert score == 0  # 最低分
        assert risk_level == "high_risk"

    def test_calculate_risk_score_medium_risk(self, analyzer):
        """测试中等风险合约的评分"""
        owner_info = {
            "has_owner": True,
            "is_renounced": False,
            "is_multisig": True  # 多签降低风险
        }
        dangerous_functions = {
            "has_dangerous_functions": True,
            "dangerous_functions": [
                {"category": "mint", "signature": "mint(address,uint256)"}
            ]
        }
        proxy_info = {
            "is_proxy": False
        }

        score, risk_level, risk_summary = analyzer._calculate_risk_score(
            owner_info,
            dangerous_functions,
            proxy_info
        )

        assert 15 <= score <= 25
        assert risk_level in ["medium_risk", "low_risk"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
