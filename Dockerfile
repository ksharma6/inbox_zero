# syntax=docker/dockerfile:1
FROM python:3.10-alpine
WORKDIR /app
ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements.txt requirements.txt
COPY src src
COPY .env.example .env

COPY .gitignore .gitignore
COPY .pre-commit-config.yaml .pre-commit-config.yaml
RUN pip install -r requirements.txt
EXPOSE 5002

CMD ["flask", "run", "--debug"]