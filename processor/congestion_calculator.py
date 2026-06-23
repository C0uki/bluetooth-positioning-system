"""
processor/congestion_calculator.py

【重要】本番では使用しません。
混雑レベルの本番計算は Shoki の API Route 側で実行されます
（process.me Phase 7-4「混雑レベル算出ロジック（API Route側）」参照）。

このモジュールは Surface 単体でのローカル動作確認・事前テスト用です。
ここに実装されているC-3ハイブリッド型のロジックは、
Shoki への実装仕様としてそのまま渡すことができます。
"""

import statistics
from datetime import datetime
from config.settings import (
    LOCAL_PREVIEW_BASELINE_MAX,
    LOCAL_PREVIEW_SWITCH_TIME,
    LOCAL_PREVIEW_STDDEV_THRESHOLD,
    LOCAL_PREVIEW_RATIOS,
)

_device_count_history: list[int] = []
_switched = False


def preview_calculate(device_count: int) -> dict:
    """
    【ローカル確認専用】デバイス数から想定される混雑レベルを計算する。
    本番の判定はサーバー側（Vercel API Route）で行われるため、
    ここでの結果はあくまで「動作確認の参考値」。

    Returns:
        dict: { "status": int, "switchMode": str, "switched": bool }
    """
    global _switched

    _update_history(device_count)

    if not _switched:
        _switched = _should_switch()

    if _switched:
        baseline = _dynamic_baseline()
        mode = "stddev"
    else:
        baseline = LOCAL_PREVIEW_BASELINE_MAX
        mode = "time"

    status = _to_status(device_count, baseline)

    print(f"[参考値] {device_count}台 / baseline={baseline} → status={status} ({mode})")

    return {"status": status, "switchMode": mode, "switched": _switched}


def _should_switch() -> bool:
    now = datetime.now().strftime("%H:%M")
    if now >= LOCAL_PREVIEW_SWITCH_TIME:
        return True
    if len(_device_count_history) >= 5:
        stddev = statistics.stdev(_device_count_history[-10:])
        if stddev <= LOCAL_PREVIEW_STDDEV_THRESHOLD:
            return True
    return False


def _dynamic_baseline() -> int:
    if not _device_count_history:
        return LOCAL_PREVIEW_BASELINE_MAX
    return max(_device_count_history)


def _update_history(device_count: int) -> None:
    _device_count_history.append(device_count)
    if len(_device_count_history) > 30:
        _device_count_history.pop(0)


def _to_status(device_count: int, baseline: int) -> int:
    if baseline <= 0:
        return 1
    # device_count/baseline*100 <= upper を整数比較で評価する。
    # 浮動小数点だと「ちょうど55%」が 55.00000000000001 となり境界の
    # 隙間に落ちて最大値(5)を返してしまうため、両辺を baseline 倍して比較する。
    scaled = device_count * 100
    for status, (_lower, upper) in LOCAL_PREVIEW_RATIOS.items():
        if scaled <= upper * baseline:
            return status
    return 5
