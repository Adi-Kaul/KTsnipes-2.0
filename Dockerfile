FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot ./bot
# Settings and tokens come from env vars. Mount a volume at /data so the tally survives redeploys.
ENV DB_PATH=/data/snipes.db
RUN mkdir -p /data
CMD ["python", "-m", "bot.main"]
