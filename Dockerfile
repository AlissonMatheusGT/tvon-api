FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy
WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Instalamos fontes para o navegador e bibliotecas de sistema
RUN apt-get update && apt-get install -y fonts-liberation fontconfig fonts-roboto && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Instalamos o camoufox com o extra [geoip] que o erro pediu
RUN pip install --no-cache-dir -r requirements.txt gunicorn flask "camoufox[geoip]" \
    && python3 -m camoufox fetch

COPY . .
EXPOSE 5000

CMD ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "240", "app:app"]
