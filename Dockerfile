FROM python:3.12-slim

# Не создавать .pyc и не буферизовать вывод (логи сразу видны в панели)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — кешируется отдельным слоем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем весь проект
COPY . .

# Порт WebApp (BotHost может переопределить через переменную окружения PORT)
EXPOSE 8000

# Единая точка входа: поднимает и FastAPI (WebApp + API), и бота aiogram
CMD ["python", "run.py"]
