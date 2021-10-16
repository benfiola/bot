FROM rust:slim-bullseye AS geckodriver_builder

# download dependencies
WORKDIR /
RUN apt -y update && \
    apt -y install curl gcc make

# download source
RUN curl -fL -o geckodriver_src.tar.gz https://github.com/mozilla/geckodriver/archive/refs/tags/v0.30.0.tar.gz && \
    mkdir -p /src /build && \
    cd /src && \
    tar xvzf ../geckodriver_src.tar.gz --strip-components=1

# build
WORKDIR /src
RUN cargo build --release && \
    cp target/release/geckodriver /build/geckodriver

FROM python:3.9.6-slim-bullseye

# install dependencies
RUN apt -y update && \
    apt -y install gcc make firefox-esr libopus-dev ffmpeg curl libsodium-dev
COPY --from=geckodriver_builder /build/geckodriver /usr/local/bin/geckodriver

# stage app
WORKDIR /app
ADD setup.py setup.py
ADD bot bot

# install python dependencies
RUN SODIUM_INSTALL=system pip install -e .

CMD ["bot-cli", "run", "/config.ini"]
