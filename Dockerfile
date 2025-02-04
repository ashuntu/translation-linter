FROM python:3.12-slim

COPY main.py ./
COPY requirements.txt ./

RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python3", "main.py" ]
