# Provenance and attribution

The starting implementation is the complete MiniCalc Native 0.3 package previously delivered in this conversation. The current executable is rebuilt from the included source and exact uploaded GWP2.zip templates. Original uploaded files are unchanged.

Native template sources: SPINTEXT.GEO for the primary/view/application skeleton; NOTEPAD.GEO for menus/triggers; VIEWER.GEO for the file selectors and native help controls; TERM.GEO for plain read-only text attributes. Their SHA-256 values are recorded in EVIDENCE/BUILD.json. The original sample-derived icon remains. Original embedded notices are retained where present; no claim of authorship is made over the historical binaries.

The supplied native MONO.FNT is read solely to check metrics and reconstruct the worksheet evidence frame. No font files are included or installed. Its fingerprint and metrics are in EVIDENCE/TARGET_AUDIT.json.

Public primary reference files consulted:

- https://raw.githubusercontent.com/bluewaysw/pcgeos/master/Include/input.def
- https://raw.githubusercontent.com/bluewaysw/pcgeos/master/Include/fontID.def
- https://raw.githubusercontent.com/bluewaysw/pcgeos/master/Include/Internal/fontDr.def

These public revisions are later than the supplied 1.x binaries. The exact template bytes and native disassembly, not an assumed later SDK ABI, control this build's class layout, hints and message numbers.

No real DOS/GEOS boot or native-window screenshot is supplied. EVIDENCE/WORKSHEET_RENDER.png is a worksheet-only reconstruction of compiled-method draw calls, not a screenshot of the running native UI.
