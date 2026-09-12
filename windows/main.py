"""FlowPy — Professional Python IDE with Live Flowchart View.

TurcoDevelopStudio tarafından geliştirildi.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowpy.app import main

if __name__ == "__main__":
    sys.exit(main())


