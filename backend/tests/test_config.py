import os

import config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_db_path_default_is_repo_root_data_dir_regardless_of_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("RMT_FINDER_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    assert config.db_path() == os.path.join(REPO_ROOT, "data", "rmt-finder.db")


def test_db_path_reads_env_var(monkeypatch):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", "C:/somewhere/else.db")

    assert config.db_path() == "C:/somewhere/else.db"
