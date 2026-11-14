# Evidence Log Inspector

**JSONLイベントログの連番欠落、不正な状態遷移、根拠不足や未完了状態を、元ログを変更せず検査するCLIツールです。**

**v0.1.0 · 実験版 · Python 3.11以降 · 標準ライブラリのみ · MIT**

[English](README.md) | **日本語**

## 何を解決するツールか

JSONの構文が正しくても、ログが示す出来事の順序や状態が整合しているとは限りません。イベントの欠落、結果不明（`UNKNOWN`）から解決根拠なしで完了（`COMPLETED`）した記録、完了に必要な証拠の不足などが起こり得ます。

Evidence Log Inspector（ELI）は、こうした問題を**明示したイベント規則と照合する、無料・読取り専用のローカル検証ツール**です。ログの欠落を補完したり、記録内容が現実に起きたと証明したりすることはできません。

## 主な検査項目

| 検査 | 発見できる問題の例 |
| --- | --- |
| ストリーム別の連番 | 連番の欠番、重複、逆行 |
| 操作別の状態遷移 | `UNKNOWN → COMPLETED`への直接遷移 |
| 証拠・完了条件 | `RESOLVED`の証拠ID不足、`COMPLETED`の`result: true`不足 |
| 終端状態 | `HOLD`や`COMPLETED`に至らない未完了操作 |
| JSONLの形式 | 重複JSONキー、壊れたJSON、未知のバージョンや規則 |
| 外部ハッシュ | 事前に保持した信頼できるSHA-256と入力が一致しない |

連番の判定単位は**ストリーム**、操作状態の単位は**（ストリームID、操作ID）の組**です。規則は厳格化できますが、`UNKNOWN`の安全条件を緩和できません。[イベント規則](EVENT_RULES.md)に詳細があります。

## クイックスタート

**必要環境：** Python 3.11以降。外部サービスや追加のPythonパッケージは不要です。

リポジトリのルートから、同梱の**合成ログ**で試します。出力先は毎回新しいディレクトリ名にしてください。

```sh
python eli.py --log samples/normal.jsonl --policy samples/policy.json --out example-normal
python eli.py --log samples/unsafe.jsonl --policy samples/policy.json --out example-unsafe
python eli.py --log samples/hold.jsonl --policy samples/policy.json --out example-hold
```

Windowsでは必要に応じて`python`を`py -3`に置き換えてください。2番目のコマンドは意図的に不正なログを検出するため**終了コード1**が期待値です。既存の出力先は上書きせず拒否します。

各実行で出力先に`report.json`と`findings.csv`を保存します。ターミナルにも診断JSONを表示します。入力ログは編集・修正しません。

## 診断結果の読み方

同梱の合成データによる独立実行で、次の判定を確認しています。

| 入力 | 判定 | 終了コード | 意味 |
| --- | --- | ---: | --- |
| `normal.jsonl` | `CONSISTENT_WITH_POLICY` | `0` | 宣言した規則と整合 |
| `unsafe.jsonl` | `VIOLATION` | `1` | 不正な`UNKNOWN → COMPLETED`を検出 |
| `hold.jsonl` | `HOLD` | `0` | 適切に保留。**業務処理の成功ではない** |
| 未完了・未知イベント | `UNVERIFIABLE` | `2` | 信頼できる判定が不可能 |

意図的な不正ログを`VIOLATION`として検出したテストが合格しても、**不正ログが安全だという意味ではありません**。終了コードだけで業務処理の成功と判断しないでください。

JSON・CSVの結果にはストリームID、操作ID、入力パス、連番や規則違反の根拠を記録しますが、任意のログ本文・URL・秘密情報は転載しません。それでもIDやパス自体が機密情報になり得ます。CSVでは表計算ソフトの数式として解釈される先頭文字をエスケープします。

## ポリシーとハッシュの意味

[サンプルポリシー](samples/policy.json)では、8つの論理フィールド（`stream_id`、`sequence`、`event_type`、`operation_id`、`log_version`、`result`、`evidence`、`timestamp`）をイベントのトップレベル項目に割り当て、連番の開始値・時刻比較の範囲・状態遷移を指定します。

既定の状態遷移は次のとおりです。

```text
STARTED → RETRY / UNKNOWN / COMPLETED / HOLD
RETRY   → RETRY / UNKNOWN / COMPLETED / HOLD
UNKNOWN → RESOLVED / HOLD
RESOLVED → COMPLETED / HOLD
COMPLETED、HOLD → 終端
```

`RESOLVED`には空でない証拠IDが必要ですが、**参照先の証拠が実在・正確であるかまでは検証しません**。`same_clock=true`を指定した場合のみ、各ストリーム内の時刻の逆行を検査します。複数ホスト間の全順序は判定しません。

別途保管している**信頼できるSHA-256**と入力の全バイトを照合する場合：

```sh
python eli.py --log samples/normal.jsonl --policy samples/policy.json --out example-hash --expected-sha256 YOUR_TRUSTED_64_HEX_DIGEST
```

引数を省略すると`NOT_VERIFIED`です。ハッシュ一致は、**指定ハッシュと同じバイト列であること**しか意味しません。記録の完全性や真実性を証明するものではありません。同梱の`normal.sha256`は使用例であり、独立した信頼根拠ではありません。

## テスト・検証状況

FIX-01では**47件の自動テスト**（既存43件＋回帰4件）を備えます。5種類の入力を4方式で検証した比較実験（計20実行）では、定義した期待結果との一致はELI 5/5、固定Python基準4/5、基本的な`json.tool`・`jq`各1/5でした。ただし各方式の検査範囲が異なり、汎用OSSに対する優位性や工数削減を証明する結果ではありません。

GitHub Actionsでは**Ubuntu・Windows × Python 3.11／3.12／3.13の6環境**を設定しています。実際の成功状況は[Actions画面](https://github.com/KenKan964/evidence-log-inspector/actions)で確認してください。`evidence/ci_status.json`の`NOT_RUN`は**リポジトリ作成前の履歴記録**であり、現在のCI状態ではありません。

```sh
python -m unittest discover -s tests -v
python compare.py > comparison-local.json
```

ケース別の証拠を保存するときは、**未使用の`ELI_EVIDENCE`出力先**を指定します。既存ファイルやsymlinkと衝突した場合は、上書きせずテストを失敗させます。

```sh
ELI_EVIDENCE=acceptance-new python -m unittest discover -s tests -v
```

PowerShellでは事前に`$env:ELI_EVIDENCE='acceptance-new'`を設定してください。

## 安全上の注意と制約

- JSONLの**読取り専用検査**です。欠落イベントを追加したり、ログを修復したりしません。
- 監査証跡の真正性、未記録イベントの不存在、署名や証拠保全手続の完全性を保証しません。
- 1回に1ファイルを検査します。同じファイル内で複数ストリームを扱えますが、複数ファイルの連続性や複数ホストの全順序は推定しません。
- 未知・未対応のルールやイベントを安全と見なさず、`UNVERIFIABLE`で扱います。
- 1行65,536バイト、物理行10,000、全体10MB、JSON入れ子32などの上限があります。読取りが途中で止まった場合は全ファイルのハッシュ一致を主張しません。
- 同一権限の悪意あるプロセスによるファイル競合や同時変更への完全な隔離はありません。操作権限のある安定したディレクトリで試験し、実ログと結果を保護してください。

## 関連資料・ライセンス

[English README](README.md) · [イベント規則](EVENT_RULES.md) · [技術仕様](TECHNICAL_SPEC.md) · [セキュリティ](SECURITY.md) · [OSS比較](OSS_COMPARISON.md) · [FIX-01の差分](FIX01_CHANGES.md) · [開発報告](REPORT_ja.md) · [変更履歴](CHANGELOG.md) · [MITライセンス](LICENSE)

**ライセンス：** MIT · Copyright © 2026 KenKan964.
