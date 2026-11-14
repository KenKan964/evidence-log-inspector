# Event rules v1

形式版: log_version="1"。規則版: eli-rules-v1。証拠版: eli-report-v1。
ポリシーはpolicy_version=1、rule_version、log_version、fields、sequence_start、same_clock、transitionsの厳密7項目。
fieldsはstream_id/sequence/event_type/operation_id/log_version/result/evidence/timestampの8名称を一対一に割当てる。
全フィールド名を設定するがresultはCOMPLETED時、evidenceはRESOLVED時、timestampはsame_clock時だけ必須。
IDは制御文字を含まない1〜128文字の文字列。sequenceはbool以外の0以上整数。
STARTEDから始め、COMPLETEDまたはHOLDで終わる。中途状態だけで終わる場合はUNVERIFIABLE。

|現在|許可する次イベント|
|---|---|
|STARTED|RETRY, UNKNOWN, COMPLETED, HOLD|
|RETRY|RETRY, UNKNOWN, COMPLETED, HOLD|
|UNKNOWN|RESOLVED, HOLD|
|RESOLVED|COMPLETED, HOLD|
|COMPLETED|なし|
|HOLD|なし|

ポリシーは上記遷移を削除して厳格化できる。未知状態・規則・安全規則を緩和する遷移は検査不能。
RESOLVEDのevidenceは非空IDの存在検査だけ。参照先を取得・検証する機能はない。
COMPLETEDのresultはJSON boolean trueのみ。数値1や文字列"true"で代用しない。
一旦発見した違反は後続イベントで解消しない。順序不整合があっても観測状態を進め、全診断を残す。
同一操作IDが別streamに現れても別操作として扱う。stream間の因果・重複業務効果は対象外。
連番重複/逆行/欠番、開始番号違反、禁止遷移、開始欠落、結果/解決根拠欠落を位置付きで記録。
物理行は1始まり。ポリシー/ファイル全体の問題は行0。すべてのfindingに規則ID/パス/行/操作ID/stream ID/根拠がある。
解析前にIDを安全に取得できない場合はIDをnullとする。
時刻は有限数値のみ。same_clock=trueの場合だけ各streamのファイル出現順に比較。
