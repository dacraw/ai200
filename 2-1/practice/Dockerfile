FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
RUN mkdir /home/processed
ENV PORT=8000
EXPOSE 8000
CMD ["sh","-c","gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --access-logfile - main:app"]