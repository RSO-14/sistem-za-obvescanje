# lightweight Python base
FROM python:3.11-slim

# set workdir
WORKDIR /app

# install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy code
COPY src ./app

# runtime user (optional)
RUN useradd -m appuser
USER appuser

# expose port uvicorn will listen on
EXPOSE 8000

# default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
