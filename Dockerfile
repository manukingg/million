FROM python:3.10.6

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt

RUN pip install -r requirements.txt

COPY . /src