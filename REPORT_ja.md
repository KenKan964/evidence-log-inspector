# ELI-DEV-001 / FIX-01是正報告 2026-11-14

FIX-01-01〜03を実装・検証し、独立再審査へ提出する。
Python3.13.5と3.12.14で各47/47成功、skip0。既存43件の期待値を変更せず回帰4件を追加。
テストログevidence/tests313.log, tests312.logと各ケースJSONを収録。

## 独立検証指摘との対応

証拠上書きは排他新規作成に変更。競合やsymlinkは例外で試験非ゼロ終了、スキップ合格にしない。
旧版全discoverではmarkerを書換えたまま43件PASS、修正版全discoverではmarkerを守って非ゼロ終了。
実際の前後hash、終了値、stdout/stderrをbefore_conflict/after_conflictに保存。
通常の新規先では証拠を保存して全件PASS。ELI_EVIDENCE未設定の通常実行を「証拠出力済み」とは扱わない。

重複キーfixtureを必須フィールド欠落のない合法な系列へ変更。
同じ入力に対しELIはINVALID_JSONLで拒否、Python基準はaccepted=true。
比較20実行: ELI5/5、Python4/5、json.tool1/5、jq基本1/5期待一致。
旧Python5/5の数値は今回実測へ置換。パース方式の検査範囲を超える評価はしない。

## 退行・安全

eli.pyは原版とバイト一致。CLI実行で正常CONSISTENT_WITH_POLICY/0、危険UNKNOWN確定VIOLATION/1、
合法HOLD/0、未知型と未完了UNVERIFIABLE/2を確認しcli_checks.jsonへ保存。
NOT_VERIFIED/MISMATCH、入力不変、CSV式開始文字エスケープ等も既存試験で維持。
証拠ファイル保存の排他化は既存証拠の再利用を意図的に失敗させる。
既存ログや証拠を削除する機能は追加しない。匿名合成データだけで試験。

6環境CIは全件NOT_RUN。独立受入後のprivateリポジトリ登録・CI実行待ちとして記録。
run/job IDはnull。ローカル結果をCI成功へ読み替えない。GitHub公開HOLD。
OSS一般への優位、工数削減率・ROI・需要は未実証。
修正差分はFIX01.patch。両内包ZIPのMANIFEST.sha256は最終ファイル全件を自身を除いて再生成・照合。
