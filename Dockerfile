FROM python:3.10-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers with explicit paths
RUN pip install --no-cache-dir playwright

# Set environment variables for Playwright and Render
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
ENV RENDER=true
ENV PLAYWRIGHT_SKIP_VALIDATION=1

# Install additional dependencies required for Playwright on Render
RUN apt-get update && apt-get install -y \
    fonts-noto-color-emoji \
    ttf-wqy-zenhei \
    fonts-noto-cjk \
    fonts-freefont-ttf \
    libxtst6 \
    libxrandr2 \
    libgconf-2-4 \
    libnss3-dev \
    libgbm-dev \
    libxss1 \
    libasound2 \
    libxdamage1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium with explicit path and skip browser download check
RUN mkdir -p /app/.playwright && \
    python -m playwright install chromium --with-deps && \
    python -m playwright install-deps chromium && \
    chmod -R 777 /app/.playwright
    
# Verify browser installation
RUN ls -la /app/.playwright

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application using the start.sh script
CMD ["bash", "./start.sh"]
