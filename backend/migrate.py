"""Apply pending database migrations. Run by deploy/deploy.sh before the
services restart: `venv/bin/python backend/migrate.py`."""

import config
from storage import Storage


def main():
    version = Storage(config.db_path()).migrate()
    print(f"Database at {config.db_path()} is at schema version {version}")


if __name__ == "__main__":
    main()
