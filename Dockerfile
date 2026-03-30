# Use a lightweight Python image
FROM python:3.9-alpine

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install SQLite
RUN apk add --no-cache sqlite

# Copy application files
COPY . .

# Create session storage directory
RUN mkdir -p /app/flask_session

# Expose port 8888
EXPOSE 8888

# Command to run the Flask app
CMD ["python", "app.py"]
