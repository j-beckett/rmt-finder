import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}


def make_session() -> requests.Session:
    """Create a session with browser-like headers."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get(url: str, **kwargs) -> requests.Response:
    """Make a GET request with browser-like headers."""
    session = make_session()
    extra_headers = kwargs.pop("headers", {})
    session.headers.update(extra_headers)
    return session.get(url, **kwargs)