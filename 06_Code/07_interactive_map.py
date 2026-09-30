"""Compatibility entry point for the version 1.2.0 offline research atlas.

The full frozen data must be extracted as described in REPRODUCE.md. This
 delegates to build_atlas.py; use --help for alternate input/output paths.
"""
from build_atlas import main

if __name__ == "__main__":
    main()
