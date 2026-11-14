# FIX-01変更一覧と再現

- tests/test_acceptance.py: preserve_evidence追加、排他open('x')、symlink祖先拒否、既存ケース保存を呼出しへ置換。
- tests/test_fix01.py: 既存ファイル競合、ファイルsymlink、ディレクトリsymlink、交絡のない重複キーの4試験。
- compare.py: otherwise-valid重複キーfixtureへ置換、方式別一致数counts追加。Python基準判定ロジックは未変更。
- eli.py: SHA256同一、無変更。
- README日英、仕様、SECURITY、CHANGELOG、比較報告、本報告を同期。LICENSE名義は依頼範囲外のため既存候補のまま。

新規証拠先: ELI_EVIDENCE=fresh python3.13 -m unittest discover -s tests -v
単独回帰: python3.13 -m unittest discover -s tests -p test_fix01.py -v
比較: python3.13 compare.py > fresh-comparison.json

競合再現は一時ディレクトリへevidence/normal.jsonを合成markerで作成し、そのdirをELI_EVIDENCEへ設定して全discoverを実行。
期待: 非ゼロ終了かつmarkerのSHA256不変。回帰テストも一時領域を使う。
旧版43件PASS/marker破壊→修正版47件実行/競合ERROR・marker保護をevidence/before_conflict.*,after_conflict.*に保存。
symlink拒否は静的検査と排他作成による。悪意ある同一権限の競合操作への完全隔離ではない。
