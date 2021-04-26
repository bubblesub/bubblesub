FROM ubuntu:latest

MAINTAINER rr- "https://github.com/rr-"

# Disable user-interaction
ENV DEBIAN_FRONTEND noninteractive

# List of system packages
ENV SYSTEM="build-essential software-properties-common locales \
autoconf automake libtool git-core pkg-config wget nasm libxkbcommon-x11-0"

# Prepare building machine
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y \
        $SYSTEM

# List of mpv packages
ENV MPV="libmpv-dev"

# List of FFmpeg packages
ENV FFMPEG="libavcodec-dev libavformat-dev libavdevice-dev zlib1g-dev"

# List of bubblesub packages
ENV BUBBLESUB="python3.8 python3.8-dev python3-pip python3-enchant \
xvfb qt5-default"

# Install bubblesub's dependencies
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y \
        $MPV $FFMPEG $BUBBLESUB

# Cleanup
RUN apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Disable git sslVerify
RUN git config --global http.sslVerify false

# Set Python environment
RUN rm -f /usr/bin/python && \
    ln -s /usr/bin/python3.8 /usr/bin/python && \
    python -m pip install -U pip && \
    pip install setuptools

# Install ffms2
RUN git clone https://github.com/FFMS/ffms2.git && \
    cd ffms2 && \
    ./autogen.sh && \
    make && \
    make install

WORKDIR bubblesub

# Install bubblesub dependencies
RUN mkdir -p bubblesub && \
    touch bubblesub/__init__.py
COPY setup.py .
COPY pyproject.toml .
RUN locale-gen en_US.UTF-8 && \
    export LC_ALL=en_US.UTF-8 && \
    pip install -e .[develop]

# Install bubblesub
COPY bubblesub bubblesub
# ...but not local development garbage
RUN find . -type d -name __pycache__ -exec rm -r {} \+

# Find libffms2.so
RUN ldconfig

# Run pytest
CMD \
    # start a virtual X server for UI tests
    /sbin/start-stop-daemon --start --quiet --pidfile /tmp/custom_xvfb_99.pid --make-pidfile --background --exec /usr/bin/Xvfb -- :99 -screen 0 1920x1200x24 -ac +extension GLX; \
    # run the tests
    pytest bubblesub/
