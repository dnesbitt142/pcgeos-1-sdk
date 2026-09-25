# Advanced MiniCalc reference

This directory contains the source package used to build MiniCalc Native 0.4. It demonstrates techniques beyond the public 0.1 basic-shell API:

- menus and command triggers
- multiple GenText fields
- direct in-cell editing driven from a GenView
- native Open and Save As GenFileSelector dialogs
- title-bar Help and scrollable Help
- GEOS file-service adapters
- document save/rollback logic
- session-state handling
- a substantially larger C engine
- compiled-method test harnesses

The generated `MINICALC.GEO` is deliberately **not included in the SDK distribution**. Rebuild it from source with your own matching target archive.

The advanced example predates the generic `pcgeos1 build` driver and uses its own `TOOLS/build.py`, which is retained as a worked reference. Read its `TECHNICAL_REPORT.md` and `PROVENANCE.md` before adapting it.
