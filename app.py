"""
店舗巡回ルート最適化Webアプリケーション
Streamlit版
"""
import os
import streamlit as st
from dotenv import load_dotenv
import googlemaps
import numpy as np
import pandas as pd
import mip
from dataclasses import dataclass
from typing import List, Tuple, Optional

# 環境変数の読み込み
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="店舗巡回ルート最適化",
    page_icon="🗺️",
    layout="wide"
)

# タイトル
st.title("🗺️ 店舗巡回ルート最適化アプリ")
st.markdown("駅周辺の店舗を検索し、最適な巡回ルートを計算します")

# 設定
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
TRAVEL_MODE = "walking"
WALKING_SPEED_KM_H = 4.0

# APIキーの検証
if not GOOGLE_MAPS_API_KEY:
    st.error("❌ GOOGLE_MAPS_API_KEYが設定されていません。.envファイルを確認してください。")
    st.stop()

# Google Maps クライアント初期化
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


# データモデル
@dataclass
class Location:
    """位置情報を表すクラス"""
    lat: float
    lng: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lng)


@dataclass
class Place:
    """店舗情報を表すクラス"""
    place_id: str
    name: str
    address: str
    location: Location
    distance_from_station: Optional[float] = None


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
    places: List[Place]
    total_distance: float
    segment_distances: List[float]

    @property
    def estimated_time(self) -> float:
        """推定所要時間（分）"""
        return (self.total_distance / 1000) / WALKING_SPEED_KM_H * 60


# 関数定義
def search_station(station_name: str) -> Station:
    """駅名から駅の位置情報を取得"""
    try:
        result = gmaps.geocode(address=station_name, language="ja")
        if not result:
            raise ValueError(f"'{station_name}' に該当する駅が見つかりませんでした")

        location_data = result[0]["geometry"]["location"]
        location = Location(lat=location_data["lat"], lng=location_data["lng"])
        return Station(name=station_name, location=location)
    except Exception as e:
        raise ValueError(f"駅の検索中にエラーが発生しました: {e}")


def search_nearby_places(station: Station, keyword: str, max_results: int = 5) -> List[Place]:
    """駅周辺の店舗を検索"""
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

        return places
    except Exception as e:
        raise ValueError(f"店舗検索中にエラーが発生しました: {e}")


def calculate_distance_matrix(station: Station, places: List[Place]) -> np.ndarray:
    """駅と全店舗間の距離行列を計算（分割リクエスト対応）"""
    locations = [station.to_tuple()] + [place.location.to_tuple() for place in places]
    num_locations = len(locations)
    distance_matrix = np.zeros((num_locations, num_locations))
    BATCH_SIZE = 25

    try:
        for i_start in range(0, num_locations, BATCH_SIZE):
            i_end = min(i_start + BATCH_SIZE, num_locations)
            origins_batch = locations[i_start:i_end]

            for j_start in range(0, num_locations, BATCH_SIZE):
                j_end = min(j_start + BATCH_SIZE, num_locations)
                destinations_batch = locations[j_start:j_end]

                result = gmaps.distance_matrix(
                    origins=origins_batch,
                    destinations=destinations_batch,
                    mode=TRAVEL_MODE,
                    language="ja",
                    units="metric"
                )

                for i_local, i_global in enumerate(range(i_start, i_end)):
                    for j_local, j_global in enumerate(range(j_start, j_end)):
                        if i_global == j_global:
                            distance_matrix[i_global][j_global] = 0
                        else:
                            element = result["rows"][i_local]["elements"][j_local]
                            if element["status"] == "OK":
                                distance_matrix[i_global][j_global] = element["distance"]["value"]
                            else:
                                distance_matrix[i_global][j_global] = 999999

        for idx, place in enumerate(places, 1):
            place.distance_from_station = distance_matrix[0][idx]

        return distance_matrix
    except Exception as e:
        raise ValueError(f"距離計算中にエラーが発生しました: {e}")


def optimize_route(station: Station, places: List[Place], distance_matrix: np.ndarray) -> Route:
    """
    TSPとして最適ルートを計算（Python-MIPによる数理最適化）

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

    # 求解（最大30秒）
    OPTIMIZATION_TIME_LIMIT = 30
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
    optimized_places = [places[i-1] for i in visit_order[1:]]  # 駅を除く

    # 各区間の距離を計算
    segment_distances = []
    for i in range(len(visit_order) - 1):
        segment_distances.append(distance_matrix[visit_order[i]][visit_order[i+1]])

    # 最後: 最終店舗から駅への距離
    segment_distances.append(distance_matrix[visit_order[-1]][0])

    total_distance = sum(segment_distances)

    # 最後の店舗から駅への距離は除外（表示用）
    segment_distances_without_return = segment_distances[:-1]

    return Route(
        station=station,
        places=optimized_places,
        total_distance=total_distance,
        segment_distances=segment_distances_without_return
    )


def generate_google_maps_url(station: Station, places: List[Place], route_order: Optional[List[Place]] = None) -> str:
    """Google Maps URLを生成"""
    origin = f"{station.location.lat},{station.location.lng}"

    if route_order:
        waypoints = "|".join([f"{p.location.lat},{p.location.lng}" for p in route_order])
        destination = origin
    else:
        if len(places) > 0:
            waypoints = "|".join([f"{p.location.lat},{p.location.lng}" for p in places[:-1]])
            destination = f"{places[-1].location.lat},{places[-1].location.lng}"
        else:
            waypoints = ""
            destination = origin

    base_url = "https://www.google.com/maps/dir/"

    if waypoints:
        url = f"{base_url}?api=1&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode={TRAVEL_MODE}"
    else:
        url = f"{base_url}?api=1&origin={origin}&destination={destination}&travelmode={TRAVEL_MODE}"

    return url


# UI
st.sidebar.header("📋 検索条件")

station_name = st.sidebar.text_input("駅名", value="金山駅", help="検索したい駅名を入力してください")
keyword = st.sidebar.text_input("検索キーワード", value="手羽先", help="検索したい店舗のキーワードを入力してください")
max_results = st.sidebar.slider("最大検索結果数", min_value=3, max_value=10, value=5, help="検索する店舗の最大数")

search_button = st.sidebar.button("🔍 検索・最適化実行", type="primary")

# メインエリア
if search_button:
    if not station_name or not keyword:
        st.warning("⚠️ 駅名とキーワードを入力してください")
    else:
        try:
            with st.spinner("処理中..."):
                # 1. 駅の検索
                st.info("📍 駅を検索中...")
                station = search_station(station_name)
                st.success(f"✅ 駅の位置情報取得完了: {station.location.lat:.6f}, {station.location.lng:.6f}")

                # 2. 店舗の検索
                st.info(f"🏪 '{keyword}' を検索中...")
                places = search_nearby_places(station, keyword, max_results)
                st.success(f"✅ {len(places)}件の店舗を取得しました")

                # 検索結果の表示
                st.subheader("📊 検索結果（駅から近い順）")
                df_search = pd.DataFrame([
                    {
                        "番号": idx,
                        "店舗名": place.name,
                        "住所": place.address
                    }
                    for idx, place in enumerate(places, 1)
                ])
                st.dataframe(df_search, use_container_width=True)

                # 3. 距離行列の計算
                st.info("📏 距離行列を計算中...")
                distance_matrix = calculate_distance_matrix(station, places)
                st.success(f"✅ 距離行列計算完了 ({len(distance_matrix)}x{len(distance_matrix)})")

                # 距離行列の表示
                st.subheader("📏 地点間の距離行列（メートル）")

                # 行ラベル（店舗名付き）、列ラベル（番号のみ）を作成
                row_labels = [f"{station.name}（駅）"] + [f"{i}. {place.name}" for i, place in enumerate(places, 1)]
                col_labels = ["駅"] + [f"{i}" for i in range(1, len(places) + 1)]

                # DataFrameを作成（距離をメートル単位で表示）
                df_distance_matrix = pd.DataFrame(
                    distance_matrix,
                    index=row_labels,
                    columns=col_labels
                )

                # 整数に変換して見やすくする
                df_distance_matrix = df_distance_matrix.astype(int)

                st.dataframe(df_distance_matrix, use_container_width=True)
                st.caption("💡 表の各セルは、行の地点から列の地点への徒歩距離（メートル）を示しています。列の番号は検索結果の番号に対応しています。")

                # 検索結果の地図URL
                map_url_search = generate_google_maps_url(station, places)
                st.markdown(f"🗺️ [検索結果の地図をGoogle Mapsで開く]({map_url_search})")

                # 4. ルートの最適化
                st.info("🔧 最適ルートを計算中...")
                route = optimize_route(station, places, distance_matrix)
                st.success("✅ 最適化完了")

                # ルート詳細の表示
                st.subheader("📊 最適ルート詳細")

                # サマリー
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("総移動距離", f"{route.total_distance:.0f}m ({route.total_distance/1000:.2f}km)")
                with col2:
                    st.metric("推定所要時間", f"{route.estimated_time:.1f}分")
                with col3:
                    st.metric("訪問店舗数", f"{len(route.places)}件")

                # ルート詳細テーブル
                cumulative_distance = 0
                route_data = []
                for i, place in enumerate(route.places, 1):
                    segment_dist = route.segment_distances[i-1]
                    cumulative_distance += segment_dist
                    route_data.append({
                        "訪問順": i,
                        "店舗名": place.name,
                        "前地点からの距離": f"{segment_dist:.0f}m",
                        "累積距離": f"{cumulative_distance:.0f}m"
                    })

                df_route = pd.DataFrame(route_data)
                st.dataframe(df_route, use_container_width=True)

                # 最適ルートの地図URL
                map_url_route = generate_google_maps_url(route.station, route.places, route_order=route.places)
                st.markdown(f"🗺️ [最適ルートをGoogle Mapsで開く]({map_url_route})")

                st.balloons()

        except ValueError as e:
            st.error(f"❌ エラー: {e}")
        except Exception as e:
            st.error(f"❌ 予期しないエラー: {e}")
            import traceback
            st.code(traceback.format_exc())

else:
    st.info("👈 左のサイドバーから駅名とキーワードを入力して、検索・最適化を実行してください")

# フッター
st.markdown("---")
st.markdown("""
### 💡 使い方
1. 左のサイドバーから**駅名**を入力（例: 金山駅、新宿駅）
2. **検索キーワード**を入力（例: 手羽先、ラーメン、カフェ）
3. **最大検索結果数**をスライダーで調整
4. 「🔍 検索・最適化実行」ボタンをクリック
5. 結果の地図URLをクリックしてブラウザで確認

### 🔧 技術スタック
- **Google Maps API**: 駅・店舗検索、距離計算
- **Python-MIP**: TSP（巡回セールスマン問題）の数理最適化
- **Streamlit**: Webアプリケーションフレームワーク
""")
