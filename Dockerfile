FROM python:3.11-slim

WORKDIR /code
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code

ENV DJANGO_SETTINGS_MODULE=project.settings

CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000"]
