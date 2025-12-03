FROM python:3.12.12 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install -r requirements.txt

FROM python:3.12.12-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .

# Starte wie bei Render: uvicorn app.main:app
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
