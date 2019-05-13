docker run --name bubblesub-deploy bubblesub
docker cp bubblesub-deploy:C:\bubblesub\dist\ .
docker rm bubblesub-deploy
7z a -tzip bubblesub.zip dist\windows\bubblesub.exe
