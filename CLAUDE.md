# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

データ分析/機械学習プロジェクト。uvを使用した依存関係管理。

## 開発環境のセットアップ

### 初回セットアップ
```bash
# uv環境の初期化
uv venv
# 仮想環境の有効化 (Windows)
.venv\Scripts\activate
# または (Unix/Mac)
source .venv/bin/activate

# 依存関係のインストール
uv pip install -r requirements.txt
```

### 依存関係の管理
```bash
# 新しいパッケージの追加
uv pip install <package-name>

# requirements.txtへの書き出し
uv pip freeze > requirements.txt

# 開発用パッケージの追加 (requirements-dev.txtがある場合)
uv pip install -r requirements-dev.txt
```

## テスト実行

```bash
# 全テストの実行 (pytestを使用する場合)
pytest

# 特定のテストファイルの実行
pytest tests/test_specific.py

# 特定のテスト関数の実行
pytest tests/test_specific.py::test_function_name

# カバレッジ付きテスト実行
pytest --cov=. --cov-report=html
```

## コード品質管理

```bash
# Ruffによるlint実行 (設定されている場合)
ruff check .

# Ruffによる自動修正
ruff check --fix .

# 型チェック (mypyを使用する場合)
mypy .
```

## Jupyter Notebook

```bash
# Jupyter Labの起動
jupyter lab

# Jupyter Notebookの起動
jupyter notebook
```

## プロジェクト構造のガイドライン

### ディレクトリ構成
- `data/`: データセット (生データ、処理済みデータ)
- `notebooks/`: Jupyter Notebook (.ipynb)
- `src/`: ソースコード (モジュール、ユーティリティ)
- `tests/`: テストコード
- `models/`: 学習済みモデル
- `scripts/`: 実行スクリプト

### コーディング規約
- Python標準スタイルガイド (PEP 8) に準拠
- 関数・クラスには型ヒント (`typing` モジュール) を使用
- ドキュメント文字列 (docstring) は NumPy/Google スタイルで記述

## データサイエンス開発のベストプラクティス

### Notebook開発
- 実験用Notebookは `notebooks/exploratory/` に配置
- 再利用可能なコードはモジュール化して `src/` に移動
- Notebookは定期的にクリーンアップして実行可能な状態を維持

### 再現性の確保
- 乱数シードは明示的に設定
- データの前処理パイプラインはスクリプト化
- 依存関係のバージョンは `requirements.txt` で固定

### モデル管理
- 学習済みモデルはバージョン管理 (ファイル名に日付やタグを含める)
- モデルの評価指標は記録して比較可能にする
