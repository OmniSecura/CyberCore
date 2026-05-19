# log_db — table definitions

Canonical SQL schema for the `log-service` (cyberlog ingest + dashboard reads)
and the `log-consumer` worker that drains the Redis buffer into MySQL.

These files document the authoritative shape of every table. The application
itself uses SQLAlchemy `create_all()` at startup (`DB_CREATE_TABLES=true`), so
these `.sql` files don't run automatically — they are the human-readable
reference used by ops scripts (`database/scripts/`) and by anyone reading the
codebase to understand the schema without booting the service.

## Tables

| File           | What it stores                                                  |
|----------------|-----------------------------------------------------------------|
| `api_keys.sql` | Per-organization API keys used by the `cyberlog` Python client. |
| `logs.sql`     | All ingested log entries, scoped to an organization.            |

## Database creation

`log_db` itself is created by `database/docker-init/01_databases.sql` on the
**first** MySQL boot. If you added `log_db` to that file after the MySQL
volume had already been initialized, the script won't re-run — recreate the
volume with `docker compose down -v` or create the DB manually:

```sql
CREATE DATABASE IF NOT EXISTS log_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON log_db.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

`log-service` will then create all tables in this directory automatically on
its next startup.
