"""Client for ArcGIS REST map and feature services (Cook County GIS). Pages a layer query as GeoJSON."""

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator

RETRY_STATUS = {429, 500, 502, 503, 504}


class ArcGISError(RuntimeError):
    pass


class ArcGIS:
    def __init__(
        self,
        layer_url: str,
        timeout: float = 120,
        retries: int = 5,
        backoff: float = 2.0,
        opener: Callable = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.layer_url = layer_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._open = opener
        self._sleep = sleep

    @property
    def host(self) -> str:
        return urllib.parse.urlparse(self.layer_url).netloc

    def query(self, params: dict) -> dict:
        url = f"{self.layer_url}/query?" + urllib.parse.urlencode(params)
        for attempt in range(self.retries + 1):
            try:
                with self._open(url, timeout=self.timeout) as resp:
                    body = json.loads(resp.read())
                if "error" in body:
                    raise ArcGISError(f"{self.layer_url}: {body['error']}")
                return body
            except urllib.error.HTTPError as e:
                if e.code not in RETRY_STATUS or attempt == self.retries:
                    raise ArcGISError(f"{self.layer_url}: HTTP {e.code}") from e
            except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError) as e:
                if attempt == self.retries:
                    raise ArcGISError(f"{self.layer_url}: {e}") from e
            self._sleep(self.backoff * 2**attempt)
        raise ArcGISError(f"{self.layer_url}: retries exhausted")

    def features(
        self, where: str, out_fields: str, key: str = "OBJECTID", page_size: int = 2000
    ) -> Iterator[list[dict]]:
        """Yield pages of GeoJSON features in lon/lat (EPSG:4326).

        Pages by key (`key > last seen`), which stays fast deep into a large layer where offsets slow down.
        """
        last = None
        fields = out_fields if key in out_fields.split(",") else f"{out_fields},{key}"
        while True:
            page_where = where if last is None else f"({where}) and {key} > {last}"
            body = self.query(
                {
                    "where": page_where,
                    "outFields": fields,
                    "outSR": 4326,
                    "orderByFields": key,
                    "resultRecordCount": page_size,
                    "f": "geojson",
                }
            )
            feats = body.get("features", [])
            if not feats:
                return
            yield feats
            last = feats[-1]["properties"][key]
            if len(feats) < page_size and not body.get("properties", {}).get("exceededTransferLimit"):
                return
