import importlib
import os
import zoneinfo
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

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


def test_retention_defaults_to_seven_days(monkeypatch):
    monkeypatch.delenv("RETENTION_DAYS", raising=False)

    assert config.retention_days() == 7


def test_retention_reads_env_var_and_zero_means_keep_everything(monkeypatch):
    monkeypatch.setenv("RETENTION_DAYS", "30")
    assert config.retention_days() == 30

    monkeypatch.setenv("RETENTION_DAYS", "0")
    assert config.retention_days() == 0


def test_vancouver_stays_on_utc_minus_7_after_bc_drops_the_fall_back():
    # BC moved to permanent UTC-7; the 2026-11-01 fall-back never happens.
    # tz data older than release 2026b would put Vancouver on UTC-8 here and
    # shift every local-time calculation (quiet hours) by an hour.
    winter = datetime(2026, 12, 1, 12, 0, tzinfo=ZoneInfo("America/Vancouver"))

    assert winter.utcoffset() == timedelta(hours=-7)


def test_config_makes_zoneinfo_use_only_the_pinned_tzdata_package(tmp_path):
    # Linux hosts (the droplet, CI) have system tz data that zoneinfo would
    # read first, and it may predate BC's change. Importing config must clear
    # the system path so the tzdata version in requirements.txt is the only
    # source everywhere.
    zoneinfo.reset_tzpath(to=[str(tmp_path)])  # stand-in for /usr/share/zoneinfo

    importlib.reload(config)

    assert zoneinfo.TZPATH == ()


def test_quiet_hours_are_off_when_neither_time_is_set(monkeypatch):
    monkeypatch.delenv("QUIET_HOURS_START", raising=False)
    monkeypatch.delenv("QUIET_HOURS_END", raising=False)

    assert config.quiet_hours() is None


def test_quiet_hours_reads_both_times(monkeypatch):
    monkeypatch.setenv("QUIET_HOURS_START", "23:00")
    monkeypatch.setenv("QUIET_HOURS_END", "06:00")

    assert config.quiet_hours() == (time(23, 0), time(6, 0))


@pytest.mark.parametrize(
    "start, end, missing",
    [("23:00", None, "QUIET_HOURS_END"), (None, "06:00", "QUIET_HOURS_START")],
)
def test_quiet_hours_with_only_one_time_set_is_an_error(
    monkeypatch, start, end, missing
):
    # A half-configured window must fail loudly, not silently scrape all night.
    for name, value in (("QUIET_HOURS_START", start), ("QUIET_HOURS_END", end)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=missing):
        config.quiet_hours()


@pytest.mark.parametrize("bad", ["11pm", "25:00", "6", "06:00:00:00", "+1:00", " 1:00"])
def test_quiet_hours_malformed_time_is_a_clear_error(monkeypatch, bad):
    monkeypatch.setenv("QUIET_HOURS_START", bad)
    monkeypatch.setenv("QUIET_HOURS_END", "06:00")

    with pytest.raises(ValueError, match=r"QUIET_HOURS_START .*HH:MM"):
        config.quiet_hours()


def test_quiet_hours_with_the_same_start_and_end_is_an_error(monkeypatch):
    # Ambiguous (all day, or never?) and "off" is already "leave both unset".
    monkeypatch.setenv("QUIET_HOURS_START", "23:00")
    monkeypatch.setenv("QUIET_HOURS_END", "23:00")

    with pytest.raises(ValueError, match="leave both unset"):
        config.quiet_hours()


def test_quiet_hours_are_off_when_both_times_are_empty(monkeypatch):
    # e.g. QUIET_HOURS_START= in a systemd unit, to switch it off in place.
    monkeypatch.setenv("QUIET_HOURS_START", "")
    monkeypatch.setenv("QUIET_HOURS_END", "")

    assert config.quiet_hours() is None
