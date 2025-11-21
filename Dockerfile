# syntax=docker/dockerfile:1
FROM python:3.10-slim
WORKDIR /app
ENV FLASK_APP=main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5002

# Install build dependencies for Rust-based packages (orjson, jiter, ormsgpack, pydantic_core)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for compiling Rust-based Python packages
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt requirements.txt
COPY src src
COPY main.py main.py

RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5002

CMD ["flask", "run", "--debug"]