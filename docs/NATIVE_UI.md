# Native UI Reconstruction

PC/GEOS generic UI objects contain class-specific binary instance data. SDK 0.1 does not invent those layouts. Instead it extracts complete object chunks from native target applications and changes only fields that have been verified through comparison and runtime-oriented work.

## Basic shell

The supported shell contains:

- application object
- primary window
- GenView
- native title-bar Help trigger
- native scrollable Help dialog

The view size is configured by `project.json`.

## Local-memory resources

`pcgeos1/ui.py` constructs a local-memory resource with:

- LMEM header
- handle table
- object/data chunks
- object flags
- 4-byte chunk alignment
- 16-byte resource padding

The code updates generic links for parent, next sibling, first child, moniker and hints while retaining unknown class-specific bytes from the native template.

## Advanced controls

The MiniCalc reference demonstrates recovered native templates for:

- menus
- GenTriggers
- GenText input fields
- read-only GenText displays
- GenFileSelector
- modal dialogs
- reply bars and default/cancel buttons
- title-bar Help

Developers can adapt `examples/minicalc/source-package/TOOLS/ui_builder.py`, but this is an advanced, target-specific path. Create a new target profile rather than assuming offsets are universal.

## Rule of thumb

If you cannot explain which native template supplied an object's class-specific bytes, do not ship an invented binary instance.
