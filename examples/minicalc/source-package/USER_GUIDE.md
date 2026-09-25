# MiniCalc Native 0.4 — User guide

## Before upgrading

Save each working worksheet to an MCS file using your current version. Keep a separate copy. Close GEOS, back up the previous MINICALC.GEO outside the active WORLD directories, and replace it with the new file. Use a test copy or snapshot first. Keep only one active version of the application. No GEOS.INI changes are needed.

This release targets the supplied GeoWorks Pro 1.2 interfaces and a 386 or newer. It has not been boot-tested. Earlier native versions and DOS MiniCalc use the same MCS working format, but an old unsaved private session snapshot is deliberately not accepted as current program state.

## VGA layout

The worksheet shows five columns and ten rows in a 512×280 view. The address field and formula bar have explicit compact widths, and the extra Enter/Revert buttons have been removed from the bar. Edit > Revert Edit remains available. File, Edit and View are the menus; Help belongs to the title bar.

The drawing coordinates and target-font widths are checked against the compact canvas. Actual outer-window sizing and placement depend on the installed specific UI and system-font settings and still require testing at 640×480. The worksheet is not a freely zoomable or arbitrarily resizeable grid in this build.

## Entering and editing directly in a cell

Click a cell. Typing starts a replacement input in that cell, with a steady caret. You do not need to click the Formula field or prefix the input with a cell address. For example, select B2 and type `100`, not `B2 100`.

To change part of an existing value or formula, double-click the cell, press F2, or choose Edit > Edit Cell. Its original input appears in the cell. A formula is shown as its expression, not its calculated result. Click inside an active edit to reposition the caret. Longer inputs scroll horizontally within the cell.

| Key | Behavior |
|---|---|
| Enter | Accept the edit and select the cell below. |
| Shift+Enter | Accept and move up. |
| Ctrl+Enter | Accept and remain in the cell. |
| Tab / Shift+Tab | Accept and move right / left. |
| Escape | Cancel an in-cell edit and restore the stored input. |
| F2 | Begin editing the existing input. |
| Left / Right | Move the caret during editing; otherwise select an adjacent cell. |
| Home / End | Move to the start/end of an edit; otherwise select column A/Z. |
| Shift+Left/Right/Home/End | Extend the in-cell text selection. |
| Ctrl+A | Select all text inside an active in-cell edit. |
| Backspace / Delete | Remove text during an edit. Delete outside an edit clears the cell; Backspace starts an empty replacement edit. |
| Up / Down | Accept any pending edit and select the cell above/below. |
| Ctrl+Home | Select A1 when not editing. |

The numeric keypad is supported using the native control-character codes. Input remains ASCII, with a maximum of 63 characters. Unsupported key combinations are passed on to the native superclass rather than inserted as text. Page movement is available through View; no additional Page Up/Down worksheet behavior is promised.

Clicking another cell accepts the pending edit first. An input rejected by the calculation core leaves the current selection in place. A formula syntax/calculation error can be stored and shown as an error value; that is different from an invalid/oversized cell input.

## The formula and address fields

The Formula field mirrors the selected cell's original input. It remains a genuine native text field and is useful for examining long formulas. Clicking in it uses normal native text editing; Enter accepts and moves down. Clicking a different cell commits the pending formula-field text first.

The canvas editor is implemented by MiniCalc using native keyboard and drawing services, not by a native text-field overlay. Its keyboard editing features are listed above; system clipboard operations inside the canvas are not implemented. Use the native Formula field for its standard text-control behavior.

The Cell field and Go jump to an address such as D50. Edit > Revert Edit discards an uncommitted input and returns focus to the worksheet. Edit > Clear Cell removes the selected cell. Edit > Undo / Redo provides one committed-action level; it is not a per-keystroke undo history.

## First calculation

Click A1 and type `10`, then Enter. Type `20`, then Enter. Type `=SUM(A1:A2)`, then Enter. A3 should show 30. Click A1 and type `100`, then Enter: A3 should show 120. Select A3 and press F2 to edit `=SUM(A1:A2)` inside the cell. Make a partial change and press Escape to confirm that the stored formula is retained.

## Native Open and Save As

File > Save As opens a native Ensemble 1.x file-selector dialog with a folder browser and separate filename field. Choose a test directory and a new DOS 8.3 filename, such as `VGA04.MCS`. Save writes both the MCS master and a WK1 values-only companion. Check the success status before continuing.

File > Open uses a native selector filtered to MCS files. Select a working master and use Open. Directory activation is left to the native selector. New/Open request Discard/Cancel when the current sheet has unsaved changes; Cancel keeps it, while Discard abandons those changes.

Ordinary Save uses the worksheet's saved disk and directory, not the last folder browsed in a cancelled dialog. Selecting an existing filename in Save As only fills the name field; it does not automatically save. Unrelated existing destination files are refused rather than silently overwritten. Use a new name for a new copy.

Each save creates `NAME.MCS` with editable original inputs/formulas and `NAME.WK1` containing values/text for viewing. Keep the MCS file. Arbitrary Quattro WQ1/WK1 import is still unsupported. Temporary files, previous-version backups and rollback checks reduce ordinary I/O risks, but do not guarantee safety during power loss. See `RECOVERY.md`.

## Native title-bar Help

Click Help on the title bar or press F1. The help content opens in the native Ensemble 1.x scrollable help-text dialog used as a template by the supplied Viewer. Use its scroll bar or Page Up/Page Down buttons, then Close. This is not the DOS GEOHELP program and not a painted worksheet help page. There is no separate help-file installation step.

The dialog contains usage, formula, saving and limitation topics. It is the simple 1.x help style, not the later Ensemble 2.x hyperlinked help system. Actual title-bar placement, scrolling and focus restoration must be checked in the running specific UI.

## Formulas, fill and limits

Supported arithmetic includes +, -, *, /, parentheses, percentages, ordinary cell references and ranges. Functions are SUM, AVERAGE, MIN, MAX, COUNT, ABS and ROUND. References such as `$A$1` remain fixed when copying. Changing an input recalculates dependent expressions. Invalid references, circular dependencies, division by zero and unsupported functions report errors explicitly.

Edit > Fill Range copies the selected cell to a destination such as B1:B10, adjusting relative references. It overwrites existing target cells and can be undone once. There is no mouse-drag range selection.

The worksheet limit is 256 populated cells across A1–Z999, 63 ASCII characters per input, and signed fixed-point arithmetic with four decimals (−214,748.3647 through +214,748.3647). There is one live instance and one worksheet. Charts, printing, multiple sheets, variable-width columns, drag selection and full native document-control integration remain absent.

Save explicitly before closing. Normal close attempts a same-build session snapshot, but it is not a guaranteed autosave or independent backup.

## Rolling back

Save MCS masters, exit GEOS, remove the new active geode, and restore your backed-up previous geode. Reopen MCS files explicitly. Do not leave two versions active, delete the entire STATE directory, or replace UI.GEO to work around an error. Keep the exact error and a screenshot for diagnosis.
