import migrate
from storage import Storage


def test_main_migrates_the_configured_database(monkeypatch, tmp_path, capsys):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))

    migrate.main()

    Storage(str(db_path)).require_current()
    assert "schema version 1" in capsys.readouterr().out
