FROM python:3.9.6-buster

RUN apt -y update && \
    apt -y install firefox-esr libopus-dev ffmpeg curl && \
    cd /usr/local/bin && \
    curl -fL -o geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz && \
    tar xvzf geckodriver.tar.gz && \
    rm -rf geckodriver.tar.gz

WORKDIR /app
ADD setup.py setup.py
ADD bot bot

RUN pip install -e .
CMD ["bot-cli", "run", "/config.ini"]