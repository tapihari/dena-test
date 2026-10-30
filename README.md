# dena-test

レシピを作成・取得・更新・削除する REST API です。

- 公開URL: https://dena-test.onrender.com
- リポジトリ: https://github.com/tapihari/dena-test

## 構成

```
クライアント
   |  HTTPS
   v
Render (Web Service / Singapore)
   FastAPI + uvicorn
   |  MySQL over TLS
   v
Aiven for MySQL (Free plan)
   recipes テーブル
```

| 項目 | 内容 |
|---|---|
| 言語 | Python 3.12 |
| フレームワーク | FastAPI |
| アプリサーバー | uvicorn |
| DB | MySQL (Aiven for MySQL) |
| DBドライバ | PyMySQL |
| ホスティング | Render |

## API仕様

ステータスコードは定義済みのエンドポイントではすべて `200` を返し、成功・失敗はレスポンスの `message` で区別します。定義外のパスやメソッドには `404` を返します。

| メソッド | パス | 内容 |
|---|---|---|
| POST | `/recipes` | レシピを作成 |
| GET | `/recipes` | レシピ一覧を取得 |
| GET | `/recipes/{id}` | 指定したレシピを取得 |
| PATCH | `/recipes/{id}` | 指定したレシピを更新 |
| DELETE | `/recipes/{id}` | 指定したレシピを削除 |

### POST /recipes

リクエスト（全項目必須）

```json
{
  "title": "トマトスープ",
  "making_time": "15分",
  "serves": "5人",
  "ingredients": "玉ねぎ, トマト, スパイス, 水",
  "cost": 450
}
```

成功

```json
{
  "message": "Recipe successfully created!",
  "recipe": [
    {
      "id": 3,
      "title": "トマトスープ",
      "making_time": "15分",
      "serves": "5人",
      "ingredients": "玉ねぎ, トマト, スパイス, 水",
      "cost": 450,
      "created_at": "2026-10-30 11:58:34",
      "updated_at": "2026-10-30 11:58:34"
    }
  ]
}
```

失敗（必須項目が欠けている場合）

```json
{
  "message": "Recipe creation failed!",
  "required": "title, making_time, serves, ingredients, cost"
}
```

### GET /recipes

```json
{
  "recipes": [
    { "id": 1, "title": "チキンカレー", "making_time": "45分", "serves": "4人", "ingredients": "玉ねぎ,肉,スパイス", "cost": 1000 }
  ]
}
```

### GET /recipes/{id}

```json
{
  "message": "Recipe details by id",
  "recipe": [
    { "id": 1, "title": "チキンカレー", "making_time": "45分", "serves": "4人", "ingredients": "玉ねぎ,肉,スパイス", "cost": 1000 }
  ]
}
```

### PATCH /recipes/{id}

送信した項目のみ更新します。

```json
{
  "message": "Recipe successfully updated!",
  "recipe": [
    { "title": "トマトスープ", "making_time": "15分", "serves": "5人", "ingredients": "玉ねぎ, トマト, スパイス, 水", "cost": 500 }
  ]
}
```

### DELETE /recipes/{id}

```json
{ "message": "Recipe successfully removed!" }
```

### 対象のレシピが存在しない場合（GET / PATCH / DELETE）

```json
{ "message": "No recipe found" }
```

## ローカルでの起動

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`.env` を作成し、DBの接続情報を記載します（`.env` は Git の管理対象外です）。

```
DB_HOST=<ホスト>
DB_PORT=<ポート>
DB_USER=<ユーザー>
DB_PASSWORD=<パスワード>
DB_NAME=<データベース名>
```

テーブルと初期データを作成し、サーバーを起動します。

```bash
mysql -h <ホスト> -P <ポート> -u <ユーザー> -p --ssl-mode=REQUIRED <データベース名> < sql/create.sql
uvicorn main:app --reload
```

## デプロイ

Render の Web Service に以下を設定しています。`main` ブランチへの push で自動デプロイされます。

| 項目 | 値 |
|---|---|
| Region | Singapore |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Environment Variables | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |

## 設計上の判断

- **DBに外部の MySQL を採用**: 提供された `sql/create.sql` は MySQL 構文のため、無変更で利用できるよう Aiven for MySQL を使用しました。Render の無料枠はファイルシステムが揮発性のため、SQLite ではなくアプリと分離した DB にすることで、再起動やデプロイでデータが失われない構成にしています。
- **接続情報は環境変数で管理**: パスワード等はコードやリポジトリに含めず、ローカルは `.env`、Render は環境変数から読み込みます。DB との通信は TLS を必須としています。
- **リージョン**: アプリ（Render）を DB（Aiven、アジア）に近い Singapore に配置し、応答時間を抑えています。
- **ステータスコードとエラー形式**: 仕様に合わせ、必須項目の欠落でも FastAPI の自動 `422` を返さないよう、入力は任意項目として受け取りアプリ側で検証しています。未定義メソッドの `405` も `404` に統一しています。
- **PATCH の存在確認**: MySQL は値が変わらない UPDATE を影響行数 0 と数えるため、更新前に SELECT で存在を確認しています。
- **更新日時**: `updated_at` は `create.sql` の `ON UPDATE CURRENT_TIMESTAMP` により DB 側で自動更新されます。日時は DB のタイムゾーン（UTC）で記録されます。