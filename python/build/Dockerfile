FROM python:3.8-slim
WORKDIR /app
COPY module module
COPY restTorest.py restTorest.py
RUN pip install -r module/requirements.txt
#ENTRYPOINT ["python3"]
ENV PYTHONUNBUFFERED=1
CMD ["python3", "./restTorest.py"]

