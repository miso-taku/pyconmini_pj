# 店舗巡回ルート最適化アプリケーション

駅周辺の店舗を検索し、最適な巡回ルートを数理最適化（TSP: 巡回セールスマン問題）で計算するJupyter Notebookアプリケーションです。

## 機能

- **駅周辺の店舗検索**: Google Places APIを使用して、指定した駅の周辺から店舗を検索（近い順に10件）
- **検索結果の可視化**: 表形式と地図で検索結果を表示
- **距離行列の計算**: Google Maps Distance Matrix APIで徒歩経路の実距離を計算
- **最適ルート計算**: Python-MIPを使用したTSP最適化により、最短巡回ルートを計算
- **ルートの可視化**: 最適ルートを地図上に表示し、詳細情報を表形式で提供

## 技術スタック

- **言語**: Python 3.10以上
- **実行環境**: Jupyter Notebook
- **パッケージマネージャー**: uv
- **主要ライブラリ**:
  - `googlemaps`: Google Maps API クライアント
  - `mip`: Python-MIP（数理最適化）
  - `ipyleaflet`: インタラクティブ地図表示
  - `pandas`, `numpy`: データ処理

## セットアップ

### 1. 前提条件

- Python 3.10以上がインストールされていること
- uvがインストールされていること
- Google Cloud Platformアカウント
- Google Maps APIキー（以下のAPIを有効化）:
  - Geocoding API
  - Places API
  - Distance Matrix API

### 2. uvのインストール（未インストールの場合）

```bash
# Windowsの場合
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linuxの場合
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. プロジェクトのセットアップ

```bash
# リポジトリのクローン（またはダウンロード）
cd pyconmini_pj

# uv環境の初期化
uv venv

# 仮想環境の有効化
# Windowsの場合:
.venv\Scripts\activate
# macOS/Linuxの場合:
source .venv/bin/activate

# 依存パッケージのインストール
uv pip install -r requirements.txt
```

### 4. APIキーの設定

```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

### 5. Jupyter Notebookの起動

```bash
jupyter notebook
```

ブラウザが開いたら、`notebooks/main.ipynb`を開きます。

## 使い方

1. **関数の定義**: セル1〜6を順番に実行して、必要な関数を定義します
2. **パラメータの設定**: セル7の以下のパラメータを編集します
   ```python
   STATION_NAME = "新宿駅"      # 駅名
   KEYWORD = "カフェ"            # 検索キーワード
   ```
3. **実行**: セル7を実行すると、以下の処理が順番に実行されます
   - 駅の検索
   - 店舗の検索
   - 検索結果の表示（表 + 地図）
   - 距離行列の計算
   - 最適ルートの計算
   - 最適ルートの表示（表 + 地図）

## プロジェクト構成

```
pyconmini_pj/
├── .env                    # APIキー設定（gitignore対象）
├── .env.example            # APIキー設定テンプレート
├── .gitignore
├── requirements.txt        # 依存パッケージ
├── README.md               # 本ファイル
├── CLAUDE.md              # Claude Code用設定
├── docs/
│   ├── requirements.md     # 要求定義書
│   └── design.md           # 詳細設計書
└── notebooks/
    └── main.ipynb          # メインノートブック
```

## Notebookセル構成

| セル | 内容 |
|------|------|
| セル1 | ライブラリインポート・設定・APIキー読み込み |
| セル2 | データモデル定義（Location, Place, Station, Route） |
| セル3 | 店舗検索関数 |
| セル4 | 距離計算関数 |
| セル5 | ルート最適化関数（TSP） |
| セル6 | 可視化関数（地図・表） |
| セル7 | メイン実行 |

## TSP最適化について

本アプリケーションでは、巡回セールスマン問題（TSP）として最適ルートを計算しています。

- **目的**: 駅から出発し、全店舗を1回ずつ訪問して駅に戻る最短経路を求める
- **手法**: Python-MIPによる混合整数計画法（MIP）
- **制約**: MTZ制約により部分巡回路を除去
- **計算時間**: 10地点程度であれば30秒以内に厳密解を計算可能

## トラブルシューティング

### APIキーエラー

```
❌ GOOGLE_MAPS_API_KEYが設定されていません
```

→ `.env`ファイルにAPIキーが正しく設定されているか確認してください

### 駅が見つからない

```
❌ エラー: '新宿' に該当する駅が見つかりませんでした
```

→ 駅名を正確に入力してください（例: 「新宿駅」）

### 店舗が見つからない

```
❌ エラー: 'カフェ' に該当する店舗が見つかりませんでした
```

→ 検索キーワードを変更してください（店舗名または業種）

### API利用制限

Google Maps APIには無料枠があります。利用量が多い場合は、Google Cloud Platformのコンソールで利用状況を確認してください。

## 制約事項

- 検索結果は10件固定
- 移動手段は徒歩のみ
- リアルタイムの交通状況は考慮されない
- Google Maps APIの無料枠内での利用を想定

## 今後の拡張案

- 訪問店舗数の可変化
- 複数の移動手段対応（自転車、車など）
- 営業時間の考慮
- ルート結果のエクスポート機能（CSV、PDF）
- パラメータのUI化（ipywidgetsによる入力フォーム）

## ライセンス

本プロジェクトは教育・個人利用を目的としています。

## 参考資料

- [Google Maps Platform Documentation](https://developers.google.com/maps/documentation)
- [Python-MIP Documentation](https://www.python-mip.com/)
- [ipyleaflet Documentation](https://ipyleaflet.readthedocs.io/)

## 開発者向け情報

詳細な仕様については、`docs/`ディレクトリ内のドキュメントを参照してください。

- `docs/requirements.md`: 要求定義書
- `docs/design.md`: 詳細設計書
