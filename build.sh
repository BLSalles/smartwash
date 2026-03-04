#!/usr/bin/env bash
set -e

echo "[build] Installing requirements..."
pip install -r requirements.txt

echo "[build] Collecting static..."
python manage.py collectstatic --noinput
