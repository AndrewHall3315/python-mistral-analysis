FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python files
COPY mistral_api_handler.py .
COPY urban_planning_analysis.py .
COPY document_processor.py .
COPY app.py .

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Run with gunicorn for production
# - 2 workers for handling concurrent requests
# - 300 second timeout (5 minutes) for long-running analysis
# - Bind to 0.0.0.0 so Railway can access it
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 app:app
