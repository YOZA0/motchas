FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py ./
COPY web/ ./web/
COPY private_assets/ ./private_assets/
RUN mkdir -p /app/data
ENV PORT=8080
EXPOSE 8080
CMD ["python", "server.py"]
