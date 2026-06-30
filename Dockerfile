FROM python:3.11-alpine

ENV FLASK_APP=flasky.py
ENV FLASK_CONFIG=production

RUN adduser -D flasky

WORKDIR /home/flasky

COPY requirements requirements
RUN python -m venv venv
RUN venv/bin/pip install -r requirements/docker.txt

COPY app app
COPY migrations migrations
COPY flasky.py config.py boot.sh ./

RUN chmod +x boot.sh
RUN chown -R flasky:flasky /home/flasky

USER flasky

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]