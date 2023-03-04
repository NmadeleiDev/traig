FROM python:3.10.2

COPY . probe
RUN pip install --no-cache-dir -r probe/requirements.txt

CMD pytest probe
