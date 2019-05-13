FROM mcr.microsoft.com/windows/servercore:1803

ENV chocolateyUseWindowsCompression false

ARG choco_link=https://chocolatey.org/install.ps1

RUN powershell -Command \
    iex ((new-object net.webclient).DownloadString('%choco_link%')); \
choco feature disable --name showDownloadProgress

# Install python 3.7, visual studio tools and 7zip
RUN choco install -y python3 visualstudio2017-workload-vctools 7zip

# Add visual studio tools path to the environment variable PATH
ARG vspath="C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\VC"
RUN setx path "%path%;%vspath%\Tools\MSVC\14.16.27023\bin\Hostx64\x64"

# Add api-ms-crt libraries path to the environment variable PATH
RUN setx path "%path%;C:\Windows\System32\downlevel"

# Upgrade pip and install packages
RUN python -m pip install --upgrade pip
RUN pip install Cython sip

# Set working directory
WORKDIR bubblesub

# Copy bubblesub locally
COPY . .

ARG bat_dir=build/windows

# MPV Compilation
RUN call %bat_dir%\install-mpv.bat

# FFMS2 Compilation
RUN call %bat_dir%\install-ffms2.bat

# LIBASS Compilation
RUN call %bat_dir%\install-libass.bat

# BUBBLESUB building
RUN pip install .

# Create exe
RUN call %bat_dir%\create-binary.bat
