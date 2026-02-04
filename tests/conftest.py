import sys
from pathlib import Path

# configure sys.path to include the project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
