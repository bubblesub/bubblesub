build:
    docker build . --target bubblesub -t bubblesub -f docker/Dockerfile
    docker build . --target tests -t bubblesub-tests -f docker/Dockerfile

test *args:
    docker run --env DISPLAY=':99.0' --rm bubblesub-tests {{args}}

run:
    [ ! -S /tmp/pulseaudio.socket ] && pactl load-module module-native-protocol-unix socket=/tmp/pulseaudio.socket || /bin/true
    docker run \
        -e LOCAL_USER_ID=$(id -u) \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -e DISPLAY=$DISPLAY \
        --env PULSE_SERVER=unix:/tmp/pulseaudio.socket \
        --env PULSE_COOKIE=/tmp/pulseaudio.cookie \
        --volume /tmp/pulseaudio.socket:/tmp/pulseaudio.socket \
        -h $HOSTNAME \
        -v $HOME/.Xauthority:/home/user/.Xauthority \
        -v $HOME/.config/bubblesub/:/home/user/.config/bubblesub/:rw \
        -v $(pwd)/data/:/home/user/data/:rw \
        --rm -it bubblesub
    # pactl unload-module module-native-protocol-unix

mypy:
    uv run scripts/run_mypy
assets:
    uv run scripts/generate_assets
docs:
    uv run scripts/generate_documentation
