#!/bin/bash

USER_ID=${LOCAL_USER_ID:-9001}
echo "Starting with UID : $USER_ID"
useradd --shell /bin/bash -u $USER_ID -o -c "" -m user
adduser user pulse-access
export HOME=/home/user

# change ownership of the installed app to the user
chown -R ${USER_ID}:${USER_ID} .

echo "default-server = unix:/tmp/pulseaudio.socket
# Prevent a server running in the container
autospawn = no
daemon-binary = /bin/true
# Prevent the use of shared memory
enable-shm = false" >/etc/pulse/client.conf

exec gosu user sh -c "uv run --no-sync --project /home/user/bubblesub bubblesub"
