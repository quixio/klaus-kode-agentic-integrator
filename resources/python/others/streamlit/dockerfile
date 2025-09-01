# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install required packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Streamlit uses
EXPOSE 80

# Run the Streamlit app
CMD ["streamlit", "run", "main.py", "--server.port=80", "--server.enableCORS=false", "--server.address=0.0.0.0"]