SET LOCAL_PATH=bubblesub\
SET PKG_PATH=C:\Python37\Lib\site-packages\
SET LAZY=%PKG_PATH%lazy_import\VERSION
SET ASS=%PKG_PATH%ass_tag_parser\data\draw_bnf.txt

pip install pyinstaller

pyinstaller --add-data="%LOCAL_PATH%data;bubblesub\data" ^
            --add-data="%LOCAL_PATH%cmd;bubblesub\cmd" ^
            --add-data="%LOCAL_PATH%ui\font_combo_box.py;bubblesub\ui" ^
            --add-data="%LOCAL_PATH%ui\model\styles.py;bubblesub\ui\model" ^
            --add-data="%LAZY%;lazy_import" ^
            --add-data="%ASS%;ass_tag_parser\data" ^
            --noconfirm ^
            --windowed ^
            --noupx ^
            --onefile ^
            --dist .\dist\windows ^
            --name "bubblesub" ^
            bubblesub\__main__.py
