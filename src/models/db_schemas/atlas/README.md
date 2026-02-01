## Run Alembic Migrations

### Configuration

```bash
cp alembic.ini.example alembic.ini
```

- Update the `alembic.ini` with your database credentials (`sqlalchemy.url`)
  
### (Optional) Create a new migration

```bash
alembic revision --autogenerate -m "Add ..."
```

### Upgrade the database

```bash
alembic upgrade head
```

### Create the database (if missing)

If the `atlas` database does not exist, create it before running migrations. Examples:

- Using the running `pgvector` container:

```bash
sudo docker exec -u postgres pgvector psql -c "CREATE DATABASE atlas;"
```

- Using a local `psql` client (adjust host/user as needed):

```bash
psql -h localhost -U postgres -c "CREATE DATABASE atlas;"
```

After creating the database run:

```bash
alembic upgrade head
```