#!/usr/bin/env python3
from pathlib import Path

here = Path(__file__).resolve().parent
parts = [here / f"evaluate-mark-matched-edge-geometry.part{i}.inc.py" for i in range(4)]
source = "".join(part.read_text(encoding="utf-8") for part in parts)
exec(compile(source, str(parts[0]), "exec"))
