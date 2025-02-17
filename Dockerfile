# Use Python 3.12 as the base image
FROM python:3.12-slim

# Prevent Python from writing pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy README.md first
COPY README.md .
COPY pyproject.toml poetry.lock ./

# Upgrade pip, install Poetry, and install project dependencies without creating a virtual environment
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --only main

# Copy project files into the container
COPY . /app/

# Expose port 8000
EXPOSE 8000

# Start the application using Gunicorn
CMD ["gunicorn", "ai_cooking_project.wsgi:application", "--bind", "0.0.0.0:8000"]
