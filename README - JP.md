# Resume Agent (RA)

Resume Agent（RA）は、採用担当者による求人情報の整理、履歴書の解析、候補者と求人のマッチング評価、および候補者能力の発見を支援するAI活用型の履歴書選考システムです。

現在のシステムは、以下の構成で動作します。

- FastAPI バックエンド
- Vue 3 フロントエンド
- SQLite データベース
- Alembic マイグレーション
- OpenAI互換 LLM API
- PDF履歴書の解析・保存
- 中国語・日本語・英語対応

## 1. 主な機能

現在のRAでは、以下の機能を提供しています。

- ユーザーログイン・セッション認証
- Job Description（JD）の作成・AI解析
- PDF履歴書のアップロード・構造化解析
- 候補者管理
- 求人と候補者のマッチング評価
- Talent Discovery
- AIによる能力発見
- HR指定能力による評価
- 元履歴書の閲覧
- 多言語対応
  - 簡体字中国語
  - 日本語
  - 英語

## 2. 動作環境

### Python

推奨環境：

```text
Python 3.10
```

現在の開発・動作確認済み環境：

```text
Python 3.10.20
```

RAの実際の開発環境ではCondaを使用しています。

Condaは必須ではありませんが、開発環境を再現する場合はCondaの使用を推奨します。

### Node.js

以下を使用してください。

```text
Node.js 22.12.0 以上
```

現在の `package-lock.json` に含まれる依存関係では、Node.js 22.12.0以上を推奨します。

### OS

主にWindows環境で開発・動作確認しています。

以下のコマンド例はWindows PowerShellを前提としています。

## 3. プロジェクト構成

```text
resume_agent_manual/
├─ backend/                 FastAPI バックエンド
│  ├─ api/                  APIルート
│  ├─ app/                  FastAPIアプリケーション
│  ├─ clients/              LLMなど外部サービスクライアント
│  ├─ repositories/         データアクセス層
│  ├─ services/             ビジネスロジック
│  ├─ scripts/              管理用スクリプト
│  ├─ tests/                バックエンドテスト
│  ├─ alembic/              DBマイグレーション
│  ├─ requirements.txt      Python依存関係
│  └─ alembic.ini
│
├─ frontend/                Vueフロントエンド
│  ├─ src/
│  ├─ package.json
│  └─ package-lock.json
│
├─ data/                    実行時データ
│  ├─ avatars/
│  └─ resumes/
│
├─ docs/                    プロジェクト関連ドキュメント
├─ .env.example             環境変数テンプレート
└─ README.md
```

## 4. 初回セットアップ

### Step 1：リポジトリを取得

```powershell
git clone <repository-url>
cd resume_agent_manual
```

## 5. バックエンド環境構築

### Step 2：Python環境を作成

推奨Conda環境：

```powershell
conda create -n resume_agent_py310 python=3.10
conda activate resume_agent_py310
```

Pythonバージョンを確認します。

```powershell
python --version
```

以下のように表示されれば問題ありません。

```text
Python 3.10.x
```

### Step 3：Python依存関係をインストール

プロジェクトルートから実行します。

```powershell
python -m pip install -r .\backend\requirements.txt
```

## 6. 環境変数の設定

`.env.example` をコピーします。

```powershell
Copy-Item .\.env.example .\.env
```

その後、`.env` を編集してください。

主な設定例：

```env
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=
LLM_TIMEOUT=60

JD_USE_MOCK=false
RESUME_USE_MOCK=false
SCORING_USE_MOCK=false
TALENT_USE_MOCK=false
TRANSLATION_USE_MOCK=false

DATABASE_URL=sqlite+pysqlite:///./data/resume_agent.db
COOKIE_SECURE=false
```

実際のAPI KeyをGitへコミットしないでください。

### LLM設定について

RAではOpenAI Python SDKを使用し、OpenAI互換APIを呼び出します。

実際のAI処理を使用する場合、主に以下の設定が必要です。

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

以下の機能でLLMを使用します。

- JD解析
- 履歴書解析
- 求人マッチング評価
- Talent Discovery
- 翻訳

各機能の `*_USE_MOCK` を `true` に設定すると、該当機能でモックデータを使用できます。

デフォルトではモック機能は無効です。

LLM設定がない場合でもバックエンド自体は起動できますが、AI機能を実行した際にエラーになります。

## 7. データベース初期化

バックエンドディレクトリへ移動します。

```powershell
cd backend
```

Alembicマイグレーションを実行します。

```powershell
python -m alembic upgrade head
```

これにより、SQLiteデータベースと必要なテーブルが作成されます。

デフォルトのデータベース：

```text
data/resume_agent.db
```

SQLiteデータベースファイル自体をGitへ含める必要はありません。

## 8. 初期ユーザー作成

RAにはデフォルトのユーザー名・パスワードはありません。

DB初期化後、最初のユーザーを作成してください。

```powershell
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

実行後、パスワードを対話形式で2回入力します。

パスワードは8文字以上必要です。

基本形式：

```powershell
python .\scripts\manage_user.py create USERNAME [--display-name NAME] [--language zh-CN|ja-JP|en-US]
```

例：

```powershell
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

`--display-name` は任意です。

`--language` も任意で、デフォルトは以下です。

```text
zh-CN
```

## 9. バックエンド起動

`backend` ディレクトリで以下を実行します。

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 18000
```

バックエンド：

```text
http://127.0.0.1:18000
```

FastAPI Swagger UI：

```text
http://127.0.0.1:18000/docs
```

## 10. フロントエンド環境構築

別のPowerShellを開きます。

プロジェクトルートから以下を実行します。

```powershell
cd frontend
```

依存関係をインストールします。

```powershell
npm ci
```

本プロジェクトには `package-lock.json` があるため、fresh clone後は `npm ci` を推奨します。

続いてVueフロントエンドを起動します。

```powershell
npm run dev
```

フロントエンド：

```text
http://127.0.0.1:12140
```

ログイン画面：

```text
http://127.0.0.1:12140/login
```

## 11. ローカル開発時の構成

```text
Browser
   │
   ▼
Vue / Vite
127.0.0.1:12140
   │
   │ /api
   ▼
Vite Proxy
   │
   ▼
FastAPI
127.0.0.1:18000
   │
   ├─ SQLite
   ├─ Resume Storage
   └─ LLM API
```

フロントエンドからのAPIリクエストでは `/api/...` の相対パスを使用します。

Viteが以下へプロキシします。

```text
http://127.0.0.1:18000
```

そのため、通常のローカル開発では追加のCORS設定は不要です。

## 12. Cookie設定

ローカルHTTP環境では以下を使用してください。

```env
COOKIE_SECURE=false
```

HTTP環境で `COOKIE_SECURE=true` を設定すると、ログインAPI自体は成功しても、その後Cookieが送信されず、`401 Unauthorized` が発生する可能性があります。

HTTPS環境へ正式配置する場合は、通常：

```env
COOKIE_SECURE=true
```

を使用します。

## 13. 履歴書のアップロードと保存

現在のRAではPDF履歴書をサポートしています。

元PDFは以下へ保存されます。

```text
data/resumes/<candidate_id>/original.pdf
```

DBにはローカルPCの絶対パスではなく相対パスを保存します。

そのため、異なるPC間でもプロジェクト構造を維持できます。

アップロードされた履歴書はGitへコミットしません。

## 14. 実行時に生成されるファイル

通常、以下はGitへコミットしません。

```text
.env
data/resume_agent.db
data/*.db-wal
data/*.db-shm
data/resumes/
frontend/node_modules/
Python __pycache__/
```

以下はソースコードの引き渡し時に必要です。

```text
.env.example
backend/requirements.txt
backend/alembic/
backend/alembic.ini
frontend/package.json
frontend/package-lock.json
```

## 15. 初回動作確認

セットアップ完了後、以下の順番で確認してください。

1. FastAPIバックエンドを起動
2. Vueフロントエンドを起動
3. `http://127.0.0.1:12140/login` を開く
4. `manage_user.py` で作成したユーザーでログイン
5. JDを作成または解析
6. PDF履歴書をアップロード
7. 履歴書解析を実行
8. 求人マッチング評価を実行
9. Talent Discoveryを実行
10. 候補者詳細画面で結果を確認

実LLMを使用する場合、AI関連処理には有効なLLM設定が必要です。

## 16. よくある問題

### ログイン後に401になる

ローカルHTTP環境では以下を確認してください。

```env
COOKIE_SECURE=false
```

### AI機能でモデル設定エラーになる

以下を確認してください。

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
```

### フロントエンドが起動しない

Node.jsのバージョンを確認してください。

```powershell
node --version
```

Node.js 22.12.0以上を使用してください。

その後：

```powershell
npm ci
```

を実行してください。

### データベースが作成されていない

```powershell
cd backend
python -m alembic upgrade head
```

を実行してください。

### ログインユーザーが存在しない

```powershell
cd backend
python .\scripts\manage_user.py create japan_admin --display-name "Japan Admin" --language ja-JP
```

を実行してください。

## 17. 現在の対象範囲

現在のRAは、主にローカル環境・社内利用・プロジェクト検証を想定しています。

現在のリポジトリでは以下を提供しています。

- Viteベースのフロントエンド開発環境
- FastAPIバックエンド
- SQLiteデータベース
- LLM API連携

以下は現時点のプロジェクト対象外です。

- 本番用リバースプロキシ
- HTTPS終端設定
- Docker / Kubernetesなどのコンテナ運用
- 本番用フロントエンドホスティング
- クラウドインフラ構築