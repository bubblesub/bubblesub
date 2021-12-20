FROM ubuntu:latest

MAINTAINER rr- "https://github.com/rr-"

ENV SYSTEM_PACKAGES="\
    build-essential software-properties-common locales autoconf automake \
    libtool git-core pkg-config wget nasm libxkbcommon-x11-0"
ENV MPV_PACKAGES="\
    libmpv-dev"
ENV FFMPEG_PACKAGES="\
    libavcodec-dev libavformat-dev libavdevice-dev zlib1g-dev"
ENV BUBBLESUB_PACKAGES="\
    python3.9 python3.9-dev python3.9-distutils enchant libfftw3-dev xvfb qt5-default"
ENV EXTRA_PACKAGES="\
    neovim"

# Disable user-interaction
ENV DEBIAN_FRONTEND noninteractive
# Install dependencies
RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y \
        $SYSTEM_PACKAGES \
        $MPV_PACKAGES \
        $FFMPEG_PACKAGES \
        $BUBBLESUB_PACKAGES \
        $EXTRA_PACKAGES

# Cleanup
RUN apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Set Python environment
RUN wget https://bootstrap.pypa.io/get-pip.py -O get-pip.py && \
    python3.9 get-pip.py && \
    python3.9 -m pip install setuptools && \
    python3.9 -m pip install Cython  # https://github.com/pyFFTW/pyFFTW/issues/252

# Disable git sslVerify
RUN git config --global http.sslVerify false
# Install ffms2
RUN git clone https://github.com/FFMS/ffms2.git && \
    cd ffms2 && \
    ./autogen.sh && \
    make && \
    make install

WORKDIR bubblesub

# Install bubblesub dependencies
COPY bubblesub bubblesub
COPY setup.cfg .
COPY pyproject.toml .
RUN locale-gen en_US.UTF-8 && \
    export LC_ALL=en_US.UTF-8 && \
    python3.9 -m pip install .[develop]

# Remove local development garbage
RUN find . -type d -name __pycache__ -exec rm -r {} \+

# Find libffms2.so
RUN ldconfig

# Run pytest
CMD \
    # start a virtual X server for UI tests
    /sbin/start-stop-daemon --start --quiet --pidfile /tmp/custom_xvfb_99.pid --make-pidfile --background --exec /usr/bin/Xvfb -- :99 -screen 0 1920x1200x24 -ac +extension GLX; \
    # run the tests
    python3.9 -m pytest bubblesub/
