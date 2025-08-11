FROM ubuntu:latest AS base

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

RUN apt-get update && apt-get -y --no-install-recommends install \
    ca-certificates \
    curl


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
RUN ldconfig

WORKDIR /bubblesub

# Install bubblesub dependencies
COPY pyproject.toml .
COPY README.md README.md
COPY bubblesub bubblesub
RUN uv sync --dev
RUN uv pip install .

FROM base AS tests

COPY docker/entrypoint_tests.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

FROM base AS bubblesub
RUN apt-get update && \
    apt-get -y --no-install-recommends install \
        gosu \
        libswscale-dev \
        libavutil-dev \
        libavfilter-dev \
        pulseaudio

ENV PULSE_SERVER=host.docker.internal
RUN mkdir /home/user
RUN cp -r /bubblesub /home/user

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
WORKDIR /home/user
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
