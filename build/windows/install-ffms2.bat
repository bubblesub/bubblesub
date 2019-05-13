curl -O https://tmp.sakuya.pl/bubblesub/ffms2.zip

7z x ffms2.zip

set ffms2d=plugins64

dumpbin /EXPORTS %ffms2d%\ffms2.dll > %ffms2d%\ffms2.txt

echo EXPORTS >> %ffms2d%\ffms2.def

for /f "skip=19 tokens=4" %%A in ("type %ffms2d%\ffms2.txt") do (
    echo %%A >> %ffms2d%\ffms2.def
)

lib /def:%ffms2d%\ffms2.def /machine:x64 /out:%ffms2d%\ffms2.lib

move %ffms2d%\ffms2.dll C:\Python37\Scripts

move %ffms2d%\ffmsindex.exe C:\Python37\Scripts

move %ffms2d%\ffms2.lib C:\Python37\Scripts
