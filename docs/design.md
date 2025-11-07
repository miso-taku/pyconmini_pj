# 詳細設計書: 店舗巡回ルート最適化アプリケーション

## 1. システムアーキテクチャ

### 1.1 全体構成

```
┌─────────────────────────────────────────────────────────┐
│            Jupyter Notebook (main.ipynb)                 │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル1: ライブラリインポート・設定                  │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル2: データモデル定義                            │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル3: 店舗検索関数                                │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル4: 距離計算関数                                │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル5: ルート最適化関数                            │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル6: 可視化関数                                  │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ セル7: メイン実行                                  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ↓↑
┌─────────────────────────────────────────────────────────┐
│                   外部API層                              │
│  - Google Places API                                     │
│  - Google Maps Distance Matrix API                       │
└─────────────────────────────────────────────────────────┘
```

### 1.2 ディレクトリ構成

```
pyconmini_pj/
├── .env                          # APIキー設定（gitignore対象）
├── .env.example                  # APIキー設定テンプレート
├── .gitignore
├── requirements.txt              # 依存パッケージ
├── README.md                     # 実行手順
├── CLAUDE.md
├── docs/
│   ├── requirements.md           # 要求定義書
│   └── design.md                 # 本ドキュメント
└── notebooks/
    └── main.ipynb                # メインノートブック（全機能を含む）
```

## 2. Notebookセル構成設計

### 2.1 セル1: ライブラリインポートと設定

#### 2.1.1 責務
- 必要なライブラリのインポート
- 環境変数からAPIキーを読み込み
- アプリケーション設定の定義

#### 2.1.2 実装内容

```python
# ライブラリインポート
import os
from dotenv import load_dotenv
import googlemaps
import numpy as np
import pandas as pd
import mip
import ipyleaflet
from ipywidgets import HTML
from dataclasses import dataclass
from typing import List, Tuple, Optional

# 環境変数の読み込み
load_dotenv()

# 設定
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
MAX_SEARCH_RESULTS = 10
TRAVEL_MODE = "walking"
OPTIMIZATION_TIME_LIMIT = 30  # 秒
WALKING_SPEED_KM_H = 4.0  # 徒歩速度 km/h

# APIキーの検証
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("❌ GOOGLE_MAPS_API_KEYが設定されていません。.envファイルを確認してください。")

# Google Maps クライアント初期化
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

print("✅ 設定完了")
print(f"📍 最大検索結果数: {MAX_SEARCH_RESULTS}件")
print(f"🚶 移動手段: {TRAVEL_MODE}")
```

### 2.2 セル2: データモデル定義

#### 2.2.1 責務
- アプリケーション内で使用するデータクラスを定義

#### 2.2.2 実装内容

```python
@dataclass
class Location:
    """位置情報を表すクラス"""
    lat: float  # 緯度
    lng: float  # 経度

    def __post_init__(self):
        if not (-90 <= self.lat <= 90):
            raise ValueError(f"緯度が範囲外です: {self.lat}")
        if not (-180 <= self.lng <= 180):
            raise ValueError(f"経度が範囲外です: {self.lng}")

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lng)


@dataclass
class Place:
    """店舗情報を表すクラス"""
    place_id: str
    name: str
    address: str
    location: Location
    distance_from_station: Optional[float] = None  # メートル

    def to_dict(self) -> dict:
        return {
            "店舗名": self.name,
            "住所": self.address,
            "駅からの距離": f"{self.distance_from_station:.0f}m" if self.distance_from_station else "N/A"
        }


@dataclass
class Station:
    """駅情報を表すクラス"""
    name: str
    location: Location

    def to_tuple(self) -> Tuple[float, float]:
        return self.location.to_tuple()


@dataclass
class Route:
    """最適化されたルート情報を表すクラス"""
    station: Station
    places: List[Place]  # 最適順序
    total_distance: float  # メートル
    segment_distances: List[float]  # 各区間の距離（メートル）

    @property
    def estimated_time(self) -> float:
        """推定所要時間（分）"""
        return (self.total_distance / 1000) / WALKING_SPEED_KM_H * 60

    def to_dataframe(self) -> pd.DataFrame:
        """ルート詳細のDataFrameを作成"""
        data = []
        cumulative_distance = 0

        for i, place in enumerate(self.places, 1):
            segment_dist = self.segment_distances[i-1]
            cumulative_distance += segment_dist
            data.append({
                "訪問順": i,
                "店舗名": place.name,
                "前地点からの距離": f"{segment_dist:.0f}m",
                "累積距離": f"{cumulative_distance:.0f}m"
            })

        return pd.DataFrame(data)

    def summary(self) -> pd.DataFrame:
        """サマリー情報のDataFrameを作成"""
        data = {
            "項目": ["総移動距離", "推定所要時間", "訪問店舗数"],
            "値": [
                f"{self.total_distance:.0f}m ({self.total_distance/1000:.2f}km)",
                f"{self.estimated_time:.1f}分",
                f"{len(self.places)}件"
            ]
        }
        return pd.DataFrame(data)

print("✅ データモデル定義完了")
```

### 2.3 セル3: 店舗検索関数

#### 2.3.1 責務
- 駅の位置情報取得
- 店舗検索

#### 2.3.2 実装内容

```python
def search_station(station_name: str) -> Station:
    """
    駅名から駅の位置情報を取得

    Args:
        station_name: 駅名

    Returns:
        Station: 駅情報オブジェクト

    Raises:
        ValueError: 駅が見つからない場合
    """
    try:
        result = gmaps.geocode(address=station_name, language="ja")

        if not result:
            raise ValueError(f"'{station_name}' に該当する駅が見つかりませんでした")

        location_data = result[0]["geometry"]["location"]
        location = Location(lat=location_data["lat"], lng=location_data["lng"])

        return Station(name=station_name, location=location)

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"駅の検索中にエラーが発生しました: {e}")


def search_nearby_places(station: Station, keyword: str, max_results: int = MAX_SEARCH_RESULTS) -> List[Place]:
    """
    駅周辺の店舗を検索

    Args:
        station: 駅情報
        keyword: 検索キーワード
        max_results: 最大取得件数

    Returns:
        List[Place]: 店舗リスト（駅から近い順）

    Raises:
        ValueError: 検索結果が0件の場合
    """
    try:
        result = gmaps.places_nearby(
            location=station.to_tuple(),
            keyword=keyword,
            rank_by="distance",
            language="ja"
        )

        if not result.get("results"):
            raise ValueError(f"'{keyword}' に該当する店舗が見つかりませんでした")

        places = []
        for place_data in result["results"][:max_results]:
            location_data = place_data["geometry"]["location"]
            location = Location(lat=location_data["lat"], lng=location_data["lng"])

            place = Place(
                place_id=place_data["place_id"],
                name=place_data["name"],
                address=place_data.get("vicinity", "住所情報なし"),
                location=location
            )
            places.append(place)

        if len(places) < max_results:
            print(f"⚠️ 検索結果が{len(places)}件のみでした")

        return places

    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"店舗検索中にエラーが発生しました: {e}")


print("✅ 店舗検索関数定義完了")
```

### 2.4 セル4: 距離計算関数

#### 2.4.1 責務
- 距離行列の計算

#### 2.4.2 実装内容

```python
def calculate_distance_matrix(station: Station, places: List[Place]) -> np.ndarray:
    """
    駅と全店舗間の距離行列を計算

    距離行列の構造:
    - インデックス0: 駅
    - インデックス1〜N: 各店舗

    Args:
        station: 駅情報
        places: 店舗リスト

    Returns:
        np.ndarray: 距離行列 (N+1 x N+1)
    """
    # 全地点の位置情報リストを作成
    locations = [station.to_tuple()] + [place.location.to_tuple() for place in places]
    num_locations = len(locations)

    # 距離行列を初期化
    distance_matrix = np.zeros((num_locations, num_locations))

    try:
        # Distance Matrix APIを呼び出し
        result = gmaps.distance_matrix(
            origins=locations,
            destinations=locations,
            mode=TRAVEL_MODE,
            language="ja",
            units="metric"
        )

        # レスポンスから距離を抽出
        for i in range(num_locations):
            for j in range(num_locations):
                if i == j:
                    distance_matrix[i][j] = 0
                else:
                    element = result["rows"][i]["elements"][j]
                    if element["status"] == "OK":
                        distance_matrix[i][j] = element["distance"]["value"]  # メートル
                    else:
                        # 経路が見つからない場合は大きな値を設定
                        distance_matrix[i][j] = 999999
                        print(f"⚠️ 地点{i}から地点{j}への経路が見つかりませんでした")

        # 店舗に駅からの距離を設定
        for idx, place in enumerate(places, 1):
            place.distance_from_station = distance_matrix[0][idx]

        return distance_matrix

    except Exception as e:
        raise ValueError(f"距離計算中にエラーが発生しました: {e}")


print("✅ 距離計算関数定義完了")
```

### 2.5 セル5: ルート最適化関数

#### 2.5.1 責務
- TSP問題の定式化と求解

#### 2.5.2 実装内容

```python
def optimize_route(station: Station, places: List[Place], distance_matrix: np.ndarray) -> Route:
    """
    TSPとして最適ルートを計算

    Args:
        station: 駅情報
        places: 店舗リスト
        distance_matrix: 距離行列

    Returns:
        Route: 最適化されたルート情報
    """
    n = len(distance_matrix)  # 地点数（駅 + 店舗）

    # モデル作成
    model = mip.Model(sense=mip.MINIMIZE)
    model.verbose = 0  # ログを抑制

    # 決定変数: x[i][j] = 地点iから地点jへ移動するか（1 or 0）
    x = [[model.add_var(var_type=mip.BINARY) for j in range(n)] for i in range(n)]

    # 補助変数: u[i] = 地点iの訪問順序（部分巡回路除去用）
    u = [model.add_var(var_type=mip.INTEGER, lb=1, ub=n-1) for i in range(n)]

    # 目的関数: 総移動距離の最小化
    model.objective = mip.xsum(distance_matrix[i][j] * x[i][j] for i in range(n) for j in range(n))

    # 制約1: 各地点から出る辺は1本のみ
    for i in range(n):
        model += mip.xsum(x[i][j] for j in range(n) if i != j) == 1

    # 制約2: 各地点に入る辺は1本のみ
    for j in range(n):
        model += mip.xsum(x[i][j] for i in range(n) if i != j) == 1

    # 制約3: 部分巡回路の除去（MTZ制約）
    for i in range(1, n):
        for j in range(1, n):
            if i != j:
                model += u[i] - u[j] + n * x[i][j] <= n - 1

    # 求解
    status = model.optimize(max_seconds=OPTIMIZATION_TIME_LIMIT)

    if status != mip.OptimizationStatus.OPTIMAL and status != mip.OptimizationStatus.FEASIBLE:
        raise ValueError("最適化に失敗しました。時間制限内に解が見つかりませんでした。")

    # 解から訪問順序を抽出
    current = 0  # 駅からスタート
    visit_order = [0]
    visited = {0}

    while len(visited) < n:
        for j in range(n):
            if j not in visited and x[current][j].x > 0.5:
                visit_order.append(j)
                visited.add(j)
                current = j
                break

    # Routeオブジェクトを構築
    optimized_places = [places[i-1] for i in visit_order[1:-1]]  # 駅を除く

    # 各区間の距離を計算
    segment_distances = []
    for i in range(len(visit_order) - 1):
        segment_distances.append(distance_matrix[visit_order[i]][visit_order[i+1]])

    total_distance = sum(segment_distances)

    # 最後の店舗から駅への距離は除外（表示用）
    segment_distances_without_return = segment_distances[:-1]

    return Route(
        station=station,
        places=optimized_places,
        total_distance=total_distance,
        segment_distances=segment_distances_without_return
    )


print("✅ ルート最適化関数定義完了")
```

### 2.6 セル6: 可視化関数

#### 2.6.1 責務
- 地図表示
- 表形式表示

#### 2.6.2 実装内容

```python
def visualize_search_results(station: Station, places: List[Place]) -> ipyleaflet.Map:
    """
    検索結果を地図上に表示

    Args:
        station: 駅情報
        places: 店舗リスト

    Returns:
        ipyleaflet.Map: 検索結果を表示した地図
    """
    # 中心位置を計算
    center = station.to_tuple()

    # 地図作成
    m = ipyleaflet.Map(center=center, zoom=14)

    # 駅のマーカーを追加
    station_marker = ipyleaflet.Marker(
        location=center,
        draggable=False,
        title=station.name,
        icon=ipyleaflet.AwesomeIcon(name='train', marker_color='blue')
    )
    m.add_layer(station_marker)

    # 店舗のマーカーを追加
    for place in places:
        marker = ipyleaflet.Marker(
            location=place.location.to_tuple(),
            draggable=False,
            title=place.name,
            icon=ipyleaflet.AwesomeIcon(name='store', marker_color='red')
        )

        # ポップアップ
        popup_html = f"""
        <b>{place.name}</b><br>
        {place.address}<br>
        駅から: {place.distance_from_station:.0f}m
        """
        popup = ipyleaflet.Popup(
            location=place.location.to_tuple(),
            child=HTML(popup_html),
            close_button=True,
            auto_close=True
        )
        marker.popup = popup
        m.add_layer(marker)

    return m


def visualize_optimized_route(route: Route) -> ipyleaflet.Map:
    """
    最適化されたルートを地図上に表示

    Args:
        route: ルート情報

    Returns:
        ipyleaflet.Map: ルートを表示した地図
    """
    # 中心位置を計算
    center = route.station.to_tuple()

    # 地図作成
    m = ipyleaflet.Map(center=center, zoom=14)

    # 駅のマーカーを追加
    station_marker = ipyleaflet.Marker(
        location=center,
        draggable=False,
        title=route.station.name,
        icon=ipyleaflet.AwesomeIcon(name='train', marker_color='blue')
    )
    m.add_layer(station_marker)

    # 店舗のマーカーを追加（訪問順に番号付き）
    for idx, place in enumerate(route.places, 1):
        marker = ipyleaflet.Marker(
            location=place.location.to_tuple(),
            draggable=False,
            title=f"{idx}. {place.name}",
            icon=ipyleaflet.AwesomeIcon(
                name='info',
                marker_color='green',
                icon_color='white'
            )
        )

        # ポップアップ
        popup_html = f"""
        <b>訪問順: {idx}</b><br>
        <b>{place.name}</b><br>
        {place.address}
        """
        popup = ipyleaflet.Popup(
            location=place.location.to_tuple(),
            child=HTML(popup_html),
            close_button=True,
            auto_close=True
        )
        marker.popup = popup
        m.add_layer(marker)

    # ルート線を追加
    route_coords = [route.station.to_tuple()]
    route_coords.extend([place.location.to_tuple() for place in route.places])
    route_coords.append(route.station.to_tuple())  # 駅に戻る

    polyline = ipyleaflet.Polyline(
        locations=route_coords,
        color="blue",
        fill=False,
        weight=3
    )
    m.add_layer(polyline)

    return m


def display_search_results_table(places: List[Place]) -> pd.DataFrame:
    """
    検索結果を表形式で表示

    Args:
        places: 店舗リスト

    Returns:
        pd.DataFrame: 表示用DataFrame
    """
    data = []
    for idx, place in enumerate(places, 1):
        data.append({
            "番号": idx,
            "店舗名": place.name,
            "住所": place.address,
            "駅からの距離": f"{place.distance_from_station:.0f}m" if place.distance_from_station else "N/A"
        })
    return pd.DataFrame(data)


print("✅ 可視化関数定義完了")
```

### 2.7 セル7: メイン実行

#### 2.7.1 責務
- ユーザー入力受付
- 各関数の呼び出し
- 結果の表示

#### 2.7.2 実装内容

```python
# ========================================
# パラメータ設定
# ========================================
STATION_NAME = "新宿駅"      # 駅名を入力
KEYWORD = "カフェ"            # 検索キーワードを入力

print("="*60)
print(f"🚉 駅: {STATION_NAME}")
print(f"🔍 キーワード: {KEYWORD}")
print("="*60)

try:
    # ========================================
    # 1. 駅の検索
    # ========================================
    print("\n📍 駅を検索中...")
    station = search_station(STATION_NAME)
    print(f"✅ 駅の位置情報取得完了: {station.location.lat:.6f}, {station.location.lng:.6f}")

    # ========================================
    # 2. 店舗の検索
    # ========================================
    print(f"\n🏪 '{KEYWORD}' を検索中...")
    places = search_nearby_places(station, KEYWORD)
    print(f"✅ {len(places)}件の店舗を取得しました")

    # 検索結果を表示
    print("\n📊 検索結果（駅から近い順）:")
    df_search = display_search_results_table(places)
    display(df_search)

    print("\n🗺️ 検索結果の地図表示:")
    map_search = visualize_search_results(station, places)
    display(map_search)

    # ========================================
    # 3. 距離行列の計算
    # ========================================
    print("\n📏 距離行列を計算中...")
    distance_matrix = calculate_distance_matrix(station, places)
    print(f"✅ 距離行列計算完了 ({len(distance_matrix)}x{len(distance_matrix)})")

    # ========================================
    # 4. ルートの最適化
    # ========================================
    print("\n🔧 最適ルートを計算中...")
    route = optimize_route(station, places, distance_matrix)
    print(f"✅ 最適化完了")

    # ルート詳細を表示
    print("\n📊 最適ルート詳細:")
    df_route = route.to_dataframe()
    display(df_route)

    print("\n📈 サマリー:")
    df_summary = route.summary()
    display(df_summary)

    print("\n🗺️ 最適ルートの地図表示:")
    map_route = visualize_optimized_route(route)
    display(map_route)

    print("\n" + "="*60)
    print("✅ すべての処理が完了しました！")
    print("="*60)

except ValueError as e:
    print(f"\n❌ エラー: {e}")
    print("💡 入力内容を確認してください")
except Exception as e:
    print(f"\n❌ 予期しないエラー: {e}")
    print("💡 APIキーや設定を確認してください")
```

## 3. データフロー

### 3.1 処理フロー図

```
[ユーザー入力]
  駅名、検索キーワード
    ↓
[セル7: メイン実行開始]
    ↓
[セル3: search_station()]
  → Google Geocoding API
  → Station オブジェクト作成
    ↓
[セル3: search_nearby_places()]
  → Google Places API
  → Place オブジェクトリスト作成
    ↓
[セル6: 検索結果の表示]
  → DataFrame表示
  → 地図表示（ipyleaflet）
    ↓
[セル4: calculate_distance_matrix()]
  → Google Distance Matrix API
  → 距離行列（numpy配列）作成
    ↓
[セル5: optimize_route()]
  → Python-MIP によるTSP求解
  → Route オブジェクト作成
    ↓
[セル6: 最適ルートの表示]
  → DataFrame表示（詳細・サマリー）
  → 地図表示（ルート描画）
    ↓
[完了]
```

## 4. API設計

### 4.1 外部API呼び出し仕様

#### 4.1.1 Google Geocoding API

**使用箇所**: `search_station()`

**リクエスト**:
```python
gmaps.geocode(address="新宿駅", language="ja")
```

**レスポンス**:
```python
[{
    "geometry": {"location": {"lat": 35.6896, "lng": 139.7006}},
    "formatted_address": "日本、東京都新宿区..."
}]
```

#### 4.1.2 Google Places API (Nearby Search)

**使用箇所**: `search_nearby_places()`

**リクエスト**:
```python
gmaps.places_nearby(
    location=(35.6896, 139.7006),
    keyword="カフェ",
    rank_by="distance",
    language="ja"
)
```

**レスポンス**:
```python
{
    "results": [
        {
            "place_id": "ChIJ...",
            "name": "スターバックス",
            "vicinity": "東京都新宿区...",
            "geometry": {"location": {"lat": 35.6900, "lng": 139.7010}}
        }
    ]
}
```

#### 4.1.3 Google Distance Matrix API

**使用箇所**: `calculate_distance_matrix()`

**リクエスト**:
```python
gmaps.distance_matrix(
    origins=[(35.6896, 139.7006), ...],
    destinations=[(35.6900, 139.7010), ...],
    mode="walking",
    language="ja",
    units="metric"
)
```

**レスポンス**:
```python
{
    "rows": [
        {
            "elements": [
                {"distance": {"value": 450}, "status": "OK"}
            ]
        }
    ]
}
```

## 5. TSP最適化の数理モデル

### 5.1 決定変数

- `x[i][j]`: 地点iから地点jへ移動する場合1、しない場合0（二値変数）
- `u[i]`: 地点iの訪問順序（整数変数、部分巡回路除去用）

### 5.2 目的関数

```
minimize: Σ(i,j) distance[i][j] * x[i][j]
```

### 5.3 制約条件

1. **各地点から出る辺は1本**: `Σ(j) x[i][j] = 1` for all i
2. **各地点に入る辺は1本**: `Σ(i) x[i][j] = 1` for all j
3. **部分巡回路の除去（MTZ制約）**: `u[i] - u[j] + n*x[i][j] <= n-1` for all i≠j (i,j ≠ 0)
4. **訪問順序の範囲**: `1 <= u[i] <= n-1` for all i ≠ 0

## 6. エラーハンドリング

### 6.1 エラー種別と対応

| エラー種別 | 検出箇所 | エラーメッセージ例 | 対応 |
|-----------|---------|------------------|------|
| APIキー未設定 | セル1 | `GOOGLE_MAPS_API_KEYが設定されていません` | .env確認を促す |
| 駅が見つからない | `search_station()` | `'新宿' に該当する駅が見つかりませんでした` | 駅名の再入力を促す |
| 店舗が見つからない | `search_nearby_places()` | `'カフェ' に該当する店舗が見つかりませんでした` | キーワード変更を促す |
| API呼び出し失敗 | 各API関数 | `APIエラー: ...` | 接続・認証確認を促す |
| 最適化失敗 | `optimize_route()` | `最適化に失敗しました` | データ確認を促す |

### 6.2 エラーメッセージ設計

**基本フォーマット**:
```
❌ エラー: [エラー内容]
💡 [対処法]
```

## 7. セキュリティ設計

### 7.1 APIキー管理

**.envファイル**:
```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

**.env.example（テンプレート）**:
```
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

**.gitignore**:
```
.env
```

### 7.2 入力検証

- 駅名: 空文字チェック（関数内で実施）
- キーワード: 空文字チェック（関数内で実施）
- 座標: データクラスの`__post_init__`で範囲チェック

## 8. パフォーマンス設計

### 8.1 処理時間目標

| 処理 | 目標時間 |
|------|----------|
| 駅の検索 | 1秒以内 |
| 店舗検索 | 3秒以内 |
| 距離行列計算 | 5秒以内 |
| TSP最適化 | 30秒以内 |
| 地図描画 | 2秒以内 |
| **合計** | **45秒以内** |

### 8.2 最適化手法

- Distance Matrix APIは1回の呼び出しで全距離を取得（11x11行列）
- Python-MIPのCBCソルバー使用（10地点のTSPは高速に厳密解を計算可能）

## 9. テスト設計

### 9.1 テストシナリオ

**正常系**:
1. 新宿駅 + カフェ
2. 渋谷駅 + コンビニ
3. 鎌倉駅 + 観光地

**異常系**:
1. 存在しない駅名
2. 検索結果0件のキーワード
3. APIキー未設定

## 10. 運用設計

### 10.1 初期セットアップ

1. uvで仮想環境を構築
2. `uv pip install -r requirements.txt`
3. `.env`ファイル作成とAPIキー設定
4. Jupyter Notebook起動
5. `notebooks/main.ipynb`を開く

### 10.2 使用方法

1. セル1〜6を順番に実行（関数定義）
2. セル7のパラメータ（`STATION_NAME`, `KEYWORD`）を編集
3. セル7を実行

## 11. 依存パッケージ

```txt
# requirements.txt
python-dotenv==1.0.0
googlemaps==4.10.0
numpy==1.24.3
pandas==2.0.3
mip==1.15.0
ipyleaflet==0.17.3
ipywidgets==8.1.0
jupyter==1.0.0
```

## 12. 今後の拡張可能性

1. **パラメータのUI化**: ipywidgetsでインタラクティブな入力フォーム
2. **複数ルート比較**: 最適解以外の候補も表示
3. **訪問店舗数の可変化**: 10件以外も指定可能に
4. **結果のエクスポート**: CSV、PDF出力機能

## 13. 付録

### 13.1 用語集

| 用語 | 説明 |
|------|------|
| TSP | 巡回セールスマン問題 |
| MTZ制約 | Miller-Tucker-Zemlin制約（部分巡回路除去） |
| MIP | 混合整数計画法 |

---

**文書履歴**

| 版 | 日付 | 作成者 | 変更内容 |
|----|------|--------|----------|
| 1.0 | 2025-11-07 | Claude Code | 初版作成 |
| 2.0 | 2025-11-07 | Claude Code | Jupyter Notebook単一ファイル構成に変更 |
