# OSS比較 — FIX-01再実測

5合成入力をjson.tool、jq基本処理、汎用Python基準、ELIへ同じバイト列で渡した。20実行。

|方式|契約期待との一致|重複キー以外有効な系列の判定|
|---|---:|---|
|ELI|5/5|拒否、INVALID_JSONL・UNVERIFIABLE/2|
|汎用Python固定基準|4/5|accepted=true、issues=[]、重複キー検出不可|
|json.tool|1/5|構文検査として受理|
|jq基本処理|1/5|パース・object確認として受理|

今回のduplicate_keyは開始イベントのsequence:1を2回記載し、そのほか必須フィールドと合法な完了を備える。
欠落フィールドによりPython基準が拒否した旧実験の交絡を除いた。期待不合格という契約は変更していない。
Python基準のロジックは未修正。ELI/基準の比較結果をよく見せるための数値合わせはしない。
結果と理由・contract_matched・countsはevidence/comparison.json。回帰test_clean_duplicate_fixtureで独立に確認。

json.tool/jq自体の不具合率ではなく今回設定した検査契約の範囲差である。
状態契約検査機能を備えた設定を与えていないパースツールに、状態検査能力の優劣を主張しない。
汎用Pythonへ厳密パーサを追加すれば同等対応は可能で、独占的な検出原理ではない。
個別イベント位置、規則、設定、限界を配布物としてまとめる点がELIの追加価値。
機械時間はパーサの子プロセス起動等を含むため速度優位に使わない。
工数削減、ROI、需要、一般の誤検知率・見逃し率は未測定。

一次資料: https://docs.python.org/3/library/json.html 、https://jqlang.org/manual/
再現: python compare.py > comparison-new.json （jq未導入時はNOT_INSTALLED_NOT_RUN）。
