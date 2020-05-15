FROM python:2.7         
ADD . /todo
WORKDIR /todo
EXPOSE 5001
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "run.py"]
CMD ["run.py"]
#CMD ["worker.py"]
