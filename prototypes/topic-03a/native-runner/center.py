"""Called by the live native integration while both Multica tasks are active."""
from pathlib import Path
import os
import sys

from exchange import center

os.umask(0o077)
center(Path(sys.argv[1]))
