build:
    docker build . --target bubblesub -t bubblesub -f docker/Dockerfile
    docker build . --target tests -t bubblesub-tests -f docker/Dockerfile

test *args:
    docker run --env DISPLAY=':99.0' --rm bubblesub-tests {{args}}

run:
    docker run \
        -e LOCAL_USER_ID=$(id -u) \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -e DISPLAY=$DISPLAY \
        -h $HOSTNAME \
        -v $HOME/.Xauthority:/home/user/.Xauthority \
        -v $HOME/.config/bubblesub/:/home/user/.config/bubblesub/:rw \
        -v $(pwd)/data/:/home/user/data/:rw \
        --rm -it bubblesub

mypy:
    uv run scripts/run_mypy
assets:
    uv run scripts/generate_assets
docs:
    uv run scripts/generate_documentation
