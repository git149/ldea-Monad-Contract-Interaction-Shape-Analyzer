# -*- coding: utf-8 -*-
"""
持有者集中度分析模块

分析代币Top10持有者占比,评估抛压风险 (权重30分)

数据源:
- Nansen API (快速模式): 1次API调用直接获取Top持有者 + Smart Money 标签
- BlockPi RPC (深度模式): 从Transfer事件构建完整持有者映射
"""

from typing import Dict, List, Tuple, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.blockchain.web3_client import Web3Client
from src.blockchain.contract_reader import ContractReader
from src.blockchain.nansen_client import NansenClient, NansenError
from src.utils.simple_db import SimpleDB


class HolderAnalyzer:
    """
    持有者集中度分析器

    支持两种数据源:
    - fast: 使用 Nansen API，1次调用获取 Top 持有者 + Smart Money 标签 (推荐)
    - deep: 使用 BlockPi RPC 从 Transfer 事件构建完整映射

    使用示例:
        # 快速模式 (推荐)
        analyzer = HolderAnalyzer(web3_client, nansen_client)
        result = analyzer.analyze(token_address, mode="fast")

        # 深度模式
        result = analyzer.analyze(token_address, mode="deep")
    """

    def __init__(
        self,
        client: Web3Client,
        nansen: Optional[NansenClient] = None,
        use_cache: bool = True
    ):
        """
        初始化持有者分析器

        Args:
            client: Web3客户端实例 (BlockPi RPC)
            nansen: Nansen客户端实例 (可选，用于快速模式)
            use_cache: 是否使用缓存(默认True)
        """
        self.client = client
        self.nansen = nansen
        self.use_cache = use_cache
        self.db = SimpleDB(db_path="data/holder_cache.db", ttl_hours=1)

    def analyze(
        self,
        token_address: str,
        mode: str = "auto",
        from_block: int = 0,
        to_block: int = None
    ) -> Dict:
        """
        分析持有者集中度 (统一入口)

        Args:
            token_address: 代币合约地址
            mode: 分析模式
                - "auto": 自动选择 (有 Blockvision 则用 fast)
                - "fast": 使用 Blockvision API (1次调用)
                - "deep": 使用 BlockPi RPC (完整分析)
            from_block: 起始区块 (仅 deep 模式使用)
            to_block: 结束区块 (仅 deep 模式使用)

        Returns:
            分析结果字典
        """
        # 自动选择模式
        if mode == "auto":
            mode = "fast" if self.nansen else "deep"

        if mode == "fast":
            if not self.nansen:
                raise ValueError("Nansen client required for fast mode")
            return self._analyze_fast(token_address)
        else:
            return self.analyze_holder_concentration(token_address, from_block, to_block)

    def _analyze_fast(self, token_address: str) -> Dict:
        """
        快速分析 - 使用 Nansen Token Holders API

        优点: 1次API调用，秒级响应，带 Smart Money 标签
        注意: Nansen API 只返回 Top 10 持有者，不返回总持有者数量
        """
        print(f"\n=== Analyzing Holder Concentration (Fast Mode) ===")
        print(f"  Using Nansen API...")

        try:
            # 1次API调用获取Top10持有者
            result = self.nansen.get_token_holders(token_address, page_size=10)

            holders = result["holders"]

            # 调试: 打印持有者数据
            if holders:
                print(f"  [DEBUG] First holder: address={holders[0].address[:16]}..., balance={holders[0].balance_formatted}, pct={holders[0].percentage}%")

            # 如果 Nansen 不返回占比数据 (percentage == -1)，尝试从链上获取总供应量计算
            if holders and holders[0].percentage < 0:
                print(f"  [!] Nansen API did not return percentage data, fetching total supply from chain...")
                print(f"  [DEBUG] First holder balance_formatted: {holders[0].balance_formatted}")
                try:
                    from src.blockchain.contract_reader import ContractReader
                    reader = ContractReader(self.client, token_address)
                    # 使用人类可读格式的总供应量（已除以 decimals）
                    total_supply = reader.get_total_supply_human()
                    print(f"  [DEBUG] Total supply (human readable): {total_supply}")
                    if total_supply and total_supply > 0:
                        print(f"  [OK] Total supply from chain: {total_supply:,.2f}")
                        for h in holders:
                            h.percentage = (h.balance_formatted / total_supply) * 100
                        print(f"  [OK] Recalculated percentages, first holder: {holders[0].percentage:.4f}%")
                    else:
                        print(f"  [!] Could not get total supply, percentages will be 0")
                        for h in holders:
                            h.percentage = 0
                except Exception as e:
                    print(f"  [!] Failed to get total supply: {e}")
                    import traceback
                    traceback.print_exc()
                    for h in holders:
                        h.percentage = 0

            if not holders:
                return {
                    "total_holders": 0,
                    "total_supply": 0,
                    "top10_holders": [],
                    "top10_percentage": 0.0,
                    "score": 0.0,
                    "max_score": 30.0,
                    "risk_level": "unknown",
                    "data_source": "nansen",
                    "error": "No holders found",
                }

            # 计算Top10占比 (Nansen 返回的 ownership_percentage 已经是正确的占比)
            top10_percentage = sum(h.percentage for h in holders[:10])

            # 格式化Top10数据 (包含 Smart Money 标签)
            # 清理标签中的特殊字符
            top10_formatted = []
            for h in holders[:10]:
                # 移除零宽字符
                clean_label = h.address_label.replace('\u200b', '').strip() if h.address_label else ''
                top10_formatted.append((h.address, h.balance, h.percentage, clean_label))

            # 统计 Smart Money/Bot
            smart_money_count = sum(1 for h in holders if h.is_smart_money)
            bot_count = sum(1 for h in holders if h.is_dex_bot)

            # 计算评分
            score = self._calculate_score(top10_percentage)
            risk_level = self._determine_risk_level(top10_percentage)

            print(f"  [OK] Top10 Percentage: {top10_percentage:.2f}%")
            print(f"  [OK] Smart Money/Bots in Top10: {smart_money_count}")
            print(f"  [OK] Score: {score:.2f}/30")

            return {
                "total_holders": "N/A (Top10 only)",  # Nansen 不返回总数
                "total_supply": 0,
                "top10_holders": top10_formatted,
                "top10_percentage": round(top10_percentage, 2),
                "smart_money_count": smart_money_count,
                "bot_count": bot_count,
                "score": round(score, 2),
                "max_score": 30.0,
                "risk_level": risk_level,
                "data_source": "nansen",
                "data_note": "Nansen returns Top 10 holders with labels, not total holder count"
            }

        except NansenError as e:
            print(f"  [!] Nansen API error: {e}")
            print(f"  [!] Falling back to deep mode...")
            # 降级到深度模式 (使用最近的区块范围)
            current_block = self.client.get_latest_block()
            return self.analyze_holder_concentration(
                token_address,
                from_block=max(0, current_block - 50000),
                to_block=current_block
            )

    def get_all_holders(
        self, token_address: str, from_block: int = 0, to_block: int = None
    ) -> Dict[str, int]:
        """
        获取所有持有者及其余额

        Args:
            token_address: 代币合约地址
            from_block: 起始区块(0表示创世区块)
            to_block: 结束区块(None表示最新区块)

        Returns:
            {address: balance} 字典
        """
        # 检查缓存
        cache_key = f"holders_{token_address.lower()}"
        if self.use_cache:
            cached = self.db.get(cache_key)
            if cached:
                print("  Using cached holder data...")
                return cached

        print(f"  Fetching all holders from blockchain...")

        # 1. 收集所有出现过的地址
        reader = ContractReader(self.client, token_address)
        if to_block is None:
            to_block = self.client.get_latest_block()

        # 为了避免RPC限制,分批查询(使用较小批次更稳定)
        BATCH_SIZE = 1000  # 降低到1000以避免RPC限制
        all_addresses = set()
        current = from_block

        while current <= to_block:
            batch_end = min(current + BATCH_SIZE, to_block)
            print(f"    Scanning blocks {current} -> {batch_end}...")

            try:
                events = reader.get_transfer_events(current, batch_end)
                for event in events:
                    # 零地址是铸币/销毁,不是真实持有者
                    if event["from"] != "0x0000000000000000000000000000000000000000":
                        all_addresses.add(event["from"])
                    if event["to"] != "0x0000000000000000000000000000000000000000":
                        all_addresses.add(event["to"])

                current = batch_end + 1
            except Exception as e:
                print(f"    [!] Batch query failed: {e}")
                # 如果还是失败,尝试更小的批次
                if "block range too large" in str(e).lower():
                    print(f"    Retrying with smaller batch size...")
                    smaller_batch = (batch_end - current) // 2
                    if smaller_batch < 100:
                        print(f"    Batch too small, skipping range...")
                        current = batch_end + 1
                        continue
                    batch_end = current + smaller_batch
                    try:
                        events = reader.get_transfer_events(current, batch_end)
                        for event in events:
                            if event["from"] != "0x0000000000000000000000000000000000000000":
                                all_addresses.add(event["from"])
                            if event["to"] != "0x0000000000000000000000000000000000000000":
                                all_addresses.add(event["to"])
                        current = batch_end + 1
                    except Exception as retry_e:
                        print(f"    Retry failed: {retry_e}, skipping...")
                        current = batch_end + 1
                        continue
                else:
                    current = batch_end + 1
                    continue

        print(f"  Found {len(all_addresses)} unique addresses")

        # 2. 查询每个地址的当前余额
        holders = {}
        for i, addr in enumerate(all_addresses, 1):
            if i % 50 == 0:
                print(f"    Checking balances... {i}/{len(all_addresses)}")

            try:
                balance = reader.get_balance(addr)
                if balance > 0:
                    holders[addr] = balance
            except Exception as e:
                print(f"    [!] Failed to get balance for {addr[:10]}...: {e}")
                continue

        print(f"  [OK] Found {len(holders)} holders with non-zero balance")

        # 缓存结果
        if self.use_cache:
            self.db.set(cache_key, holders)

        return holders

    def analyze_holder_concentration(
        self, token_address: str, from_block: int = 0, to_block: int = None
    ) -> Dict:
        """
        分析持有者集中度

        Args:
            token_address: 代币合约地址
            from_block: 起始区块
            to_block: 结束区块

        Returns:
            {
                "total_holders": int,
                "total_supply": int,
                "top10_holders": [(address, balance, percentage)],
                "top10_percentage": float,
                "score": float,
                "risk_level": str
            }
        """
        print(f"\n=== Analyzing Holder Concentration ===")

        # 1. 获取所有持有者
        holders = self.get_all_holders(token_address, from_block, to_block)

        if len(holders) == 0:
            return {
                "total_holders": 0,
                "total_supply": 0,
                "top10_holders": [],
                "top10_percentage": 0.0,
                "score": 0.0,
                "max_score": 30.0,
                "risk_level": "unknown",
                "data_source": "blockpi",
                "error": "No holders found",
            }

        # 2. 计算总供应量(所有持有者余额之和)
        total_supply = sum(holders.values())

        # 3. 按余额排序,获取Top10
        sorted_holders = sorted(holders.items(), key=lambda x: x[1], reverse=True)
        top10 = sorted_holders[:10]

        # 计算Top10占比
        top10_sum = sum([balance for _, balance in top10])
        top10_percentage = (top10_sum / total_supply * 100) if total_supply > 0 else 0

        # 4. 格式化Top10数据
        top10_formatted = [
            (addr, balance, balance / total_supply * 100) for addr, balance in top10
        ]

        # 5. 计算评分 (权重30分)
        score = self._calculate_score(top10_percentage)

        # 6. 风险等级
        risk_level = self._determine_risk_level(top10_percentage)

        return {
            "total_holders": len(holders),
            "total_supply": total_supply,
            "top10_holders": top10_formatted,
            "top10_percentage": round(top10_percentage, 2),
            "score": round(score, 2),
            "max_score": 30.0,
            "risk_level": risk_level,
            "data_source": "blockpi",
        }

    def _calculate_score(self, top10_percentage: float) -> float:
        """
        计算评分 (3-30分)

        评分标准:
        - <= 20%: 30分 (健康，持仓分散)
        - 20-40%: 20-30分 (线性递减)
        - 40-70%: 10-20分 (线性递减)
        - 70-100%: 3-10分 (线性递减，最低3分)

        最低分数为3分，避免显示0分
        """
        if top10_percentage <= 20:
            return 30.0
        elif top10_percentage <= 40:
            # 20-40%之间线性递减: 30 -> 20
            return 30.0 - (top10_percentage - 20) * 0.5
        elif top10_percentage <= 70:
            # 40-70%之间线性递减: 20 -> 10
            return 20.0 - (top10_percentage - 40) * (10.0 / 30.0)
        else:
            # 70-100%之间线性递减: 10 -> 3
            # 100%时最低3分
            score = 10.0 - (top10_percentage - 70) * (7.0 / 30.0)
            return max(3.0, score)

    def _determine_risk_level(self, top10_percentage: float) -> str:
        """
        判断风险等级

        Returns:
            "low_risk" | "medium_risk" | "high_risk" | "extreme_risk"
        """
        if top10_percentage <= 20:
            return "low_risk"
        elif top10_percentage <= 40:
            return "medium_risk"
        elif top10_percentage <= 60:
            return "high_risk"
        else:
            return "extreme_risk"


# 使用示例
if __name__ == "__main__":
    import os
    import time
    from dotenv import load_dotenv

    load_dotenv()

    print("=" * 60)
    print("Holder Analyzer Test")
    print("=" * 60)

    # 测试代币 (WMON)
    token_address = os.getenv("TEST_TOKEN_ADDRESS", "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A")
    print(f"\nTest Token: {token_address}")

    # ========== 快速模式 (Nansen) ==========
    print("\n" + "=" * 60)
    print("Mode 1: FAST (Nansen API)")
    print("=" * 60)

    try:
        nansen = NansenClient()
        client = Web3Client(network="monad_mainnet")

        analyzer = HolderAnalyzer(client, nansen=nansen)
        result = analyzer.analyze(token_address, mode="fast")

        print(f"\n=== Result (Fast Mode) ===")
        print(f"Data Source: {result.get('data_source', 'unknown')}")
        print(f"Total Holders: {result['total_holders']}")
        print(f"Top10 Percentage: {result['top10_percentage']:.2f}%")
        print(f"Smart Money Count: {result.get('smart_money_count', 0)}")
        print(f"Score: {result['score']:.2f}/{result.get('max_score', 30)}")
        print(f"Risk Level: {result['risk_level']}")

        if result.get("top10_holders"):
            print(f"\nTop 5 Holders:")
            for i, holder_data in enumerate(result["top10_holders"][:5], 1):
                if len(holder_data) >= 4:
                    addr, balance, pct, label = holder_data
                    # 移除 emoji 以避免 Windows 控制台编码问题
                    safe_label = label.encode('ascii', 'ignore').decode('ascii') if label else ''
                    print(f"  {i}. {addr[:16]}... - {pct:.2f}% [{safe_label}]")
                else:
                    addr, balance, pct = holder_data[:3]
                    print(f"  {i}. {addr[:16]}... - {pct:.2f}%")

    except Exception as e:
        print(f"\n[!] Fast mode failed: {e}")
        import traceback
        traceback.print_exc()

    # ========== 深度模式 (BlockPi) - 可选 ==========
    # 注意: 深度模式会扫描大量区块，耗时较长
    # 取消下面的注释来测试深度模式

    # print("\n" + "=" * 60)
    # print("Mode 2: DEEP (BlockPi RPC)")
    # print("=" * 60)
    #
    # try:
    #     client = Web3Client(network="monad_mainnet")
    #     analyzer = HolderAnalyzer(client)
    #
    #     current_block = client.get_latest_block()
    #     # 仅扫描最近1000个区块作为演示
    #     result = analyzer.analyze(
    #         token_address,
    #         mode="deep",
    #         from_block=current_block - 1000,
    #         to_block=current_block
    #     )
    #
    #     print(f"\n=== Result (Deep Mode) ===")
    #     print(f"Data Source: {result.get('data_source', 'unknown')}")
    #     print(f"Total Holders: {result['total_holders']}")
    #     print(f"Top10 Percentage: {result['top10_percentage']:.2f}%")
    #     print(f"Score: {result['score']:.2f}/{result.get('max_score', 30)}")
    #     print(f"Risk Level: {result['risk_level']}")
    #
    # except Exception as e:
    #     print(f"\n[!] Deep mode failed: {e}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
