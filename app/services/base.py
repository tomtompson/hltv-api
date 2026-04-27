from dataclasses import dataclass, field
from typing import Optional
from xml.etree import ElementTree
import time
import random
import logging

import cloudscraper
from bs4 import BeautifulSoup
from fastapi import HTTPException
from lxml import etree
from requests import Response, TooManyRedirects
import requests

from app.utils.utils import trim 

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class HLTVBase:
    """
    base class for making http requests to hltv and extracting data from web pages.
    """

    URL: str = field(init=False)
    response: dict = field(default_factory=lambda: {}, init=False)
    use_proxy: bool = field(default=False, init=False)
    max_retries: int = field(default=3, init=False)

    # ==================== INIT METHODS ====================

    def __post_init__(self):
        """initialize scraper with advanced settings"""
        self._init_scraper()
        self._init_logging()

    def _init_scraper(self):
        """create cloudscraper with good settings"""
        self.scraper = cloudscraper.create_scraper(
            interpreter='nodejs',        # better for complex js
            delay=15,                     # delay for cloudflare
            browser={
                "browser": "chrome",
                "platform": "windows",
                "desktop": True,
                "mobile": False
            },
            captcha={
                'provider': '2captcha',   # if you have a key
                'api_key': None
            }
        )

        # headers copied from real browser
        self.scraper.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-US;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"'
        })

        # proxy setup (optional)
        self.proxies = []
        self.current_proxy_index = 0

    def _init_logging(self):
        """setup logger for base class"""
        self.logger = logger

    # ==================== PROXY METHODS ====================

    def add_proxy_list(self, proxy_list: list):
        """add list of proxies to rotate"""
        self.proxies = proxy_list
        self.use_proxy = True

    def _get_next_proxy(self) -> Optional[dict]:
        """get next proxy from rotation list"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        return {
            'http': proxy,
            'https': proxy
        }

    # ==================== HELPER METHODS ====================

    def _random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        """add random delay to look like a human"""
        time.sleep(random.uniform(min_sec, max_sec))

    # ==================== REQUEST METHODS ====================

    def make_request(self, url: Optional[str] = None, retry_count: int = 0) -> Response:
        """
        make http get request with retry logic.
        
        args:
            url: url to request (uses self.url if none)
            retry_count: current retry attempt number
            
        returns:
            response object
            
        raises:
            http exception on failure
        """
        url = self.URL if not url else url
        
        # add random delay first time only
        if retry_count == 0:
            self._random_delay(1.0, 3.0)
        
        try:
            # use proxy if enabled
            if self.use_proxy and self.proxies:
                proxy = self._get_next_proxy()
                if proxy:
                    self.scraper.proxies.update(proxy)
                    logger.info(f"using proxy: {proxy['http']}")
            
            # do the request
            response = self.scraper.get(
                url, 
                timeout=30,
                allow_redirects=True
            )
            
            # log response
            logger.info(f"request to {url} - status: {response.status_code}")
            
            # handle 403 with retry
            if response.status_code == 403 and retry_count < self.max_retries:
                logger.warning(f"got 403 for {url}. retrying... (attempt {retry_count + 1})")
                
                # exponential backoff
                wait_time = (2 ** retry_count) + random.uniform(1, 3)
                time.sleep(wait_time)
                
                # recreate scraper on last retry
                if retry_count >= 2:
                    self.__post_init__()
                
                return self.make_request(url, retry_count + 1)
            
            response.raise_for_status()
            return response
            
        except TooManyRedirects:
            raise HTTPException(status_code=404, detail=f"not found for url: {url}")
        except ConnectionError:
            if retry_count < self.max_retries:
                logger.warning(f"connection error. retrying...")
                time.sleep(5)
                return self.make_request(url, retry_count + 1)
            raise HTTPException(status_code=500, detail=f"connection error for url: {url}")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail=f"access forbidden for url: {url}. hltv is blocking the request."
                )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"http error: {str(e)} for url: {url}"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"error for url: {url}. {str(e)}")

    # ==================== PARSING METHODS ====================

    def request_url_bsoup(self, url: Optional[str] = None) -> BeautifulSoup:
        """get page and parse with beautifulsoup"""
        response: Response = self.make_request(url)
        return BeautifulSoup(markup=response.content, features="html.parser")

    @staticmethod
    def convert_bsoup_to_page(bsoup: BeautifulSoup) -> ElementTree:
        """turn beautifulsoup object into elementtree for xpath"""
        return etree.HTML(str(bsoup))

    def request_url_page(self, url: Optional[str] = None) -> ElementTree:
        """get page and convert to elementtree (ready for xpath)"""
        bsoup: BeautifulSoup = self.request_url_bsoup(url)
        return self.convert_bsoup_to_page(bsoup=bsoup)

    # ==================== XPATH METHODS ====================

    def get_all_by_xpath(self, xpath: str, element=None) -> list[str]:
        """get all text elements matching xpath"""
        try:
            target = element if element is not None else self.page
            elements = target.xpath(xpath)
            return [trim(e) for e in elements if e]
        except Exception as e:
            raise ValueError(f"error at xpath data extract '{xpath}': {e}") from e

    def get_text_by_xpath(self, xpath: str, pos: int = 0, iloc: Optional[int] = None,
                          iloc_from: Optional[int] = None, iloc_to: Optional[int] = None,
                          join_str: Optional[str] = None, attribute: Optional[str] = None,
                          element=None) -> Optional[str]:
        """get text or attribute from elements using xpath"""
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

        elements = [extract(e) for e in elements if extract(e)]

        if isinstance(iloc, int):
            return elements[iloc] if iloc < len(elements) else None

        if isinstance(iloc_from, int) and isinstance(iloc_to, int):
            elements = elements[iloc_from:iloc_to]
        elif isinstance(iloc_to, int):
            elements = elements[:iloc_to]
        elif isinstance(iloc_from, int):
            elements = elements[iloc_from:]

        if join_str:
            return join_str.join(elements)

        try:
            return elements[pos]
        except IndexError:
            return None

    def get_elements_by_xpath(self, xpath: str, element=None) -> list[etree._Element]:
        """get raw elements matching xpath"""
        base = element if element is not None else self.page
        try:
            return base.xpath(xpath)
        except Exception as e:
            raise ValueError(f"error at xpath elements extract '{xpath}': {e}") from e

    # ==================== VALIDATION METHODS ====================

    def raise_exception_if_not_found(self, xpath: str):
        """raise 404 if xpath returns nothing"""
        if not self.get_text_by_xpath(xpath):
            raise HTTPException(status_code=404, detail=f"invalid request (url: {self.URL})")