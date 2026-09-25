# File I/O and Native File Dialogs

The basic SDK 0.1 runtime intentionally omits file services from the public C API. The advanced MiniCalc example contains the recovered design used successfully in its modeled instruction tests.

## Native file services used by the advanced example

The adapter wraps target kernel entry points for:

- open
- create
- read
- write
- close
- rename
- delete
- push directory
- pop directory

All services execute on the original native GEOS stack with interrupts enabled. The private C register state is saved before crossing into GEOS.

## Why that matters

Calling kernel file services while leaving GEOS on the private GCC stack would expose scheduler/file code to a stack layout that the operating system did not create. The advanced adapter therefore restores the real session stack first.

## Native Open and Save As

MiniCalc reconstructs the Viewer's native GenFileSelector dialogs. The selector owns directory and drive browsing. Selection notifications populate application fields; actual save occurs only from the explicit Save trigger.

A useful safety pattern is to keep three concepts separate:

1. directory currently being browsed;
2. currently opened document path;
3. user-entered destination filename.

Cancelling a dialog must not silently change the document's save directory.

## Transactional saving

The advanced example writes temporary master/view files, closes and validates them, renames previous versions to backups, installs new versions, and attempts rollback after failure.

This pattern is strongly recommended for old systems with limited filesystem guarantees.

## Promoting file I/O into the public SDK

A future 0.2 should expose a small stable API only after live GEOS tests confirm the recovered ordinals and error mappings across the target profile.
