# -*- coding: utf-8 -*-
"""
Interaction Shape Analyzer

Analyzes contract interaction patterns to identify distribution shapes,
concentration levels, and potential risks.
"""

from typing import Dict, List, Any, Optional
from collections import Counter
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.blockchain.blockvision_client import BlockvisionClient


def analyze_interaction_shape(
    contract_address: str,
    limit: int = 500,
    fetch_all: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Analyze contract interaction shape and distribution

    Args:
        contract_address: Contract address to analyze
        limit: Maximum number of transactions to fetch
        fetch_all: Whether to fetch all transactions (ignores limit)

    Returns:
        Dictionary with analysis results or None if analysis fails
    """
    try:
        print(f"\n[Analyzer] Starting analysis for {contract_address}")
        print(f"[Analyzer] Limit: {limit}, Fetch all: {fetch_all}")

        # Initialize BlockVision client
        blockvision = BlockvisionClient()

        # Fetch transaction data using get_recent_transfers
        print("[Analyzer] Fetching transactions...")
        if fetch_all:
            transactions = blockvision.get_recent_transfers(
                contract_address,
                limit=10000,  # Large number for "all"
                use_cache=False
            )
        else:
            transactions = blockvision.get_recent_transfers(
                contract_address,
                limit=limit,
                use_cache=True
            )

        if not transactions:
            print("[Analyzer] No transactions found")
            return None

        print(f"[Analyzer] Found {len(transactions)} transactions")

        # Analyze interactions
        interactions = _analyze_interactions(transactions)

        # Classify addresses (basic classification using transaction patterns)
        print("[Analyzer] Classifying addresses...")
        classified = _classify_addresses_simple(transactions, interactions)

        # Calculate metrics
        print("[Analyzer] Calculating metrics...")
        metrics = _calculate_metrics(interactions, classified)

        # Determine shape and risk
        shape_info = _determine_shape(metrics)

        # Get top interactors
        top_interactors = _get_top_interactors(interactions, classified)

        result = {
            "token_address": contract_address,
            "total_addresses": len(interactions),
            "total_interaction_volume": sum(interactions.values()),
            "shape": shape_info["shape"],
            "shape_cn": shape_info["shape_cn"],
            "risk_level": shape_info["risk_level"],
            "top_1_ratio": metrics["top_1_ratio"],
            "top_10_percent_ratio": metrics["top_10_percent_ratio"],
            "bot_warning": metrics["bot_warning"],
            "bot_warning_cn": metrics["bot_warning_cn"],
            "bot_ratio": metrics["bot_ratio"],
            "bot_volume_ratio": metrics["bot_volume_ratio"],
            "type_distribution": metrics["type_distribution"],
            "eoa_ratio": metrics["eoa_ratio"],
            "top_interactors": top_interactors
        }

        print("[Analyzer] Analysis complete")
        return result

    except Exception as e:
        print(f"[Analyzer ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def _analyze_interactions(transactions: List) -> Dict[str, int]:
    """
    Count interactions per address from transaction list

    Args:
        transactions: List of TokenTransfer objects

    Returns:
        Dictionary mapping address to interaction count
    """
    interactions = Counter()

    for tx in transactions:
        # Count interactions from 'from' address
        from_addr = tx.from_address.lower() if hasattr(tx, 'from_address') else ''
        if from_addr and from_addr != '0x0000000000000000000000000000000000000000':
            interactions[from_addr] += 1

    return dict(interactions)


def _classify_addresses_simple(
    transactions: List,
    interactions: Dict[str, int]
) -> Dict[str, Dict[str, Any]]:
    """
    Classify addresses using simple heuristics from transaction data

    Args:
        transactions: List of TokenTransfer objects
        interactions: Interaction counts per address

    Returns:
        Dictionary mapping address to classification info
    """
    classified = {}

    # Build address info from transactions
    address_info = {}
    for tx in transactions:
        from_addr = tx.from_address.lower() if hasattr(tx, 'from_address') else ''
        to_addr = tx.to_address.lower() if hasattr(tx, 'to_address') else ''

        if from_addr and from_addr != '0x0000000000000000000000000000000000000000':
            if from_addr not in address_info:
                address_info[from_addr] = {
                    'is_contract': getattr(tx, 'from_is_contract', False),
                    'methods': []
                }
            method = getattr(tx, 'method_name', '')
            if method:
                address_info[from_addr]['methods'].append(method)

    # Classify each address
    for addr in interactions.keys():
        info = address_info.get(addr, {'is_contract': False, 'methods': []})

        # Determine type based on patterns
        addr_type = _determine_address_type_simple(
            addr,
            info.get('is_contract', False),
            interactions[addr],
            info.get('methods', [])
        )

        classified[addr] = {
            "type": addr_type,
            "labels": [],
            "name": "",
            "is_contract": info.get('is_contract', False)
        }

    return classified


def _determine_address_type_simple(
    address: str,
    is_contract: bool,
    interaction_count: int,
    methods: List[str]
) -> str:
    """
    Determine address type using simple heuristics

    Returns:
        One of: bot, dex, cex, smart_money, contract, eoa_unlabeled
    """
    # If it's a contract, classify as contract
    if is_contract:
        return "contract"

    # Bot detection: very high interaction frequency
    if interaction_count > 50:  # More than 50 interactions suggests automation
        return "bot"

    # Smart money: moderate to high activity
    if interaction_count > 10:
        return "smart_money"

    # Default to EOA
    return "eoa_unlabeled"


def _calculate_metrics(
    interactions: Dict[str, int],
    classified: Dict[str, Dict]
) -> Dict[str, Any]:
    """
    Calculate distribution and concentration metrics
    """
    total_addresses = len(interactions)
    total_volume = sum(interactions.values())

    # Sort by interaction count
    sorted_interactions = sorted(
        interactions.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Calculate top percentages
    top_1_volume = sorted_interactions[0][1] if sorted_interactions else 0
    top_1_ratio = (top_1_volume / total_volume * 100) if total_volume > 0 else 0

    top_10_percent_count = max(1, int(total_addresses * 0.1))
    top_10_percent_volume = sum(
        count for _, count in sorted_interactions[:top_10_percent_count]
    )
    top_10_percent_ratio = (
        top_10_percent_volume / total_volume * 100
    ) if total_volume > 0 else 0

    # Calculate type distribution
    type_counts = Counter()
    type_volumes = Counter()

    for addr, count in interactions.items():
        addr_type = classified.get(addr, {}).get("type", "eoa_unlabeled")
        type_counts[addr_type] += 1
        type_volumes[addr_type] += count

    type_distribution = {}
    for addr_type in ["bot", "dex", "cex", "smart_money", "contract", "eoa_unlabeled"]:
        type_distribution[addr_type] = {
            "count": type_counts.get(addr_type, 0),
            "volume": type_volumes.get(addr_type, 0)
        }

    # Bot analysis
    bot_count = type_counts.get("bot", 0)
    bot_volume = type_volumes.get("bot", 0)
    bot_ratio = (bot_count / total_addresses * 100) if total_addresses > 0 else 0
    bot_volume_ratio = (bot_volume / total_volume * 100) if total_volume > 0 else 0

    # Bot warning level
    if bot_volume_ratio >= 50:
        bot_warning = "HIGH"
        bot_warning_cn = "高风险：Bot 活动占主导"
    elif bot_volume_ratio >= 20:
        bot_warning = "MEDIUM"
        bot_warning_cn = "中风险：Bot 活动明显"
    else:
        bot_warning = "LOW"
        bot_warning_cn = "低风险：Bot 活动较少"

    # EOA ratio
    eoa_count = type_counts.get("eoa_unlabeled", 0)
    eoa_ratio = (eoa_count / total_addresses * 100) if total_addresses > 0 else 0

    return {
        "top_1_ratio": round(top_1_ratio, 2),
        "top_10_percent_ratio": round(top_10_percent_ratio, 2),
        "bot_warning": bot_warning,
        "bot_warning_cn": bot_warning_cn,
        "bot_ratio": round(bot_ratio, 2),
        "bot_volume_ratio": round(bot_volume_ratio, 2),
        "type_distribution": type_distribution,
        "eoa_ratio": round(eoa_ratio, 2)
    }


def _determine_shape(metrics: Dict) -> Dict[str, str]:
    """
    Determine interaction shape and risk level
    """
    top_10_ratio = metrics["top_10_percent_ratio"]
    bot_volume_ratio = metrics["bot_volume_ratio"]

    # Determine shape
    if top_10_ratio >= 80:
        shape = "HIGHLY_CONCENTRATED"
        shape_cn = "高度集中型"
        risk = "HIGH"
    elif top_10_ratio >= 60:
        shape = "CONCENTRATED"
        shape_cn = "集中型"
        risk = "MEDIUM_HIGH"
    elif top_10_ratio >= 40:
        shape = "MODERATE"
        shape_cn = "适度分散型"
        risk = "MEDIUM"
    else:
        shape = "DISTRIBUTED"
        shape_cn = "分散型"
        risk = "LOW"

    # Adjust risk based on bot activity
    if bot_volume_ratio >= 50:
        risk = "HIGH"
    elif bot_volume_ratio >= 20 and risk != "HIGH":
        if risk == "LOW":
            risk = "MEDIUM"
        elif risk == "MEDIUM":
            risk = "MEDIUM_HIGH"

    return {
        "shape": shape,
        "shape_cn": shape_cn,
        "risk_level": risk
    }


def _get_top_interactors(
    interactions: Dict[str, int],
    classified: Dict[str, Dict]
) -> List[Dict[str, Any]]:
    """
    Get top interactors with their info
    """
    sorted_interactions = sorted(
        interactions.items(),
        key=lambda x: x[1],
        reverse=True
    )

    top_interactors = []
    for addr, count in sorted_interactions[:10]:
        info = classified.get(addr, {})
        top_interactors.append({
            "address": addr,
            "interaction_count": count,
            "type": info.get("type", "unknown"),
            "labels": info.get("labels", []),
            "name": info.get("name", "")
        })

    return top_interactors


def generate_profile_report(result: Dict[str, Any]) -> str:
    """
    Generate a formatted profile report from analysis results

    Args:
        result: Analysis result dictionary

    Returns:
        Formatted report string
    """
    report_lines = []

    report_lines.append("=" * 60)
    report_lines.append("  CONTRACT INTERACTION PROFILE")
    report_lines.append("=" * 60)
    report_lines.append("")

    # Basic Info
    report_lines.append(f"Contract Address: {result['token_address']}")
    report_lines.append(f"Total Addresses:  {result['total_addresses']}")
    report_lines.append(f"Total Interactions: {result['total_interaction_volume']}")
    report_lines.append("")

    # Shape Analysis
    report_lines.append("DISTRIBUTION SHAPE")
    report_lines.append("-" * 60)
    report_lines.append(f"Shape: {result['shape']} ({result['shape_cn']})")
    report_lines.append(f"Risk Level: {result['risk_level']}")
    report_lines.append("")

    # Concentration
    report_lines.append("CONCENTRATION METRICS")
    report_lines.append("-" * 60)
    report_lines.append(f"Top 1 Address: {result['top_1_ratio']:.2f}% of volume")
    report_lines.append(f"Top 10% Addresses: {result['top_10_percent_ratio']:.2f}% of volume")
    report_lines.append("")

    # Bot Analysis
    report_lines.append("BOT ACTIVITY ANALYSIS")
    report_lines.append("-" * 60)
    report_lines.append(f"Warning Level: {result['bot_warning']} ({result['bot_warning_cn']})")
    report_lines.append(f"Bot Addresses: {result['bot_ratio']:.2f}%")
    report_lines.append(f"Bot Volume: {result['bot_volume_ratio']:.2f}%")
    report_lines.append("")

    # Address Distribution
    report_lines.append("ADDRESS TYPE DISTRIBUTION")
    report_lines.append("-" * 60)
    td = result['type_distribution']
    report_lines.append(f"  EOA (Unlabeled): {td['eoa_unlabeled']['count']:>5} addresses")
    report_lines.append(f"  Bots:            {td['bot']['count']:>5} addresses")
    report_lines.append(f"  DEX:             {td['dex']['count']:>5} addresses")
    report_lines.append(f"  CEX:             {td['cex']['count']:>5} addresses")
    report_lines.append(f"  Smart Money:     {td['smart_money']['count']:>5} addresses")
    report_lines.append(f"  Contracts:       {td['contract']['count']:>5} addresses")
    report_lines.append("")

    # Top Interactors
    report_lines.append("TOP 5 INTERACTORS")
    report_lines.append("-" * 60)
    for i, interactor in enumerate(result['top_interactors'][:5], 1):
        name = interactor['name'] or interactor['address'][:10] + "..."
        report_lines.append(
            f"{i}. {name} ({interactor['type']}): "
            f"{interactor['interaction_count']} interactions"
        )

    report_lines.append("")
    report_lines.append("=" * 60)

    return "\n".join(report_lines)
