"""Client for the Chicago Data Portal and the Cook County data catalog (Socrata SoQL).

Pages with $limit/$offset under a stable $order, sends the app token when set, and retries
throttling and server errors with backoff. The app never calls this live; only jobs do.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator

from core.settings import settings

CHICAGO = "data.cityofchicago.org"
COOK = "datacatalog.cookcountyil.gov"

RETRY_STATUS = {429, 500, 502, 503, 504}


class SocrataError(RuntimeError):
    pass


class Socrata:
    def __init__(
        self,
        host: str,
        app_token: str | None = None,
        timeout: float = 120,
        retries: int = 5,
        backoff: float = 2.0,
        opener: Callable = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.host = host
        self.app_token = settings.socrata_app_token if app_token is None else app_token
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._open = opener
        self._sleep = sleep

    def url(self, dataset_id: str, params: dict) -> str:
        return f"https://{self.host}/resource/{dataset_id}.json?" + urllib.parse.urlencode(params)

    def get(self, dataset_id: str, params: dict) -> list[dict]:
        req = urllib.request.Request(self.url(dataset_id, params))
        if self.app_token:
            req.add_header("X-App-Token", self.app_token)
        for attempt in range(self.retries + 1):
            try:
                with self._open(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code not in RETRY_STATUS or attempt == self.retries:
                    raise SocrataError(f"{dataset_id}: HTTP {e.code}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == self.retries:
                    raise SocrataError(f"{dataset_id}: {e}") from e
            self._sleep(self.backoff * 2**attempt)
        raise SocrataError(f"{dataset_id}: retries exhausted")

    def pages(
        self,
        dataset_id: str,
        order: str,
        select: str | None = None,
        where: str | None = None,
        page_size: int = 50_000,
    ) -> Iterator[list[dict]]:
        """Yield pages until a short page comes back. `order` must make rows unique (e.g. ':id')."""
        offset = 0
        while True:
            params = {"$order": order, "$limit": page_size, "$offset": offset}
            if select:
                params["$select"] = select
            if where:
                params["$where"] = where
            rows = self.get(dataset_id, params)
            if rows:
                yield rows
            if len(rows) < page_size:
                return
            offset += page_size

    def since(self, column: str, value: str) -> str:
        """Where clause for incremental pulls: rows changed after the last pull."""
        return f"{column} > '{value}'"
