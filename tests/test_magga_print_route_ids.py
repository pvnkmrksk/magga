"""magga_cli --print-top-route-ids (for process_transit_map.sh)."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "bmtc-2.zip"


@pytest.mark.skipif(not ZIP.is_file(), reason="bmtc-2.zip not present")
def test_print_top_route_ids_stdout_only():
    out = subprocess.check_output(
        [
            sys.executable,
            str(ROOT / "magga_cli.py"),
            str(ZIP),
            "--print-top-route-ids",
            "7",
        ],
        cwd=str(ROOT),
        text=True,
        stderr=subprocess.DEVNULL,
    )
    ids = out.strip().split(",")
    assert len(ids) == 7
    assert all(len(x) > 0 for x in ids)


@pytest.mark.skipif(not ZIP.is_file(), reason="bmtc-2.zip not present")
def test_print_top_route_ids_rejects_combined_flags():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "magga_cli.py"),
            str(ZIP),
            "--print-top-route-ids",
            "1",
            "--stats-dir",
            "/tmp",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "cannot be combined" in (r.stderr or "")
