FROM python:3.8-slim-buster

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY *.py ./
CMD ["python", "main.py"]
