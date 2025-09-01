FROM python:3.11.1-slim-buster

# Set environment variables to non-interactive and unbuffered output
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file(s) to leverage Docker cache
# Assuming all requirements files are in the root or subdirectories
COPY ./requirements.txt ./

# Install dependencies
# Adding `--no-cache-dir` to avoid storing unnecessary files and potentially reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set the command to run your application
ENTRYPOINT ["python3", "main.py"]