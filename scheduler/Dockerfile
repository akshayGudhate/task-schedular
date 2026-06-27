FROM python:3.11-slim

# non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# install deps first — better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# copy app code
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE ${SCHEDULER_PORT}

CMD ["python3", "run.py"]
