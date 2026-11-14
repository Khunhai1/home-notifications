import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36"
)


def http_client():
    return httpx.Client(headers={"User-Agent": USER_AGENT, "Accept-Language": "de-CH,de;q=0.9"}, timeout=30)
