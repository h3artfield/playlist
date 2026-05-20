"""POST a workbook through the dev proxy and direct API."""
from __future__ import annotations

import sys
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "data" / "imported" / "cloud" / "MAY 2026 BINGE GRIDS.xlsx"

BOUNDARY = "----testboundary"
body_start = (
    f"--{BOUNDARY}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{FILE.name}"\r\n'
    "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
).encode()
body_end = f"\r\n--{BOUNDARY}--\r\n".encode()
payload = body_start + FILE.read_bytes() + body_end

for label, url in [
    ("direct", "http://127.0.0.1:8765/api/content/import/parse"),
    ("vite", "http://localhost:5173/api/content/import/parse"),
]:
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={BOUNDARY}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read(500)
            print(f"{label}: OK {resp.status} {data[:120]!r}...")
    except Exception as exc:
        print(f"{label}: FAIL {exc}")
