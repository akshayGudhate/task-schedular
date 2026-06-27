FROM python:3.11-slim

# non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# set working directory
WORKDIR /app

# install deps first — better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# copy app code
COPY . .

# set ownership and switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# expose the port
EXPOSE ${SCHEDULER_PORT}

# command to run the service
CMD ["python3", "run.py"]
