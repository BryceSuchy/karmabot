FROM python:3.14

WORKDIR /app
ENV POETRY_VIRTUALENVS_CREATE=false
RUN pip3 install --no-cache-dir poetry==2.2.1

COPY pyproject.toml poetry.lock README.md /app/
COPY karmabot /app/karmabot
RUN poetry install --only main --no-interaction --no-ansi

ADD start.sh /app/main

ENTRYPOINT /app/main
