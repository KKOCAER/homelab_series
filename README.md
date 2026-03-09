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

