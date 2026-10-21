"""Download the JPL DE440 excerpt the ephemeris reads: python -m twinsky_engine.fetch [directory]

The file is cut from NASA JPL's public DE440 with jplephem's excerpt command, which reads
only the needed byte ranges of the remote file: years 1760-2560 and only the Sun, Moon,
Earth and the five classical planets. The cut is deterministic, so the result is checked
against a fixed sha256.

The directory defaults to TWINSKY_EPHE_PATH, else ~/.twinsky-engine. Set
TWINSKY_DE440_SOURCE to a local de440.bsp to cut from it instead of the network.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

FILENAME = "de440_1760_2560.bsp"
SHA256 = "d0efcafe9c5037eb84ab0abcc938fabbc40445698f597a6d7fbe5d5cb86035c1"
START, END = "1760/1/1", "2560/1/1"
TARGETS = "1,2,3,4,5,6,10,301,399"
SOURCES = (
    "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp",
    "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de440.bsp",
)


def default_ephemeris_path() -> str:
    """TWINSKY_EPHE_PATH, else ~/.twinsky-engine."""
    return os.environ.get("TWINSKY_EPHE_PATH") or str(Path.home() / ".twinsky-engine")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_ephemeris(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / FILENAME
    if target.is_file() and _sha256(target) == SHA256:
        print(f"JPL ephemeris ready: {target}")
        return target
    local = os.environ.get("TWINSKY_DE440_SOURCE")
    errors = []
    for source in ((local,) if local else SOURCES):
        temporary = destination / f".{FILENAME}.download"
        temporary.unlink(missing_ok=True)
        try:
            subprocess.run([sys.executable, "-m", "jplephem", "excerpt", "--targets", TARGETS,
                            START, END, source, str(temporary)],
                           check=True, stdout=subprocess.DEVNULL, timeout=900)
            actual = _sha256(temporary)
            if actual != SHA256:
                raise RuntimeError(f"checksum mismatch: {actual}")
            os.replace(temporary, target)
            print(f"JPL ephemeris written: {target} (from {source})")
            return target
        except (subprocess.SubprocessError, OSError, RuntimeError) as exc:
            errors.append(f"{source}: {exc}")
        finally:
            temporary.unlink(missing_ok=True)
    raise RuntimeError("Could not obtain the JPL ephemeris: " + "; ".join(errors))


if __name__ == "__main__":
    fetch_ephemeris(Path(sys.argv[1] if len(sys.argv) > 1 else default_ephemeris_path()))
