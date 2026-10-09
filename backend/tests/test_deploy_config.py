import os
import re

DEPLOY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "deploy")
UNIT = os.path.join(DEPLOY_DIR, "goatcounter.service")
CADDYFILE = os.path.join(DEPLOY_DIR, "Caddyfile")
DEPLOY_SH = os.path.join(DEPLOY_DIR, "deploy.sh")
VERSION = os.path.join(DEPLOY_DIR, "GOATCOUNTER_VERSION")


def _read(path):
    with open(path) as f:
        return f.read()


def _unit_listen():
    match = re.search(r"-listen[ =](\S+)", _read(UNIT))
    assert match, "goatcounter unit has no -listen (default is *:8080)"
    host, _, port = match.group(1).rpartition(":")
    return host, port


def _api_port():
    # deploy.sh's health check is the repo's record of the API port.
    match = re.search(r"localhost:(\d+)/api/", _read(DEPLOY_SH))
    assert match, "deploy.sh health check URL not found"
    return match.group(1)


def _caddy_upstream(site_prefix):
    """reverse_proxy target of the site block whose address starts with site_prefix."""
    lines = _read(CADDYFILE).splitlines()
    starts = [
        i for i, line in enumerate(lines)
        if line.startswith(site_prefix) and line.rstrip().endswith("{")
    ]
    assert len(starts) == 1, f"expected one {site_prefix} block in Caddyfile"
    depth = 0
    for line in lines[starts[0]:]:
        depth += line.count("{") - line.count("}")
        match = re.match(r"\s*reverse_proxy\s+(\S+)\s*$", line)
        if match:
            return match.group(1)
        if depth == 0:
            break
    raise AssertionError(f"{site_prefix} block has no reverse_proxy")


def test_goatcounter_listens_on_localhost_only():
    host, _ = _unit_listen()

    assert host == "127.0.0.1"


def test_goatcounter_unit_caps_memory():
    match = re.search(r"^MemoryMax=(\S+)$", _read(UNIT), re.MULTILINE)

    assert match, "goatcounter unit has no MemoryMax"
    assert match.group(1) != "infinity"


def test_caddy_stats_proxies_to_goatcounter_port():
    _, port = _unit_listen()

    assert _caddy_upstream("stats.") == f"127.0.0.1:{port}"


def test_caddy_rmtfinder_still_proxies_to_api_port():
    assert _caddy_upstream("rmtfinder.") == f"127.0.0.1:{_api_port()}"


def test_goatcounter_port_differs_from_api_port():
    _, port = _unit_listen()

    assert port != _api_port()


def test_goatcounter_version_is_pinned_in_one_line():
    assert re.fullmatch(r"v\d+\.\d+\.\d+\n", _read(VERSION))
