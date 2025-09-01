FROM python:3.12.5-slim-bookworm
			
# Set environment variables for non-interactive setup and unbuffered output
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONPATH="/app"
			
# Build argument for setting the main app path
ARG MAINAPPPATH=.
			
# Set working directory inside the container
WORKDIR /app
			
# Copy requirements to leverage Docker cache
COPY "${MAINAPPPATH}/requirements.txt" "${MAINAPPPATH}/requirements.txt"
			
# Install dependencies without caching
RUN pip install --no-cache-dir -r "${MAINAPPPATH}/requirements.txt"
			
# Copy entire application into container
COPY . .
			
# Set working directory to main app path
WORKDIR "/app/${MAINAPPPATH}"
			
# Define the container's startup command
ENTRYPOINT ["python3", "main.py"]