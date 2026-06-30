#!/bin/bash
sed -i 's/\r//' boot.sh
. venv/bin/activate

while true; do
    flask deploy
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo "Deploy command failed, retrying in 5 secs..."
    sleep 5
done

exec gunicorn -b :${PORT:-5000} --access-logfile - --error-logfile - flasky:app