"""Client for ArcGIS REST map and feature services (Cook County GIS). Pages a layer query as GeoJSON."""

import http.client
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator

RETRY_STATUS = {429, 500, 502, 503, 504}


MIN_PAGE = 25


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
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                ConnectionError,
                TimeoutError,
                ValueError,
            ) as e:
                # ValueError: a body that is not JSON (an HTML error page from an overloaded server).
                if attempt == self.retries:
                    raise ArcGISError(f"{self.layer_url}: {e}") from e
            self._sleep(self.backoff * 2**attempt)
        raise ArcGISError(f"{self.layer_url}: retries exhausted")

    def object_id_field(self) -> str:
        """The layer's own object ID field (OBJECTID, OBJECTID_1, FID, ...), from its metadata."""
        url = f"{self.layer_url}?f=json"
        with self._open(url, timeout=self.timeout) as resp:
            meta = json.loads(resp.read())
        if meta.get("objectIdField"):
            return meta["objectIdField"]
        return next(
            (f["name"] for f in meta.get("fields", []) if f.get("type") == "esriFieldTypeOID"), "OBJECTID"
        )

    def features(
        self,
        where: str,
        out_fields: str,
        key: str = "OBJECTID",
        page_size: int = 2000,
        extra: dict | None = None,
    ) -> Iterator[list[dict]]:
        """Yield pages of GeoJSON features in lon/lat (EPSG:4326).

        Pages by key (`key > last seen`), which stays fast deep into a large layer where offsets slow down.
        """
        last = None
        empty_tries = 0
        fields = out_fields if out_fields == "*" or key in out_fields.split(",") else f"{out_fields},{key}"
        while True:
            page_where = where if last is None else f"({where}) and {key} > {last}"
            params = {
                "where": page_where,
                "outFields": fields,
                "outSR": 4326,
                "orderByFields": key,
                "resultRecordCount": page_size,
                "f": "geojson",
                **(extra or {}),
            }
            try:
                body = self.query(params)
            except ArcGISError:
                # A page of large polygons can time out on the server (Hillsborough flood zones return an HTML
                # error page after about 40 seconds at 300 rows). Halve the page and try again.
                if page_size <= MIN_PAGE:
                    raise
                page_size = max(MIN_PAGE, page_size // 2)
                continue
            feats = body.get("features", [])
            if not feats:
                # Some servers now and then answer a page with no rows although rows remain (Houston's flood
                # layer did on 2026-11-19). Ask for the count before ending the layer.
                count_params = {k: v for k, v in params.items() if k not in ("outFields", "outSR", "orderByFields",
                                                                             "resultRecordCount")}  # fmt: skip
                left = self.query({**count_params, "returnCountOnly": "true", "f": "json"}).get("count", 0)
                if not left:
                    return
                empty_tries += 1
                if empty_tries > 3:
                    raise ArcGISError(
                        f"{self.layer_url}: empty pages while {left} rows remain past {key} {last}"
                    )
                self._sleep(self.backoff * 2**empty_tries)
                continue
            empty_tries = 0
            yield feats
            last = feats[-1]["properties"][key]
            # Some servers cap pages below the size asked for (Hillsborough County returns 999 of 1,000) and
            # never set exceededTransferLimit in GeoJSON, so only an empty page ends the layer, and only once a count
            # confirms nothing is left. That costs two extra requests per layer.
