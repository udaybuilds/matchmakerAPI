FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    git \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# Copy code
COPY ./authentication_module ./authentication_module

# Set working directory to the backend folder
WORKDIR /app/authentication_module

# Copy and install Python dependencies
COPY ./authentication_module/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Set Flask environment variables
ENV FLASK_APP=authentication.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Run the app
CMD ["flask", "run"]