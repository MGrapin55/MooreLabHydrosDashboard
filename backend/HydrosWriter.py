"""Fetch Hydros sensor logs and append them to a dated TSV file."""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


## ---- Global Variables ---- ##
HYDROS_URL = os.getenv("HYDROS_URL", "https://api.coralvuehydros.com").rstrip("/")
OUTPUT_PREFIX = "MooreLab.Call."
TSV_FIELDS = ["timestamp", "resolution", "sensor_name", "sensor_type", "value", "unit"]
SUPPORTED_RESOLUTIONS = {"10m", "2h", "1d"}
UNITS = {
    "Tmp": "°C",
    "pH": "pH",
    "ORP": "mV",
    "DKH": "dKH",
    "Sal": "PSU",
    "Flo": "LPH",
}


## ---- Functions ---- ##
def CallAPI(
    provider_key_value: str,
    device_key_value: str,
    start_ms: int,
    end_ms: int,
    resolution: str,
) -> Dict[str, Any]:
    """Fetch log data for the requested time range and resolution."""
    query = urlencode({"start": start_ms, "end": end_ms, "resolution": resolution})
    request = Request(
        f"{HYDROS_URL}/api/v1/device/logs?{query}",
        headers={
            "Accept": "application/json",
            "Authorization": f"{provider_key_value}:{device_key_value}",
        },
    )
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def ParseJSON(data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """Convert the Hydros series response into flat, TSV-ready sensor rows."""
    resolution = data.get("resolution")
    if not isinstance(resolution, str):
        raise ValueError("Hydros response must contain a 'resolution' value")

    series_data = data.get("series")
    if not isinstance(series_data, dict):
        raise ValueError("Hydros response must contain a 'series' object")

    rows: List[Dict[str, Optional[str]]] = []
    for sensor_name, sensor in series_data.items():
        if not isinstance(sensor, dict):
            raise ValueError(f"Invalid series data for sensor {sensor_name!r}")

        sensor_type = sensor.get("type")
        points = sensor.get("points")
        if not isinstance(sensor_type, str) or not isinstance(points, list):
            raise ValueError(
                f"Sensor {sensor_name!r} must contain a type and points list"
            )

        for point in points:
            if (
                not isinstance(point, (list, tuple))
                or len(point) < 2
                or isinstance(point[0], bool)
                or not isinstance(point[0], (int, float))
            ):
                raise ValueError(
                    f"Invalid timestamp/value point for sensor {sensor_name!r}: "
                    f"{point!r}"
                )

            timestamp = datetime.fromtimestamp(
                point[0] / 1000, tz=timezone.utc
            ).isoformat()
            value = point[1]
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValueError(f"Invalid sensor value for {sensor_name!r}")

            rows.append(
                {
                    "timestamp": timestamp,
                    "resolution": resolution,
                    "sensor_name": sensor_name,
                    "sensor_type": sensor_type,
                    "value": None if value is None else str(value),
                    "unit": UNITS.get(sensor_type, ""),
                }
            )
    return rows


def TSVWriter(rows: List[Dict[str, Optional[str]]], output_file: Path) -> None:
    """Write a complete monthly result to a tab-separated file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as tsv_file:
        writer = csv.DictWriter(
            tsv_file,
            fieldnames=TSV_FIELDS,
            delimiter="\t",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def GarbageFiles(output_dir: Path, expiration_days: int) -> None:
    """Remove dated Hydros TSV files older than the configured retention period."""
    if expiration_days < 1:
        raise ValueError("HYDROS_EXPIRATION_DAYS must be at least 1")

    cutoff = (
        datetime.now(timezone.utc).timestamp() - expiration_days * 24 * 60 * 60
    )
    for output_file in output_dir.glob(f"{OUTPUT_PREFIX}*.tsv"):
        if output_file.is_file() and output_file.stat().st_mtime < cutoff:
            output_file.unlink()


def PreviousMonthRange(now: datetime) -> tuple[datetime, datetime]:
    """Return UTC start and end instants for the previous calendar month."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if end.month == 1:
        start = end.replace(year=end.year - 1, month=12)
    else:
        start = end.replace(month=end.month - 1)
    return start, end


## ---- Main Logic ---- ##
def main() -> None:
    # Environment variables you can define
    provider_key = os.getenv("HYDROS_PROVIDER_KEY")
    device_key = os.getenv("HYDROS_DEVICE_KEY")
    resolution = os.getenv("HYDROS_RESOLUTION", "1d")
    if not provider_key or not device_key:
        raise ValueError(
            "Set HYDROS_PROVIDER_KEY and HYDROS_DEVICE_KEY before running this script"
        )
    if not HYDROS_URL.startswith("https://"):
        raise ValueError("HYDROS_URL must use HTTPS")

    expiration_days = int(os.getenv("HYDROS_EXPIRATION_DAYS", "365"))
    if resolution not in SUPPORTED_RESOLUTIONS:
        raise ValueError(
            "HYDROS_RESOLUTION must be one of: "
            + ", ".join(sorted(SUPPORTED_RESOLUTIONS))
        )
    output_dir = Path(
        os.getenv("HYDROS_OUTPUT_DIR", str(Path(__file__).resolve().parent / "data"))
    )
    start_time, end_time = PreviousMonthRange(datetime.now(timezone.utc))
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    response_data = CallAPI(provider_key, device_key, start_ms, end_ms, resolution)
    response_resolution = response_data.get("resolution")
    if response_resolution != resolution:
        raise ValueError(
            f"Requested {resolution!r} resolution, but Hydros returned "
            f"{response_resolution!r}; refusing to write data."
        )
    rows = ParseJSON(response_data)

    output_file = output_dir / f"{OUTPUT_PREFIX}{start_time:%Y-%m}.tsv"
    TSVWriter(rows, output_file)
    GarbageFiles(output_dir, expiration_days)
    print(f"Wrote {len(rows)} sensor readings to {output_file}")


if __name__ == "__main__":
    main()
