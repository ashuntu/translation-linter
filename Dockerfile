FROM python:3.12

COPY main.py /main.py
COPY translations/ /translations/
COPY requirements.txt /requirements.txt

RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install -r /requirements.txt

ENTRYPOINT [ "python3", "main.py" ]
