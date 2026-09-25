# Development Safety

This SDK creates low-level executable files for an old operating environment. Mistakes can hang or crash GEOS and can corrupt documents if file operations are wrong.

- Develop against copied installations or emulator snapshots.
- Never replace your only copy of a system library or UI geode.
- Keep generated applications in a separate test directory until they are stable.
- Make application file writes transactional where practical.
- Treat malformed or unknown geodes as untrusted input; use the bounds-checked parser.
- Do not disable target hash checks merely to make a build pass.
- Keep a DOS-level rollback path when testing native applications.
