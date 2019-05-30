FROM ubuntu:bionic

MAINTAINER rr- "https://github.com/rr-"

# Disable user-interaction
ENV DEBIAN_FRONTEND noninteractive

# List of system packages
ENV SYSTEM="build-essential software-properties-common locales \
autoconf automake libtool git-core pkg-config wget nasm"

# Prepare building machine
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y \
        $SYSTEM

# List of mpv packages
ENV MPV="libegl1-mesa libgl1-mesa-glx libice6 libsm6 libx11-xcb1 libx11-6 \
libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 \
libxinerama1 libxrandr2 libxrender1 libxss1 libxtst6 libxv1 libasound2 \
libbluray-dev libcaca0 libcdio-dev libcdio-cdda-dev libcdio-paranoia-dev \
libdvdnav4 libdvdread4 libenca0 liblua5.2-dev liblua5.2-0 \
libglu1-mesa-dev freeglut3-dev mesa-common-dev \
libfontconfig1 libgstreamer-plugins-base1.0-dev libguess1 \
libharfbuzz0b libicu60 libjack-jackd2-0 libjpeg-turbo8 liblua5.2-0 libpulse0 \
libpython3.7 librubberband2 libsmbclient libuchardet0 libv4l-0 libvdpau1 \
libwayland-egl1-mesa libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
libxcb-randr0 libxcb-render-util0 libxcb-render0 \
libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 libxcb-xkb1 libxcb1 \
libxkbcommon-x11-0 libxkbcommon0 libgnutlsxx28 libass-dev libsdl2-dev"

# List of FFmpeg packages
ENV FFMPEG="libavcodec-dev libavformat-dev libavdevice-dev"

# List of bubblesub packages
ENV BUBBLESUB="python3.7 python3.7-dev python3-pip python-enchant xvfb"

# Install bubblesub's dependencies
RUN add-apt-repository ppa:jonathonf/ffmpeg-4 && \
    apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y \
        $MPV $FFMPEG $BUBBLESUB

# Cleanup
RUN apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Disable git sslVerify
RUN git config --global http.sslVerify false

# Set Python environment
RUN rm -f /usr/bin/python && \
    ln -s /usr/bin/python3.7 /usr/bin/python && \
    python -m pip install -U pip && \
    pip install setuptools dataclasses && \
    pip install pytest docstring_parser mock

# Install mpv
RUN git clone --depth 1 https://github.com/mpv-player/mpv.git && \
    cd mpv && \
    ./bootstrap.py && \
    ./waf configure \
        --enable-libmpv-shared \
        --disable-vdpau \
        --disable-vulkan \
        --disable-drm \
        --disable-drmprime \
        --disable-egl-drm \
        --disable-vaapi-drm \
        --enable-egl-x11 \
        --enable-x11 && \
    ./waf -j4 && \
    ./waf install

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
    pip install -e .

# Install bubblesub
COPY bubblesub bubblesub
# ...but not local development garbage
RUN find . -type d -name __pycache__ -exec rm -r {} \+

# Find libffms2.so
RUN ldconfig

# Run pytest
CMD pytest bubblesub/
