# Use a modern Python slim image with better security patch cadence
FROM python:3.12-slim-bookworm

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install SQLite CLI
RUN apt-get update \
	&& apt-get install -y --no-install-recommends sqlite3 \
	&& rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . .

# Create session storage directory
RUN mkdir -p /app/flask_session

# Expose port 8888
EXPOSE 8888

# Command to run the app with a production WSGI server
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
