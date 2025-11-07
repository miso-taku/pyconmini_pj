"""
Kernelクラッシュの原因調査用テストスクリプト
段階的に処理を実行して、どこでクラッシュするか特定する
"""
import os
import sys
from dotenv import load_dotenv
import googlemaps

# 標準出力のエンコーディングをUTF-8に設定
sys.stdout.reconfigure(encoding='utf-8')

# 環境変数の読み込み
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    raise ValueError("❌ GOOGLE_MAPS_API_KEYが設定されていません")

print("✅ APIキー取得成功")

# Google Maps クライアント初期化
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
print("✅ クライアント初期化成功")

# テスト1: Geocoding API
print("\n=== テスト1: Geocoding API ===")
try:
    result = gmaps.geocode(address="金山駅", language="ja")
    print(f"✅ Geocoding成功: {len(result)}件の結果")
    if result:
        loc = result[0]["geometry"]["location"]
        print(f"   位置: {loc['lat']}, {loc['lng']}")
except Exception as e:
    print(f"❌ Geocodingエラー: {e}")
    exit(1)

# テスト2: Places Nearby API
print("\n=== テスト2: Places Nearby API ===")
try:
    station_loc = (35.142926, 136.901204)  # 金山駅
    result = gmaps.places_nearby(
        location=station_loc,
        keyword="手羽先",
        rank_by="distance",
        language="ja"
    )
    print(f"✅ Places Nearby成功: {len(result.get('results', []))}件の結果")

    # 最初の5件を取得
    places = result.get("results", [])[:5]
    locations = [station_loc] + [(p["geometry"]["location"]["lat"], p["geometry"]["location"]["lng"]) for p in places]
    print(f"   地点数: {len(locations)}")

except Exception as e:
    print(f"❌ Places Nearbyエラー: {e}")
    exit(1)

# テスト3: Distance Matrix API（小規模）
print("\n=== テスト3: Distance Matrix API（小規模：2地点） ===")
try:
    test_locations = locations[:2]  # 駅と店舗1のみ
    result = gmaps.distance_matrix(
        origins=test_locations,
        destinations=test_locations,
        mode="walking",
        language="ja",
        units="metric"
    )
    print(f"✅ Distance Matrix（2地点）成功")
    print(f"   ステータス: {result['status']}")

except Exception as e:
    print(f"❌ Distance Matrix（2地点）エラー: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# テスト4: Distance Matrix API（全地点）
print("\n=== テスト4: Distance Matrix API（全地点：6地点） ===")
try:
    result = gmaps.distance_matrix(
        origins=locations,
        destinations=locations,
        mode="walking",
        language="ja",
        units="metric"
    )
    print(f"✅ Distance Matrix（6地点）成功")
    print(f"   ステータス: {result['status']}")
    print(f"   行数: {len(result.get('rows', []))}")

    # 最初の行の詳細を確認
    if result.get('rows'):
        first_row = result['rows'][0]
        print(f"   最初の行の要素数: {len(first_row.get('elements', []))}")
        for i, elem in enumerate(first_row.get('elements', [])):
            print(f"      要素{i}: status={elem.get('status')}, distance={elem.get('distance', {}).get('value', 'N/A')}")

except Exception as e:
    print(f"❌ Distance Matrix（6地点）エラー: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("✅ すべてのテスト成功！")
print("="*60)
