FROM ubuntu:20.04

COPY rsync.py .

RUN apt-get update -y && apt-get upgrade -y && apt-get install rsync python3 -y && apt-get install vim -y

CMD ["python3", "rsync.py"]
