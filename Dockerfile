FROM python:3.12-slim

COPY main.py /main.py
COPY requirements.txt /requirements.txt

RUN pip3 install --no-cache-dir -r requirements.txt
RUN python3 -m spacy download en_core_web_md

ENTRYPOINT [ "python3", "/main.py" ]
