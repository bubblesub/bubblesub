FROM ubuntu:latest

ENV SYSTEM_PACKAGES="\
    build-essential software-properties-common locales autoconf automake \
    libtool git-core pkg-config wget nasm libxkbcommon-x11-0"
ENV MPV_PACKAGES="\
    libmpv-dev"
ENV FFMPEG_PACKAGES="\
    libavcodec-dev libavformat-dev libavdevice-dev zlib1g-dev"
ENV BUBBLESUB_PACKAGES="\
    python3.10 python3-pyqt5 python3-pyqt5.qtopengl libfftw3-dev xvfb libqt5gui5"
ENV EXTRA_PACKAGES="\
    neovim"

# Disable user-interaction
ENV DEBIAN_FRONTEND=noninteractive
# Install dependencies
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y \
        $SYSTEM_PACKAGES \
        $MPV_PACKAGES \
        $FFMPEG_PACKAGES \
        $BUBBLESUB_PACKAGES \
        $EXTRA_PACKAGES && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Set Python environment
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Disable git sslVerify
RUN git config --global http.sslVerify false
# Install ffms2
RUN git clone https://github.com/FFMS/ffms2.git --branch 5.0 && \
    cd ffms2 && \
    ./autogen.sh && \
    make && \
    make install

WORKDIR /bubblesub

# Install bubblesub dependencies
COPY pyproject.toml .
RUN mkdir bubblesub
RUN uv sync --dev
RUN uv pip install .
COPY bubblesub bubblesub

# Remove local development garbage
RUN find . -type d -name __pycache__ -exec rm -r {} \+

# Find libffms2.so
RUN ldconfig

# Run pytest
# ENTRYPOINT /bin/bash
CMD \
    # start a virtual X server for UI tests
    /sbin/start-stop-daemon --start --quiet --pidfile /tmp/custom_xvfb_99.pid --make-pidfile --background --exec /usr/bin/Xvfb -- :99 -screen 0 1920x1200x24 -ac +extension GLX; \
    # run the tests
    uv run pytest bubblesub/
