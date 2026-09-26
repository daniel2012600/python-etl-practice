FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY parser.py .
COPY posts.json .

CMD ["python", "parser.py"]