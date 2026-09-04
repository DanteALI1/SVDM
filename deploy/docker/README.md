# Docker deployment notes

```bash
cp .env.example .env
docker compose up --build -d
```

Services: `db`, `redis`, `backend`, `worker`, `frontend`.

Backend entrypoint runs migrations and `bootstrap_svdb` when `SVDB_BOOTSTRAP=1`.
