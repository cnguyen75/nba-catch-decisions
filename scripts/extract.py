"""Extract each SportVU .7z archive into its own directory under DATA/json/<stem>/."""
import sys
from pathlib import Path

import py7zr

raw = Path(sys.argv[1])
out = Path(sys.argv[2])
for arc in sorted(raw.glob("*.7z")):
    dest = out / arc.stem
    if dest.exists() and any(dest.iterdir()):
        continue
    dest.mkdir(parents=True, exist_ok=True)
    with py7zr.SevenZipFile(arc) as z:
        names = z.getnames()
        assert all("/" not in n and ".." not in n for n in names), names
        z.extractall(dest)
    print(arc.name, names)
