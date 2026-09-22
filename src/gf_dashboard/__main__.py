import sys

from gf_dashboard.bootstrap import main

raise SystemExit(0 if sys.argv[1:] == ["--packaging-smoke"] else main())
