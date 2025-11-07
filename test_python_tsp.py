"""
python-tspライブラリのテスト
"""
import sys
import numpy as np
from python_tsp.exact import solve_tsp_dynamic_programming

# 標準出力のエンコーディングをUTF-8に設定
sys.stdout.reconfigure(encoding='utf-8')

print("=== python-tspライブラリのテスト ===\n")

# 簡単なTSP問題（6地点：駅+5店舗）
print("テスト: 6地点TSP（駅+5店舗）")
distance_matrix = np.array([
    [0, 98, 98, 167, 171, 346],
    [98, 0, 50, 120, 140, 280],
    [98, 50, 0, 100, 110, 250],
    [167, 120, 100, 0, 80, 200],
    [171, 140, 110, 80, 0, 150],
    [346, 280, 250, 200, 150, 0]
])

print(f"距離行列: {distance_matrix.shape}")
print("求解中...")

# TSPを解く
permutation, distance = solve_tsp_dynamic_programming(distance_matrix)

print(f"✅ 最適化成功")
print(f"   訪問順序: {permutation}")
print(f"   総移動距離: {distance}m")

# 駅から始まるように調整
station_idx = permutation.index(0)
visit_order = permutation[station_idx:] + permutation[:station_idx]
visit_order.append(0)  # 駅に戻る

print(f"   駅から始まる順序: {visit_order}")

print("\n" + "="*60)
print("✅ python-tspライブラリのテスト完了")
print("="*60)
