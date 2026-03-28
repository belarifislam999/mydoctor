#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --run-syncdb
python manage.py migrate accounts
python manage.py migrate appointments
python manage.py migrate
python manage.py createsuperadmin