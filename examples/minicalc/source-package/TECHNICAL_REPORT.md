# MiniCalc Native 0.4 — Technical report

## Result and validation boundary

This build modifies the actual native Ensemble 1.x spreadsheet in response to three reported problems: excessive window width, no editing inside the selected cell, and non-native Help placement/content. The output is `107,650` bytes, with `31,798` bytes in its code resource. It remains a 12-resource 1.x geode requiring kernel protocol 622.3 and UI protocol 693.0. There is no DOS executable launch or Ensemble 2.x library dependency.

**This build was not boot-tested in DOS/GEOS.** Tests exercise compiled methods and binary structures, not the real loader, object builder, specific UI, display driver, scheduler or physical keyboard. The user's earlier report establishes behavior of the previous build, not runtime validation of this new one.

```text
MINICALC.GEO SHA-256
0d3de500b3d6cce7da9f654fd4c5a035e1c0630a9479e800e973bab56a62652a
```

## 1. VGA layout

The previous formula bar cloned the sample's 216-point text-field width for the address field as well as the formula editor. Adding labels and buttons made the bar wider than the intended worksheet. The new address field has an explicit width of 42; the formula field has width 294. Enter/Revert are no longer additional inline buttons. Enter remains the commit key; Revert and Edit Cell are menu actions.

The native GenView initial and maximum sizes are now 512×280 rather than 552×308. The grid starts at (32,24), has five columns of width 92 and ten rows of height 20. Drawing, hit testing, scrolling the edit text and selection borders use the same constants in `SRC/ui_layout.h`. Status text is kept below the grid within the same canvas. Static checks cover all recorded primitive coordinates and the native object dimensions.

This is a conservative content-size target for 640×480, not a measurement of the outer window in a running UI. Native borders, menu/title metrics and any substituted system fonts are outside the renderer model. Unusually enlarged system-font settings and alternate specific UIs remain live checks.

The worksheet uses the target's native URW Mono font ID 0x1A00 at 10 points. The supplied MONO.FNT's plain 10-point face has an advance of exactly six points for all 95 printable ASCII characters; the target audit verifies these metrics. That avoids guessing proportional-font caret positions. Native menus, formula fields and dialogs continue using their own system text controls. **No font file is included.**

## 2. Actual in-cell editing

The process class now handles native message 0x007B for keyboard input, in addition to pointer selection 0x00C3. Selection requests focus on the GenView at chunk 0x003E, rather than on the Formula text object. The view's native control-character-forwarding bit (0x0040) is enabled alongside its existing focusable bit. This bit was identified in the supplied specific UI's key-dispatch code, not substituted from a later SDK definition.

The new editor maintains a caret, anchor and horizontal scroll offset in the live input. Printable typing replaces a selected cell's old input; F2/double-click starts editing its original expression. Left/Right/Home/End adjust the caret, Shift extends text selection, Ctrl+A selects the input, and Backspace/Delete edit it. Enter/Tab and their Shift variants commit and navigate. Escape restores the stored input without applying a partial edit. Numeric-keypad control characters are normalized to their ASCII equivalents.

The native view handles function-key accelerator routing separately from ordinary printable characters. F1 and F2 therefore also have genuine native trigger shortcuts (0x0F80 and 0x0F81), using the encoding observed in the supplied native applications. F2 targets Edit Cell; F1 targets Help. The process handler still recognizes those keys if they arrive directly. Unhandled keys use the original superclass path.

In-cell editing is application code using native GEOS keyboard, focus, font and graphics services. It is **not a GenText instance superimposed on the grid**. The existing Formula field is retained as a real native text control and mirrors the input for long-form editing. Its native text selection initialization was also corrected from the previous modifier value to the actual left-Shift+Home flags (0x0804 rather than 0x8004).

The caret is steady, not timer-blinked. Mouse drag selection, canvas clipboard commands and per-keystroke undo are not implemented. The existing committed-operation undo and document safeguards remain in place.

## 3. Title-bar Help and the native 1.x help viewer

The Help menu and painted worksheet help branch have been removed. The new Help trigger is a direct clone of the supplied Viewer's primary-resource Help trigger (resource 28, chunk 0x0056), with the same hint bytes `01 42 04 00 44 40 04 00`. The native specific UI recognizes hint 0x4044 for the corresponding placement role. The trigger's destination is changed to MiniCalc's Help action, and F1 is registered as its shortcut.

The help window is built from the supplied Viewer's actual resource-12 help controls:

| Original Viewer control | New MiniCalc chunk | Retained native role |
|---|---|---|
| Root 0x0022 | 0x00A0 | GenInteraction help dialog, flags 0x4A |
| Text 0x0032 | 0x00A2 | Scrollable, read-only GenTextDisplay |
| Reply bar 0x003C | 0x00A4 | Native reply group |
| Page Up 0x0044 | 0x00A6 | Native text message 0x226B |
| Page Down 0x0048 | 0x00A8 | Native text message 0x226C |
| Close 0x0040 | 0x00AA | Native automatically dismissing trigger |

The original Viewer's logo/artwork and external references are not copied. Its old style-run offsets are not reused against different text. Instead the text uses the plain native character attributes already present in the target's Terminal read-only text display. The display width is 400, with 12 visible lines; its native scrolling attributes and help hints are retained. `SRC/HELP.TXT` is embedded as CR-separated native text in the UI resource.

This is the simple Ensemble 1.x scrollable help-text viewer used by the native template, not the later hyperlinked 2.x help controller. It does not invoke the archive's DOS `GEOHELP.EXE`. No separate help file or system configuration is installed. The help request does not replace the worksheet or commit a pending edit. Real native modality, title-bar placement, scrolling and return of focus remain untested.

## 4. Binary structure and continuity

There are 30 process methods and 53 native generic UI objects. Method tables, class ordinals, local-memory chunk bounds and complete tree links are checked. The method table ends before the private native dgroup state area. Imported UI protocol/classes are checked against the supplied target library; the only imported library remains `ui`.

The engine resource remains 65,520 bytes, with its used-data end at 53,184 and 12,320 bytes between that end and the initial private stack. The native adapter still restores the real GEOS stack before native calls and simulated interrupt windows; tests scramble upper register halves during those windows to check preservation. The source fingerprint and private-state tag change, so older private snapshots are not accepted as the current engine workspace. This is not a substitute for saving MCS masters before upgrading.

The calculation core and document codec are byte-identical source files to 0.3. The MCS format, WK1 values-only export, checksum checks, save-pair safeguards and restrictions on unrelated Quattro workbooks are unchanged. `ENGINE_CONTINUITY.json` records the source hashes. File browser cancellation still cannot redirect the current worksheet's saved directory.

## 5. Validation performed

142 tests passed: 42 core/document tests, 32 hosted editor/model tests, 21 binary/object structure tests and 47 native execution scenarios. The native scenarios execute the compiled instruction bytes, with resolved recorded relocations and modeled GEOS service responses. The CPU probe is bypassed by the test adapter; this does not validate a real loader, native object system or screen.

New cases cover the complete key-event 30→120 calculation, actual partial formula editing, double-click BP flags, cancel, selection replacement, Ctrl+A, keypad numbers, arrow/Tab navigation, source formula preservation, native Help requests, function-key trigger metadata, long-input scrolling and caret bounds. Existing tests still cover native open/save/reopen, working-format compatibility, changed-destination protection, cancellation and injected I/O failures.

The target font audit verifies the six-point caret advance for all printable ASCII characters. A draw-call reconstruction of one actual compiled-method frame is included as `WORKSHEET_RENDER.png`. It uses the original target bitmap glyphs but does not render native chrome or dialogs and is **not a GEOS screenshot**.

`TEST_SUMMARY.json` gives the final count and executable fingerprint. Native test results were collected in four bounded batches to fit the execution environment's per-command limits; their scenario names are unique and total 47. Interrupted attempts were excluded from the final result. The executable also reproduced byte-for-byte in a fresh build.

## 6. Reproduction and installation

Python 3.10+, GCC with `-m16` support and GNU binutils build the geode from source. Native instruction tests additionally require Linux x86-64 and `modify_ldt`; these are development requirements, not requirements on the GEOS machine. Pillow is only needed for the optional evidence renderer.

```sh
python TOOLS/build.py --gwp /path/to/GWP2.zip
python TOOLS/audit_target.py --gwp /path/to/GWP2.zip
python TOOLS/test.py
python TOOLS/render_worksheet.py --gwp /path/to/GWP2.zip
```

The builder reads the hash-locked original archive and writes this package's output, not the user's installed system. Install only MINICALC.GEO in the existing application location after saving documents and exiting GEOS. Keep the previous geode outside active WORLD directories for rollback. No INI/library/UI changes are required.

## Source references and limits

Exact resource indices, offsets, hints, protocols and template bytes above are observations from the supplied GWP2.zip and the rebuilt executable. The original Viewer help resource and the specific UI's focus/key/hint-dispatch code are the controlling references for the 1.x layout. Later public definitions were used only to interpret stable record concepts and cross-check encodings, not as an exact build-matched SDK.

Public primary references consulted: `bluewaysw/pcgeos`, `Include/input.def` (character, modifier and button records), `Include/fontID.def` (font-family numbering), and `Include/Internal/fontDr.def` (bitmap font and character-table structures). See `PROVENANCE.md` for the source locations and input hashes.
