from storage import Storage


def migrated_storage(db_path: str) -> Storage:
    """A Storage on a freshly migrated database.

    Storage() no longer creates the schema (the deploy runs migrate.py), so
    tests that need tables go through here.
    """
    storage = Storage(db_path)
    storage.migrate()
    return storage
