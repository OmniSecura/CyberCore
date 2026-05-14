-- CyberCore — Docker MySQL initialisation
-- Runs automatically on first container start (mysql:8.0 mounts /docker-entrypoint-initdb.d/).
-- The root password and cybercore user credentials come from the docker-compose env vars.
--
-- Each microservice gets its own database for proper service isolation.
-- SQLAlchemy's create_all() (DB_CREATE_TABLES=true) creates the tables inside each DB.

CREATE DATABASE IF NOT EXISTS auth_db      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS org_db       CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS scan_db      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- root@% already exists in the MySQL Docker image — just ensure remote access is granted.
GRANT ALL PRIVILEGES ON auth_db.*  TO 'root'@'%';
GRANT ALL PRIVILEGES ON org_db.*   TO 'root'@'%';
GRANT ALL PRIVILEGES ON scan_db.*  TO 'root'@'%';

FLUSH PRIVILEGES;
