FROM python:3.10.11
RUN apt -y update && apt -y install ffmpeg

WORKDIR /workspaces/bot/bot
ADD bot bot
ADD pyproject.toml pyproject.toml
ADD setup.py setup.py

RUN pip install -e .
CMD ["bot", "run"]
