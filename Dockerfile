FROM python:3.9

WORKDIR /app

# Set timezone to IST (UTC+5:30) so logs show Indian Standard Time
ENV TZ=Asia/Kolkata
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies, adding psycopg2 for PostgreSQL support
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
RUN python -m nltk.downloader vader_lexicon

# Create necessary directories
RUN mkdir -p /app/data /app/logs

COPY . .

EXPOSE 7860

# We use host 0.0.0.0 and port 7860 specifically for Hugging Face Spaces
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
