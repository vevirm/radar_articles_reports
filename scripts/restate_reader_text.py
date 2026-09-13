#!/usr/bin/env python3
"""Compatibility entry point for the no-API Deep Scan workflow.

The former manual API-backed reader-language generator has been retired. This
script now only prepares the offline Deep Scan package and never calls a model
API or reads an AI billing credential.
"""
try:
    from scripts.prepare_deep_scan_package import main
except ModuleNotFoundError:
    from prepare_deep_scan_package import main  # type: ignore

if __name__ == "__main__":
    main()
