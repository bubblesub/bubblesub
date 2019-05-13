curl -O https://tmp.sakuya.pl/bubblesub/libass.zip

7z x libass.zip

set libassd=libass

dumpbin /EXPORTS %libassd%\libass.dll > %libassd%\libass.txt

echo EXPORTS >> %libassd%\libass.def

for /f "skip=19 tokens=4" %%A in ("type %libassd%\libass.txt") do (
    echo %%A >> %libassd%\libass.def
)

lib /def:%libassd%\libass.def /machine:x64 /out:%libassd%\libass.lib

move %libassd%\* C:\Python37\Scripts
