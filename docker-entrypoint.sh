#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    flask --app app.py db upgrade
fi

exec gunicorn --config /app/gunicorn.conf.py wsgi:app
