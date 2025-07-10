release: python manage.py collectstatic --noinput
web: gunicorn inkwell.wsgi:application --bind 0.0.0.0:$PORT