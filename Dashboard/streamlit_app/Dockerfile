# Лёгкий образ с Python 3.12
FROM python:3.12-slim

# Не даём Python писать .pyc и буферизовать вывод (удобнее смотреть логи)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# curl нужен только для healthcheck ниже
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Сначала копируем только requirements.txt — так Docker закэширует слой
# с зависимостями и не будет переустанавливать их при каждом изменении кода
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Теперь копируем сам код приложения
COPY app.py analysis.py charts.py data_io.py ./
COPY .streamlit ./.streamlit

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0"]
