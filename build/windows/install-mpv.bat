set mpv_path="https://sourceforge.net/projects/mpv-player-windows/files/libmpv"

curl -L %mpv_path%/mpv-dev-x86_64-20190602-git-4d001bb.7z > libmpv.7z

curl -O https://tmp.sakuya.pl/bubblesub/opengl-dll.zip

7z x libmpv.7z

7z x opengl-dll.zip

move opengl-dll\* C:\Windows\System32

lib /def:mpv.def /machine:x64 /out:mpv.lib

move mpv-1.dll C:\Python37\Scripts\mpv.dll

move mpv.lib C:\Python37\libs

move include C:\Python37\include\mpv
