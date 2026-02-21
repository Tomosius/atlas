# Docker

## Core Commands

```bash
docker build -t <image> .        # build image from Dockerfile
docker run --rm <image>          # run container, remove on exit
docker run -p 8080:8080 <image>  # map host:container ports
docker ps                        # list running containers
docker images                    # list local images
docker logs <container>          # view container logs
docker exec -it <container> sh   # open shell in running container
```

## Dockerfile Best Practices

- Use specific version tags — never `latest` in production
- One process per container
- Use multi-stage builds to keep final images small
- Put `COPY` and `RUN` instructions that change frequently at the end (cache layers)
- Run as a non-root user

```dockerfile
# Multi-stage build example (Python)
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
RUN adduser --disabled-password appuser && chown -R appuser /app
USER appuser
CMD ["python", "-m", "myapp"]
```

## .dockerignore

Always create `.dockerignore` to exclude unnecessary files:

```
.git
.env
__pycache__
*.pyc
node_modules
.venv
dist
*.log
```

## docker compose

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      timeout: 5s
      retries: 5
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

```bash
docker compose up -d        # start all services in background
docker compose down         # stop and remove containers
docker compose down -v      # also remove volumes (wipes data)
docker compose logs -f app  # follow logs for a service
docker compose exec app sh  # shell into a running service
```

## Environment Variables

- Never bake secrets into images — pass via environment variables or secrets
- Use `.env` file for local dev (never commit it)
- Use `--env-file .env` or `environment:` in compose

```bash
docker run --env-file .env <image>
```

## Image Hygiene

```bash
docker system prune          # remove stopped containers, dangling images
docker system prune -a       # also remove unused images
docker image rm <image>      # remove a specific image
```

## Commands

- Build: `{{commands.build}}`
- Run: `{{commands.run}}`
- Compose up: `{{commands.compose_up}}`
- Compose down: `{{commands.compose_down}}`
