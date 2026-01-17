# -*- coding: utf-8 -*-
"""
合约工具函数
提供合约相关的实用功能
"""

from typing import Optional, Tuple
from web3 import Web3


def get_contract_creation_block(
    w3: Web3,
    contract_address: str,
    max_search_range: int = 10000000
) -> Optional[int]:
    """
    查找合约创建区块（二分查找）

    Args:
        w3: Web3 实例
        contract_address: 合约地址
        max_search_range: 最大搜索范围

    Returns:
        合约创建区块号，找不到返回 None
    """
    address = Web3.to_checksum_address(contract_address)
    latest_block = w3.eth.block_number

    # 先确认当前区块有代码
    current_code = w3.eth.get_code(address, block_identifier=latest_block)
    if current_code == b'' or current_code.hex() == '0x':
        print(f"  [!] Address {address} is not a contract")
        return None

    # 二分查找合约创建区块
    left = max(0, latest_block - max_search_range)
    right = latest_block
    creation_block = None

    print(f"  Searching contract creation block...")
    print(f"  Search range: {left} -> {right}")

    while left <= right:
        mid = (left + right) // 2

        try:
            code = w3.eth.get_code(address, block_identifier=mid)
            has_code = code != b'' and code.hex() != '0x'

            if has_code:
                # 合约在 mid 区块存在，继续向前搜索
                creation_block = mid
                right = mid - 1
            else:
                # 合约在 mid 区块不存在，向后搜索
                left = mid + 1
        except Exception as e:
            # 某些 RPC 可能不支持历史状态查询
            print(f"  [!] Error at block {mid}: {e}")
            left = mid + 1

    if creation_block:
        print(f"  Contract created at block: {creation_block}")
    else:
        print(f"  [!] Could not find creation block, using fallback")

    return creation_block


def estimate_blocks_per_hour(w3: Web3, sample_blocks: int = 100) -> float:
    """
    估算每小时的区块数量

    Args:
        w3: Web3 实例
        sample_blocks: 采样区块数

    Returns:
        每小时区块数
    """
    latest = w3.eth.block_number

    try:
        latest_block = w3.eth.get_block(latest)
        earlier_block = w3.eth.get_block(latest - sample_blocks)

        time_diff = latest_block['timestamp'] - earlier_block['timestamp']
        if time_diff <= 0:
            return 3600  # 默认每秒 1 块

        blocks_per_second = sample_blocks / time_diff
        blocks_per_hour = blocks_per_second * 3600

        print(f"  Estimated blocks per hour: {blocks_per_hour:.0f}")
        return blocks_per_hour
    except Exception as e:
        print(f"  [!] Error estimating block rate: {e}")
        return 3600  # 默认值


def get_smart_block_range(
    w3: Web3,
    contract_address: str,
    hours_back: int = 24,
    full_history: bool = False
) -> Tuple[int, int]:
    """
    智能获取区块范围

    Args:
        w3: Web3 实例
        contract_address: 合约地址
        hours_back: 回溯小时数（仅 full_history=False 时有效）
        full_history: 是否获取全部历史

    Returns:
        (from_block, to_block)
    """
    latest_block = w3.eth.block_number

    if full_history:
        # 全量历史：从合约创建开始
        creation_block = get_contract_creation_block(w3, contract_address)
        from_block = creation_block if creation_block else 0
    else:
        # 时间窗口：只看最近 N 小时
        blocks_per_hour = estimate_blocks_per_hour(w3)
        blocks_back = int(blocks_per_hour * hours_back)
        from_block = max(0, latest_block - blocks_back)

    return from_block, latest_block


# 测试
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from blockchain.web3_client import Web3Client

    client = Web3Client(network="monad_mainnet")

    # 测试查找合约创建区块
    test_token = "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A"

    creation = get_contract_creation_block(client.w3, test_token)
    print(f"\nCreation block: {creation}")

    # 测试智能区块范围
    from_block, to_block = get_smart_block_range(
        client.w3, test_token, full_history=True
    )
    print(f"Smart range (full): {from_block} -> {to_block}")

    from_block, to_block = get_smart_block_range(
        client.w3, test_token, hours_back=24, full_history=False
    )
    print(f"Smart range (24h): {from_block} -> {to_block}")
