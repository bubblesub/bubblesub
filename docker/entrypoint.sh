#!/bin/bash

USER_ID=${LOCAL_USER_ID:-9001}
echo "Starting with UID : $USER_ID"
useradd --shell /bin/bash -u $USER_ID -o -c "" -m user
export HOME=/home/user

# change ownership of the installed app to the user
chown -R ${USER_ID}:${USER_ID} .

exec gosu user sh -c "uv run --project /home/user/bubblesub bubblesub"
