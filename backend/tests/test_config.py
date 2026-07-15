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


def test_frontend_origin_defaults_to_vite_dev_server(monkeypatch):
    monkeypatch.delenv("RMT_FINDER_FRONTEND_ORIGIN", raising=False)

    assert config.frontend_origin() == "http://localhost:5173"


def test_frontend_origin_reads_env_var(monkeypatch):
    monkeypatch.setenv("RMT_FINDER_FRONTEND_ORIGIN", "https://rmt.example.com")

    assert config.frontend_origin() == "https://rmt.example.com"


def test_lookahead_defaults_to_three_days(monkeypatch):
    monkeypatch.delenv("LOOKAHEAD_DAYS", raising=False)

    assert config.lookahead_days() == 3


def test_lookahead_reads_env_var(monkeypatch):
    monkeypatch.setenv("LOOKAHEAD_DAYS", "5")

    assert config.lookahead_days() == 5


def test_timezone_for_known_city():
    assert config.timezone_for_city("Victoria") == "America/Vancouver"


def test_timezone_falls_back_to_default_city_for_unknown_or_none():
    assert config.timezone_for_city(None) == "America/Vancouver"
    assert config.timezone_for_city("Nowhere") == "America/Vancouver"


def test_inter_clinic_sleep_defaults_to_one_and_a_half_seconds(monkeypatch):
    monkeypatch.delenv("INTER_CLINIC_SLEEP_SECONDS", raising=False)

    assert config.inter_clinic_sleep_seconds() == 1.5


def test_inter_clinic_sleep_reads_env_var(monkeypatch):
    monkeypatch.setenv("INTER_CLINIC_SLEEP_SECONDS", "0")

    assert config.inter_clinic_sleep_seconds() == 0.0


def test_frontend_dist_default_is_repo_root_frontend_dist_regardless_of_cwd(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("RMT_FINDER_FRONTEND_DIST", raising=False)
    monkeypatch.chdir(tmp_path)

    assert config.frontend_dist_path() == os.path.join(REPO_ROOT, "frontend", "dist")


def test_frontend_dist_reads_env_var(monkeypatch):
    monkeypatch.setenv("RMT_FINDER_FRONTEND_DIST", "C:/somewhere/dist")

    assert config.frontend_dist_path() == "C:/somewhere/dist"


def test_scrape_interval_defaults_to_15_minutes(monkeypatch):
    monkeypatch.delenv("SCRAPE_INTERVAL_MINUTES", raising=False)

    assert config.scrape_interval_minutes() == 15


def test_scrape_interval_reads_env_var(monkeypatch):
    monkeypatch.setenv("SCRAPE_INTERVAL_MINUTES", "5")

    assert config.scrape_interval_minutes() == 5
