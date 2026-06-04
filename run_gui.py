import sys
from pathlib import Path

# Ensure the root directory is on the path so that traffic_analysis_gui can be imported
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from traffic_analysis_gui.main import main

if __name__ == "__main__":
    main()
