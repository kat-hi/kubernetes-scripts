# server setup
FROM python:3.8

COPY app.py .
COPY requirements.txt .
RUN pip3 install -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["flask", "run", "--host","0.0.0.0"]