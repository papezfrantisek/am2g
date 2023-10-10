# syntax=docker/dockerfile:1
FROM python:3.12.0-alpine 
LABEL Maintainer="frantisek@elkjop.no"
ADD getmetricrest.py .
RUN pip install --upgrade pip
RUN pip install requests prometheus_client
EXPOSE 8000
CMD ["python", "./getmetricrest.py"]
