"""
processor/mac_deduplicator.py
MAC アドレスの重複排除を行うモジュール
"""


def deduplicate(mac_addresses: list[str]) -> list[str]:
    """
    MAC アドレスリストの重複を排除して返す

    Args:
        mac_addresses: スキャンで取得した MAC アドレスのリスト（重複あり）

    Returns:
        list[str]: 重複排除済みの MAC アドレスのリスト
    """
    unique = list(set(mac_addresses))
    print(f"重複排除: {len(mac_addresses)} → {len(unique)} 台")
    return unique
