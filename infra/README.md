# Infrastructure

The `infra` directory houses tooling for local docker-based development and future deployment automation.

## Docker Compose
- `docker-compose.yml` provisions the full GridBoss stack for development (frontend, api, worker, bot, postgres, redis, optional stripe-cli).
- Dockerfiles for each service (`Dockerfile.api`, `Dockerfile.frontend`, `Dockerfile.worker`, `Dockerfile.bot`) provide lightweight images tailored for iterative work.

### Usage
```powershell
Copy-Item ..\.env.example ..\.env      # if you have not created .env yet
cd ..
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

Stop and remove containers with:
```powershell
docker compose --env-file .env -f infra/docker-compose.yml down
```

Enable Stripe webhook forwarding when needed:
```powershell
docker compose --env-file .env -f infra/docker-compose.yml --profile stripe up stripe-cli
```

Volumes provide stateful Postgres (`postgres_data`), Redis (`redis_data`), and an isolated `node_modules` directory for the frontend dev server.