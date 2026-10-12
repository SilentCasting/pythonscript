"""Allow ``python -m changeimagehash ...`` as an alias for the CLI."""

from changeimagehash.cli import main

raise SystemExit(main())
