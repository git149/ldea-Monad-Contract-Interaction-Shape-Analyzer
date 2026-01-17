"""
Blockvision API 客户端
提供增强的 Monad 链上数据查询能力

用于代币评分系统的核心 API:
- Token Holders: 直接获取代币持有者列表和占比 → 持有者集中度评分 (30分)
- Token Transfers: 获取带时间戳的转账记录 → EOA 活跃度评分 (40分)

优化策略:
- 内置缓存: 同一 token 在 TTL 内不重复请求
- 批量获取: 单次请求尽可能多获取数据
- 自动分页: 支持获取超过单页限制的数据

文档: https://docs.blockvision.org/reference/monad-indexing-api
"""

import os
import time
import requests
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from dotenv import load_dotenv


class BlockvisionError(Exception):
    """Blockvision API 错误基类"""
    pass


class BlockvisionAPIError(BlockvisionError):
    """API 返回错误"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API Error [{code}]: {message}")


class BlockvisionNetworkError(BlockvisionError):
    """网络请求错误"""
    pass


class BlockvisionRateLimitError(BlockvisionError):
    """API 限流错误"""
    pass


class SimpleCache:
    """简单的内存缓存，带 TTL"""

    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: 缓存有效期 (秒)，默认 5 分钟
        """
        self._cache: Dict[str, tuple] = {}  # {key: (value, expire_time)}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None"""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self._cache[key] = (value, time.time() + self.ttl)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()


@dataclass
class TokenHolder:
    """代币持有者信息"""
    address: str
    balance: int          # 原始余额 (wei)
    balance_formatted: float  # 格式化余额
    percentage: float     # 占总供应量百分比
    rank: int = 0         # 排名
    is_contract: bool = False  # 是否是合约地址

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def is_eoa(self) -> bool:
        """是否是 EOA (外部账户)"""
        return not self.is_contract


@dataclass
class TokenTransfer:
    """代币合约交易记录 (来自 account/transactions API)"""
    tx_hash: str
    block_number: int
    timestamp: int        # Unix 时间戳 (毫秒)
    from_address: str
    to_address: str
    from_is_contract: bool  # 发送方是否是合约
    to_is_contract: bool    # 接收方是否是合约
    method_name: str = ""   # 调用的方法名 (如 transfer, withdraw)

    def to_dict(self) -> Dict:
        return asdict(self)

    @property
    def from_is_eoa(self) -> bool:
        """发送方是否是 EOA"""
        return not self.from_is_contract

    @property
    def to_is_eoa(self) -> bool:
        """接收方是否是 EOA"""
        return not self.to_is_contract


class BlockvisionClient:
    """
    Blockvision API 客户端

    提供 Monad 链上数据的增强查询能力，用于代币评分系统。

    核心功能:
    - get_token_holders(): 获取代币持有者列表 → 持有者集中度评分 (30分)
    - get_token_transfers(): 获取转账记录 → EOA 活跃度评分 (40分)

    使用示例:
        >>> client = BlockvisionClient()
        >>> # 获取 Top10 持有者占比
        >>> top10_pct = client.get_top_holders_percentage("0x...", top_n=10)
        >>> # 获取最近转账的独立地址
        >>> transfers = client.get_recent_transfers("0x...", limit=500)
        >>> unique_addrs = client.extract_unique_addresses(transfers)

    注意:
        - Monad Mainnet Indexing API 需要 Pro 套餐
        - API 有调用限制，建议配合缓存使用
    """

    # API 基础 URL (v2 API)
    BASE_URL = "https://api.blockvision.org/v2/monad"

    # 默认超时时间 (秒)
    DEFAULT_TIMEOUT = 30

    # 重试配置
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # 秒

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        auto_retry: bool = True,
        cache_ttl: int = 300
    ):
        """
        初始化 Blockvision 客户端

        Args:
            api_key: API Key，不提供则从环境变量 BLOCKVISION_Monad_RPC 读取
            timeout: 请求超时时间 (秒)
            auto_retry: 是否自动重试失败请求
            cache_ttl: 缓存有效期 (秒)，默认 5 分钟
        """
        load_dotenv()

        # 获取 API Key
        if api_key:
            self.api_key = api_key
        else:
            # 从 RPC URL 中提取 API Key
            rpc_url = os.getenv("BLOCKVISION_Monad_RPC", "")
            if rpc_url:
                # URL 格式: https://monad-mainnet.blockvision.org/v1/{api_key}
                self.api_key = rpc_url.rstrip("/").split("/")[-1]
            else:
                self.api_key = ""

        if not self.api_key:
            raise ValueError(
                "Blockvision API Key not found. "
                "Please set BLOCKVISION_Monad_RPC in .env or pass api_key parameter."
            )

        self.timeout = timeout
        self.auto_retry = auto_retry

        # 创建会话，使用 x-api-key 认证
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key
        })

        # 统计信息
        self._request_count = 0
        self._last_request_time = 0

        # 内存缓存 (避免重复 API 调用)
        self._cache = SimpleCache(ttl_seconds=cache_ttl)

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()

    # ==================== 核心 API 方法 ====================

    def get_token_holders(
        self,
        contract_address: str,
        page_index: int = 1,
        page_size: int = 100,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        获取代币持有者列表

        直接从 Blockvision 索引获取持有者数据，比从 Transfer 事件构建快得多。

        Args:
            contract_address: 代币合约地址
            page_index: 页码 (从 1 开始)
            page_size: 每页数量 (最大 100)
            use_cache: 是否使用缓存 (默认 True)

        Returns:
            {
                "total": 总持有者数量,
                "holders": [TokenHolder, ...],
                "page_index": 当前页码,
                "page_size": 每页数量
            }

        Example:
            >>> result = client.get_token_holders("0x...", page_size=10)
            >>> for holder in result["holders"]:
            ...     print(f"{holder.address}: {holder.percentage}%")
        """
        # 检查缓存
        cache_key = f"holders_{contract_address.lower()}_{page_index}_{page_size}"
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        params = {
            "contractAddress": self._normalize_address(contract_address),
            "pageIndex": max(1, page_index),
            "pageSize": min(max(1, page_size), 100)
        }

        result = self._request("GET", "token/holders", params=params)

        # 解析持有者数据
        # API 返回格式: {"data": [{"holder": "0x...", "percentage": "29.16", "amount": "154230580.01", "isContract": true}]}
        holders = []
        data_list = result.get("data", []) if isinstance(result, dict) else result

        for idx, item in enumerate(data_list):
            # amount 是已格式化的字符串 (如 "154230580.01847634")
            amount_str = item.get("amount", "0")
            try:
                balance_formatted = float(amount_str)
            except (ValueError, TypeError):
                balance_formatted = 0.0

            # percentage 是字符串 (如 "29.165037")
            pct_str = item.get("percentage", "0")
            try:
                percentage = float(pct_str)
            except (ValueError, TypeError):
                percentage = 0.0

            holders.append(TokenHolder(
                address=item.get("holder", item.get("accountAddress", "")),
                balance=int(balance_formatted),  # 近似整数值
                balance_formatted=balance_formatted,
                percentage=percentage,
                rank=(page_index - 1) * page_size + idx + 1,
                is_contract=item.get("isContract", False)
            ))

        response = {
            "total": result.get("total", 0),
            "holders": holders,
            "page_index": page_index,
            "page_size": page_size
        }

        # 缓存结果
        if use_cache:
            self._cache.set(cache_key, response)

        return response

    def get_contract_transactions(
        self,
        contract_address: str,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取代币合约的交易记录 (使用 account/transactions API)

        注意: 此 API 返回与合约交互的所有交易，并且直接标记地址是否为合约。
        这对于 EOA 活跃度分析非常有用，因为可以直接判断 isContract。

        Args:
            contract_address: 代币合约地址
            limit: 每页数量 (最大 100)
            cursor: 分页游标 (来自上一次请求的 nextPageCursor)

        Returns:
            {
                "transactions": [TokenTransfer, ...],
                "next_cursor": 下一页游标 (空字符串表示没有更多数据)
            }

        Example:
            >>> result = client.get_contract_transactions("0x...", limit=50)
            >>> eoa_count = sum(1 for tx in result["transactions"] if tx.from_is_eoa)
        """
        params = {
            "address": self._normalize_address(contract_address),
            "limit": min(max(1, limit), 100)
        }

        if cursor:
            params["cursor"] = cursor

        result = self._request("GET", "account/transactions", params=params)

        # 解析交易数据
        transactions = []
        data_list = result.get("data", []) if isinstance(result, dict) else []

        for item in data_list:
            from_addr_info = item.get("fromAddress", {})
            to_addr_info = item.get("toAddress", {})

            transactions.append(TokenTransfer(
                tx_hash=item.get("hash", ""),
                block_number=int(item.get("blockNumber", 0)),
                timestamp=int(item.get("timestamp", 0)),  # 毫秒
                from_address=item.get("from", ""),
                to_address=item.get("to", ""),
                from_is_contract=from_addr_info.get("isContract", False),
                to_is_contract=to_addr_info.get("isContract", False),
                method_name=item.get("methodName", "")
            ))

        return {
            "transactions": transactions,
            "next_cursor": result.get("nextPageCursor", "")
        }

    def get_token_transfers(
        self,
        contract_address: str,
        from_block: Optional[int] = None,
        to_block: Optional[Union[int, str]] = None,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        page_index: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        获取代币的交易记录 (兼容方法，内部调用 get_contract_transactions)

        注意: Blockvision Monad API 没有专门的 token/transfers 端点，
        此方法使用 account/transactions API 作为替代。

        Args:
            contract_address: 代币合约地址
            其他参数: 为兼容性保留，但可能不完全支持

        Returns:
            {
                "total": 0 (API 不返回总数),
                "transfers": [TokenTransfer, ...],
                "next_cursor": 下一页游标
            }
        """
        result = self.get_contract_transactions(contract_address, limit=page_size)

        return {
            "total": 0,  # API 不返回总数
            "transfers": result["transactions"],
            "next_cursor": result["next_cursor"]
        }

    # ==================== 便捷方法 ====================

    def get_top_holders(
        self,
        contract_address: str,
        top_n: int = 10
    ) -> List[TokenHolder]:
        """
        获取 Top N 持有者

        Args:
            contract_address: 代币合约地址
            top_n: 返回前 N 个持有者 (最大 100)

        Returns:
            Top N 持有者列表
        """
        result = self.get_token_holders(
            contract_address,
            page_index=1,
            page_size=min(top_n, 100)
        )
        return result["holders"][:top_n]

    def get_top_holders_percentage(
        self,
        contract_address: str,
        top_n: int = 10
    ) -> float:
        """
        获取 Top N 持有者的总占比

        Args:
            contract_address: 代币合约地址
            top_n: 统计前 N 个持有者

        Returns:
            总占比 (0-100)
        """
        holders = self.get_top_holders(contract_address, top_n)
        return sum(h.percentage for h in holders)

    def get_holder_count(self, contract_address: str) -> int:
        """
        获取代币总持有者数量

        Args:
            contract_address: 代币合约地址

        Returns:
            持有者数量
        """
        result = self.get_token_holders(contract_address, page_size=1)
        return result["total"]

    def get_recent_transfers(
        self,
        contract_address: str,
        limit: int = 1000,
        use_cache: bool = True
    ) -> List[TokenTransfer]:
        """
        获取最近的交易记录 (带缓存)

        Args:
            contract_address: 代币合约地址
            limit: 最大返回数量 (默认 1000，建议不超过 2000)
            use_cache: 是否使用缓存 (默认 True)

        Returns:
            交易记录列表 (按时间倒序)
        """
        # 检查缓存
        cache_key = f"transfers_{contract_address.lower()}_{limit}"
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        all_transfers = []
        cursor = None

        while len(all_transfers) < limit:
            result = self.get_contract_transactions(
                contract_address,
                limit=min(100, limit - len(all_transfers)),
                cursor=cursor
            )

            transfers = result["transactions"]
            if not transfers:
                break

            all_transfers.extend(transfers)
            cursor = result["next_cursor"]

            # 如果没有下一页游标，说明没有更多数据
            if not cursor:
                break

        result_transfers = all_transfers[:limit]

        # 缓存结果
        if use_cache:
            self._cache.set(cache_key, result_transfers)

        return result_transfers

    def get_transfers_in_time_range(
        self,
        contract_address: str,
        start_timestamp: int,
        end_timestamp: Optional[int] = None,
        limit: int = 10000
    ) -> List[TokenTransfer]:
        """
        获取指定时间范围内的交易记录

        Args:
            contract_address: 代币合约地址
            start_timestamp: 开始时间 (Unix 时间戳，秒)
            end_timestamp: 结束时间 (Unix 时间戳，秒)，None 表示当前时间
            limit: 最大返回数量

        Returns:
            时间范围内的交易记录
        """
        if end_timestamp is None:
            end_timestamp = int(time.time())

        # API 返回的时间戳是毫秒，转换为毫秒进行比较
        start_ts_ms = start_timestamp * 1000
        end_ts_ms = end_timestamp * 1000

        all_transfers = []
        cursor = None

        while len(all_transfers) < limit:
            result = self.get_contract_transactions(
                contract_address,
                limit=100,
                cursor=cursor
            )

            transfers = result["transactions"]
            if not transfers:
                break

            # 过滤时间范围
            for t in transfers:
                if start_ts_ms <= t.timestamp <= end_ts_ms:
                    all_transfers.append(t)
                elif t.timestamp < start_ts_ms:
                    # 已经超出时间范围，停止遍历
                    return all_transfers[:limit]

            cursor = result["next_cursor"]
            if not cursor:
                break

        return all_transfers[:limit]

    # ==================== 工具方法 ====================

    def extract_unique_addresses(
        self,
        transfers: List[TokenTransfer],
        exclude_zero_address: bool = True
    ) -> set:
        """
        从交易记录中提取唯一地址

        Args:
            transfers: 交易记录列表
            exclude_zero_address: 是否排除零地址 (铸币/销毁地址)

        Returns:
            唯一地址集合
        """
        zero_address = "0x0000000000000000000000000000000000000000"
        addresses = set()

        for t in transfers:
            from_addr = t.from_address.lower()
            to_addr = t.to_address.lower()

            if exclude_zero_address:
                if from_addr != zero_address:
                    addresses.add(from_addr)
                if to_addr != zero_address:
                    addresses.add(to_addr)
            else:
                addresses.add(from_addr)
                addresses.add(to_addr)

        return addresses

    def extract_unique_eoa_addresses(
        self,
        transfers: List[TokenTransfer],
        exclude_zero_address: bool = True
    ) -> set:
        """
        从交易记录中提取唯一的 EOA 地址

        利用 API 返回的 isContract 字段直接判断，无需额外 RPC 调用！

        Args:
            transfers: 交易记录列表
            exclude_zero_address: 是否排除零地址

        Returns:
            唯一 EOA 地址集合
        """
        zero_address = "0x0000000000000000000000000000000000000000"
        eoa_addresses = set()

        for t in transfers:
            # 检查发送方
            if t.from_is_eoa:
                from_addr = t.from_address.lower()
                if not exclude_zero_address or from_addr != zero_address:
                    eoa_addresses.add(from_addr)

            # 检查接收方
            if t.to_is_eoa:
                to_addr = t.to_address.lower()
                if not exclude_zero_address or to_addr != zero_address:
                    eoa_addresses.add(to_addr)

        return eoa_addresses

    def count_unique_eoa(
        self,
        contract_address: str,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        统计代币的独立 EOA 数量 (用于 EOA 活跃度评分)

        这是评分系统的核心方法，一站式获取 EOA 统计数据。

        Args:
            contract_address: 代币合约地址
            limit: 分析的交易数量上限

        Returns:
            {
                "unique_eoa_count": 独立 EOA 数量,
                "total_addresses": 总地址数量,
                "eoa_ratio": EOA 占比 (0-100),
                "transactions_analyzed": 分析的交易数量
            }
        """
        transfers = self.get_recent_transfers(contract_address, limit=limit)

        all_addresses = self.extract_unique_addresses(transfers)
        eoa_addresses = self.extract_unique_eoa_addresses(transfers)

        total = len(all_addresses)
        eoa_count = len(eoa_addresses)

        return {
            "unique_eoa_count": eoa_count,
            "total_addresses": total,
            "eoa_ratio": round(eoa_count / total * 100, 2) if total > 0 else 0,
            "transactions_analyzed": len(transfers)
        }

    def is_available(self) -> bool:
        """
        检查 API 是否可用

        Returns:
            True 如果 API 可用
        """
        try:
            # 尝试一个简单的查询
            self.get_token_holders(
                "0x0000000000000000000000000000000000000000",
                page_size=1
            )
            return True
        except BlockvisionRateLimitError:
            # 限流也说明 API 是可用的
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取客户端统计信息

        Returns:
            {
                "request_count": 请求计数,
                "api_key_prefix": API Key 前缀 (用于调试),
                "base_url": 基础 URL
            }
        """
        return {
            "request_count": self._request_count,
            "api_key_prefix": self.api_key[:8] + "..." if len(self.api_key) > 8 else self.api_key,
            "base_url": self.BASE_URL
        }

    # ==================== 内部方法 ====================

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        发送 API 请求

        Args:
            method: HTTP 方法 (GET, POST)
            endpoint: API 端点
            params: URL 参数
            data: 请求体数据

        Returns:
            API 响应的 result 字段

        Raises:
            BlockvisionAPIError: API 返回错误
            BlockvisionNetworkError: 网络请求失败
            BlockvisionRateLimitError: 触发限流
        """
        # API v2 格式: https://api.blockvision.org/v2/monad/{endpoint}
        url = f"{self.BASE_URL}/{endpoint}"

        retries = 0
        last_error = None

        while retries <= (self.MAX_RETRIES if self.auto_retry else 0):
            try:
                self._request_count += 1
                self._last_request_time = time.time()

                if method.upper() == "GET":
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=self.timeout
                    )
                else:
                    response = self.session.post(
                        url,
                        params=params,
                        json=data,
                        timeout=self.timeout
                    )

                # 检查 HTTP 状态码
                if response.status_code == 429:
                    raise BlockvisionRateLimitError("API rate limit exceeded")

                response.raise_for_status()

                # 解析响应
                result = response.json()

                # 检查 API 错误码
                code = result.get("code", 0)
                if code != 0:
                    raise BlockvisionAPIError(
                        code,
                        result.get("message", "Unknown error")
                    )

                return result.get("result", result.get("data", {}))

            except BlockvisionRateLimitError:
                raise
            except BlockvisionAPIError:
                raise
            except requests.exceptions.Timeout as e:
                last_error = BlockvisionNetworkError(f"Request timeout: {e}")
            except requests.exceptions.RequestException as e:
                last_error = BlockvisionNetworkError(f"Request failed: {e}")
            except Exception as e:
                last_error = BlockvisionError(f"Unexpected error: {e}")

            retries += 1
            if retries <= self.MAX_RETRIES and self.auto_retry:
                time.sleep(self.RETRY_DELAY * retries)

        raise last_error

    def _normalize_address(self, address: str) -> str:
        """
        标准化地址格式

        Args:
            address: 原始地址

        Returns:
            标准化后的地址 (小写，带 0x 前缀)
        """
        address = address.strip().lower()
        if not address.startswith("0x"):
            address = "0x" + address
        return address

    def __repr__(self) -> str:
        """返回客户端信息"""
        return (
            f"BlockvisionClient("
            f"api_key={self.api_key[:8]}..., "
            f"requests={self._request_count})"
        )


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()

    print("=" * 60)
    print("Blockvision Client Test")
    print("=" * 60)

    try:
        # 创建客户端
        client = BlockvisionClient()
        print(f"\nClient: {client}")

        # 测试代币地址 (从环境变量获取)
        test_token = os.getenv("TEST_TOKEN_ADDRESS")
        if not test_token:
            print("\nNo TEST_TOKEN_ADDRESS in .env, using WMON")
            test_token = "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A"

        print(f"\nTest Token: {test_token}")

        # 测试 Token Holders API (获取 Top 10)
        print("\n--- Token Holders API ---")
        holders_result = client.get_token_holders(test_token, page_size=10)
        print(f"Total Holders: {holders_result['total']}")

        top10_pct = 0
        for h in holders_result["holders"][:5]:  # 只显示前5个
            print(f"  #{h.rank} {h.address[:16]}... : {h.percentage:.2f}%")
            top10_pct += h.percentage

        # 计算完整的 Top 10 占比
        top10_pct = sum(h.percentage for h in holders_result["holders"][:10])
        print(f"\nTop 10 Holders Total: {top10_pct:.2f}%")

        # 延迟避免限流
        print("\n[Waiting 3s to avoid rate limit...]")
        time.sleep(3)

        # 测试 Contract Transactions API
        print("\n--- Contract Transactions API ---")
        tx_result = client.get_contract_transactions(test_token, limit=10)
        cursor_display = tx_result['next_cursor'][:20] + "..." if tx_result['next_cursor'] else "None"
        print(f"Next Cursor: {cursor_display}")

        eoa_count = 0
        for t in tx_result["transactions"][:5]:  # 只显示前5个
            from_type = "EOA" if t.from_is_eoa else "Contract"
            if t.from_is_eoa:
                eoa_count += 1
            print(f"  {t.from_address[:10]}... ({from_type}) | {t.method_name or 'transfer'}")

        # 从已获取的交易中计算 EOA 统计
        print("\n--- EOA Statistics (from above transactions) ---")
        transfers = tx_result["transactions"]
        all_addrs = client.extract_unique_addresses(transfers)
        eoa_addrs = client.extract_unique_eoa_addresses(transfers)

        print(f"Unique EOA Count: {len(eoa_addrs)}")
        print(f"Total Addresses: {len(all_addrs)}")
        print(f"EOA Ratio: {round(len(eoa_addrs) / len(all_addrs) * 100, 2) if all_addrs else 0}%")
        print(f"Transactions Analyzed: {len(transfers)}")

        # 统计信息
        print("\n--- Client Stats ---")
        stats = client.get_stats()
        print(f"Total API Requests: {stats['request_count']}")

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)

    except BlockvisionError as e:
        print(f"\nBlockvision Error: {e}")
    except Exception as e:
        print(f"\nUnexpected Error: {e}")
        import traceback
        traceback.print_exc()
