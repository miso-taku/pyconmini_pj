"""
mipライブラリのテスト
"""
import sys
import numpy as np
import mip

# 標準出力のエンコーディングをUTF-8に設定
sys.stdout.reconfigure(encoding='utf-8')

print("=== mipライブラリのテスト ===\n")

# 簡単なTSP問題
print("テスト1: 簡単な3地点TSP")
distance_matrix = np.array([
    [0, 100, 200],
    [100, 0, 150],
    [200, 150, 0]
])

n = 3
model = mip.Model(sense=mip.MINIMIZE)
model.verbose = 0

# 決定変数
x = [[model.add_var(var_type=mip.BINARY) for j in range(n)] for i in range(n)]
u = [model.add_var(var_type=mip.INTEGER, lb=1, ub=n-1) for i in range(n)]

# 目的関数
model.objective = mip.xsum(distance_matrix[i][j] * x[i][j] for i in range(n) for j in range(n))

# 制約
for i in range(n):
    model += mip.xsum(x[i][j] for j in range(n) if i != j) == 1

for j in range(n):
    model += mip.xsum(x[i][j] for i in range(n) if i != j) == 1

for i in range(1, n):
    for j in range(1, n):
        if i != j:
            model += u[i] - u[j] + n * x[i][j] <= n - 1

print("求解中...")
status = model.optimize(max_seconds=10)

if status == mip.OptimizationStatus.OPTIMAL or status == mip.OptimizationStatus.FEASIBLE:
    print(f"✅ 最適化成功: status={status}")
    print(f"   目的関数値: {model.objective_value}")
else:
    print(f"❌ 最適化失敗: status={status}")

print("\n" + "="*60)
print("✅ mipライブラリのテスト完了")
print("="*60)
