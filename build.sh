#!/bin/bash

# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Run migrations
echo "Running Django migrations..."
python manage.py migrate --no-input