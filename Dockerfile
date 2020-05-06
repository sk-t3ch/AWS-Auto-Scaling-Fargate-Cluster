FROM python:3.7-slim

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY src /app

EXPOSE 5000

CMD python app.py

