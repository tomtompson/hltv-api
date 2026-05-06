# app/services/hltv_base.py

import logging
import random
from dataclasses import dataclass, field
from typing import cast

import requests
from bs4 import BeautifulSoup
from curl_cffi.requests.models import Response as CurlResponse
from fastapi import HTTPException
from lxml import etree
from lxml.etree import _Element
from requests import TooManyRedirects
from requests.models import Response as RequestsResponse

from app.settings import settings
from app.utils.utils import trim

logger = logging.getLogger(__name__)

_FLARESOLVERR_SESSION_ID = "hltv-api"

# ==================== HELPERS ====================

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

_SEC_CH_UA = [
    '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    '"Chromium";v="123", "Not(A:Brand";v="24", "Google Chrome";v="123"',
]

_ACCEPT_LANGUAGES = ["pt-BR,pt;q=0.9,en;q=0.8", "en-US,en;q=0.9,pt;q=0.8"]


def _get_random_headers() -> dict[str, str]:
    """Generate random HTTP headers to avoid fingerprinting.

    Returns:
        dict with headers

    """
    ua = random.choice(_USER_AGENTS)
    sec_ch_ua = random.choice(_SEC_CH_UA)
    accept_lang = random.choice(_ACCEPT_LANGUAGES)
    platform = "Windows" if "Windows" in ua else "macOS"
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": accept_lang,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": sec_ch_ua,
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": f'"{platform}"',
    }


# ==================== BASE CLASS ====================


@dataclass
class HLTVBase:
    """class for making HTTP requests to HLTV and extracting data from web pages.

    Attributes:
        response (dict): stores the response data (results, metadata, etc.)
        use_proxy (bool): if True, proxy support can be enabled (reserved for future)

    """

    URL: str = field(init=False)
    response: dict = field(default_factory=dict, init=False)
    use_proxy: bool = field(default=False, init=False)

    # ==================== INIT METHODS ====================

    def __post_init__(self) -> None:
        """Initialize the session and logging after dataclass init."""
        self._init_session()
        self._init_logging()

    def _init_session(self) -> None:
        """Create a new HTTP session with TLS fingerprint spoofing.
        uses curl_cffi if available, otherwise falls back to cloudscraper.
        """
        try:
            from curl_cffi import requests as curl_requests

            self._session = curl_requests.Session(impersonate="chrome124")
            logger.info("using curl_cffi session with chrome 124 impersonate")
        except ImportError:
            import cloudscraper

            self._session = cloudscraper.create_scraper(
                interpreter="nodejs",
                delay=15,
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "desktop": True,
                    "mobile": False,
                },
            )
            logger.info("using cloudscraper fallback session")
        self._session.headers.update(_get_random_headers())

    def _init_logging(self) -> None:
        """Set up a logger instance for the class."""
        self.logger = logger

    def _refresh_headers(self) -> None:
        """Update session headers with a fresh random set."""
        self._session.headers.update(_get_random_headers())

    def _ensure_flaresolverr_session(self) -> None:
        """Create the persistent FlareSolverr session if it doesn't exist yet."""
        resp = requests.post(settings.FLARESOLVERR_URL, json={"cmd": "sessions.list"}, timeout=10)
        existing = resp.json().get("sessions", [])
        if _FLARESOLVERR_SESSION_ID not in existing:
            self.logger.info("creating flaresolverr session")
            requests.post(
                settings.FLARESOLVERR_URL,
                json={"cmd": "sessions.create", "session": _FLARESOLVERR_SESSION_ID},
                timeout=10,
            )

    # ==================== REQUEST METHODS ====================

    def make_request(self, url: str | None = None) -> CurlResponse | RequestsResponse:
        """Perform a single HTTP GET request, routing through FlareSolverr if available.

        Args:
            url: target url (uses self.URL if not provided)

        Returns:
            response object with status 2xx

        Raises:
            HTTPException: on connection errors, redirect loops, or http errors

        """
        url = url or self.URL
        self._refresh_headers()

        try:
            self._ensure_flaresolverr_session()

            fs_response = requests.post(
                settings.FLARESOLVERR_URL,
                json={"cmd": "request.get", "url": url, "session": _FLARESOLVERR_SESSION_ID, "maxTimeout": 60000},
                timeout=70,
            )
            fs_data = fs_response.json()

            if fs_data.get("status") != "ok":
                raise HTTPException(status_code=500, detail=f"flaresolverr error: {fs_data.get('message')}")

            status = fs_data["solution"]["status"]
            self.logger.info(f"flaresolverr request to {url} - status: {status}")

            if status == 404:
                raise HTTPException(status_code=404, detail=f"not found: {url}")
            if status == 403:
                raise HTTPException(status_code=403, detail=f"access forbidden: {url}")
            if status >= 400:
                raise HTTPException(status_code=status, detail=f"HTTP error {status}: {url}")

            # wrap response so downstream code (.content) works unchanged
            class _FakeResponse:
                def __init__(self, html: str, status_code: int) -> None:
                    self.content = html.encode("utf-8")
                    self.status_code = status_code

            return _FakeResponse(fs_data["solution"]["response"], status)  # type: ignore[return-value]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"request error: {e!s}")

    def request_url_bsoup(self, url: str | None = None) -> BeautifulSoup:
        """Fetch a url and parse it with beautifulsoup.

        Args:
            url: target url (uses self.URL if not provided)

        Returns:
            beautifulsoup object

        """
        response = self.make_request(url)
        return BeautifulSoup(response.content, "html.parser")

    def request_url_page(self, url: str | None = None) -> _Element:
        """Fetch a url and return an lxml elementtree for xpath queries.

        Args:
            url: target url (uses self.URL if not provided)

        Returns:
            lxml elementtree

        """
        bsoup = self.request_url_bsoup(url)
        return self.convert_bsoup_to_page(bsoup)

    @staticmethod
    def convert_bsoup_to_page(bsoup: BeautifulSoup) -> _Element:
        """Convert beautifulsoup object to lxml elementtree.

        Args:
            bsoup: beautifulsoup object

        Returns:
            lxml elementtree

        """
        return etree.HTML(str(bsoup))

    # ==================== PARSING METHODS ====================

    def get_all_by_xpath(self, xpath: str, element=None) -> list[str]:
        """Extract all text strings matching an xpath expression.

        Args:
            xpath: xpath expression
            element: optional lxml element (uses self.page if not provided)

        Returns:
            list of trimmed strings

        """
        try:
            target = element if element is not None else self.page
            elements = target.xpath(xpath)
            return [trim(e) for e in elements if e]
        except Exception as e:
            msg = f"xpath extraction error '{xpath}': {e}"
            raise ValueError(msg) from e

    def get_text_by_xpath(
        self,
        xpath: str,
        pos: int = 0,
        iloc: int | None = None,
        iloc_from: int | None = None,
        iloc_to: int | None = None,
        join_str: str | None = None,
        attribute: str | None = None,
        element=None,
    ) -> str | None:
        """Get text or attribute value from elements matching an xpath.

        Args:
            xpath: xpath expression
            pos: position to return (default 0)
            iloc: single index to extract
            iloc_from: start index for slicing
            iloc_to: end index for slicing
            join_str: if provided, join all extracted strings with this separator
            attribute: if provided, get this attribute value instead of text
            element: optional lxml element (uses self.page if not provided)

        Returns:
            string or None if nothing found

        """
        if not hasattr(self, "page"):
            self.page = self.request_url_page()

        base = element if element is not None else self.page
        elements = base.xpath(xpath)

        if not elements:
            return None

        def extract(e):
            if isinstance(e, etree._Element):
                if attribute:
                    return trim(e.get(attribute, ""))
                return trim(e.text) if e.text else None
            return trim(str(e)) if e else None

        extracted = [extract(e) for e in elements if extract(e)]

        if isinstance(iloc, int):
            return extracted[iloc] if iloc < len(extracted) else None
        if isinstance(iloc_from, int) and isinstance(iloc_to, int):
            extracted = extracted[iloc_from:iloc_to]
        elif isinstance(iloc_to, int):
            extracted = extracted[:iloc_to]
        elif isinstance(iloc_from, int):
            extracted = extracted[iloc_from:]

        if join_str:
            return join_str.join(extracted)
        try:
            return extracted[pos]
        except IndexError:
            return None

    def get_elements_by_xpath(self, xpath: str, element=None) -> list[etree._Element]:
        """Return raw lxml elements matching an xpath.

        Args:
            xpath: xpath expression
            element: optional lxml element (uses self.page if not provided)

        Returns:
            list of lxml elements

        """
        base = element if element is not None else self.page
        try:
            return cast(list[etree._Element], base.xpath(xpath))
        except Exception as e:
            msg = f"xpath element extraction error '{xpath}': {e}"
            raise ValueError(msg) from e

    def raise_exception_if_not_found(self, xpath: str) -> None:
        """Raise http 404 if the xpath returns no content.

        Args:
            xpath: xpath expression to check

        """
        if not self.get_text_by_xpath(xpath):
            raise HTTPException(
                status_code=404,
                detail=f"invalid request (url: {self.URL})",
            )
