Repository structure and deployment scripts for a full DFIR log ingestion platform with Terraform + Docker Compose for automatic VPS provisioning and stack setup.


---

# dfir-log-api

## Description
Production-ready DFIR/SOC lab log ingestion API with unified log schema, Redis queue, FastAPI endpoint, worker processors, Nginx reverse proxy, and Terraform + Docker Compose deployment.

---

## Repository Structure
```
dfir-log-api/
├─ log_api.py          # FastAPI endpoint for receiving logs
├─ worker.py           # Worker script to process logs from Redis queue
├─ requirements.txt    # Python dependencies
├─ README.md           # Repo overview and setup instructions
├─ docker/
│   ├─ Dockerfile      # FastAPI container
│   └─ worker.Dockerfile # Worker container
├─ nginx/
│   └─ logs.conf       # Reverse proxy config
├─ terraform/
│   ├─ main.tf         # VPS provisioning
│   ├─ variables.tf    # Terraform variables
│   └─ outputs.tf      # Terraform outputs
├─ docker-compose.yml  # Compose file for FastAPI, Worker, Redis, Nginx
└─ docs/
    └─ schema.md       # Unified log schema documentation
```

---

## terraform/main.tf
```hcl
provider "hcloud" {
  token = var.hcloud_token
}

resource "hcloud_server" "dfir_vps" {
  name        = "dfir-vps"
  image       = "ubuntu-22.04"
  server_type = "cx31"
  location    = "fsn1"
  ssh_keys    = [var.ssh_key_id]
}

output "vps_ip" {
  value = hcloud_server.dfir_vps.ipv4_address
}
```

---

## terraform/variables.tf
```hcl
variable "hcloud_token" {}
variable "ssh_key_id" {}
```

---

## terraform/outputs.tf
```hcl
output "vps_ip" {
  value = hcloud_server.dfir_vps.ipv4_address
}
```

---

## docker-compose.yml
```yaml
version: '3.8'
services:
  redis:
    image: redis:7
    container_name: redis
    ports:
      - "6379:6379"

  api:
    build: ./docker
    container_name: log_api
    environment:
      LOG_API_KEY: "CHANGE_THIS"
      REDIS_URL: "redis://redis:6379/0"
    ports:
      - "8000:8000"
    depends_on:
      - redis

  worker:
    build:
      context: ./docker
      dockerfile: worker.Dockerfile
    container_name: worker
    environment:
      REDIS_URL: "redis://redis:6379/0"
    depends_on:
      - redis

  nginx:
    image: nginx:latest
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/logs.conf:/etc/nginx/conf.d/logs.conf
      - ./certs:/etc/letsencrypt
    depends_on:
      - api
```

---

With this setup, running `terraform apply` will provision a VPS and `docker-compose up -d` will start the full stack including FastAPI API, Redis, worker processors, and Nginx reverse proxy.

1️⃣ Architecture Overview
[Log Sources] --> [API Endpoint: FastAPI on VPS] --> [Redis Queue] --> [Processor Workers] --> [Storage/Visualization]

Log Sources:
- Suricata IDS
- Cowrie SSH honeypot
- Zeek / Bro
- Linux auditd / Syslog
- Custom scripts / apps

API Endpoint:
- FastAPI, HTTPS, API key protected
- Nginx reverse proxy + TLS

Queue:
- Redis for async processing, scaling ingestion

Processor Workers:
- Python workers consuming from Redis
- Normalizes logs to a unified schema

Storage:
- OpenSearch / Elasticsearch
- Loki (optional for raw logs)
- Backup files (JSON / Parquet)
2️⃣ Endpoint Code (FastAPI)
log_api.py:
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import json
import redis
import os

API_KEY = os.getenv("LOG_API_KEY", "CHANGE_THIS")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(REDIS_URL)

app = FastAPI(title="DFIR Log Ingestion API", version="1.0")

# Unified log schema
class LogEntry(BaseModel):
    source: str = Field(..., example="suricata")
    event_type: str = Field(..., example="scan")
    severity: str = Field(..., example="high")
    host: str = Field(..., example="honeypot-01")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    src_ip: str = Field(None, example="45.22.11.90")
    dest_ip: str = Field(None, example="192.168.1.10")
    dest_port: int = Field(None, example=22)
    message: str = Field(None, example="SSH failed login attempt")
    extra: dict = Field(default_factory=dict)

@app.post("/api/v1/logs")
async def receive_log(log: LogEntry, authorization: str = Header(None)):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Push to Redis queue for processing
    r.rpush("log_queue", log.json())

    return {"status": "queued", "received": datetime.utcnow().isoformat()}
3️⃣ Deployment Steps
Install packages on VPS:
sudo apt update
sudo apt install python3-pip nginx certbot
pip install fastapi uvicorn redis pydantic
sudo apt install redis-server
Run FastAPI with Uvicorn (systemd service recommended)
uvicorn log_api:app --host 0.0.0.0 --port 8000
Configure Nginx reverse proxy + TLS
server {
    listen 80;
    server_name logs.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
sudo certbot --nginx -d logs.yourdomain.com
4️⃣ Processor Worker Example
worker.py:
import redis, json
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0)

def process_log(log_json):
    log = json.loads(log_json)
    # Example: save to file
    with open("logs_processed.json", "a") as f:
        f.write(json.dumps(log) + "\n")
    # TODO: push to OpenSearch / Loki here

while True:
    _, log_json = r.blpop("log_queue")
    process_log(log_json)
Run multiple workers to scale ingestion.
5️⃣ GitHub Repo Structure
dfir-log-api/
├─ log_api.py          # FastAPI endpoint
├─ worker.py           # Processor worker
├─ requirements.txt
├─ README.md
├─ docker/
│   ├─ Dockerfile      # FastAPI container
│   └─ worker.Dockerfile
├─ nginx/
│   └─ logs.conf       # Reverse proxy
├─ terraform/          # Optional VPS infra-as-code
└─ docs/
    └─ schema.md       # Unified log schema
6️⃣ Unified Log Schema
{
  "source": "suricata | cowrie | zeek | auditd | custom",
  "event_type": "login | scan | file_access | network | alert",
  "severity": "info | medium | high | critical",
  "host": "hostname",
  "timestamp": "ISO8601 UTC",
  "src_ip": "optional",
  "dest_ip": "optional",
  "dest_port": "optional",
  "message": "optional description",
  "extra": {"key":"value"}
}
This ensures every log source can be normalized and searchable in OpenSearch / SIEM.
