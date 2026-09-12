# Changelog

## v1.1.0 — 2026-09-13

**Critical fix for upload rejection / 打回问题的修复**

- **Removed `nircmd.exe`.** VirusTotal flagged it with 7 detections including
  `Misc.Riskware.NirCmd`, `NirCmd (PUA)` and `W32.Trojan.Gen` (riskware / PUA / trojan),
  which is why Flightsim.to rejected the upload.
  Volume now uses the Windows Core Audio session API instead of an external tool.
- **Fixed: audio kept playing after closing the app.** The tray "Exit" now stops `ffplay`
  before quitting, and any leftover `ffplay` from a previous crash is cleaned up on startup.
- **Fixed: volume changes could block the service** for up to 2 seconds (the retry loop ran
  inside the websocket event loop); playback commands now run on a worker thread.
- **New `ffplay.log`.** `ffplay`'s stderr is written to a log file instead of being discarded,
  so "no sound" issues can actually be diagnosed. If `ffplay` dies right after starting, the
  reason is also recorded in `cockpit.log`.
- **Packaged as `--onedir`** instead of `--onefile` (fewer antivirus false positives on the exe).
- Volume has a fallback backend: without the optional `pycaw` module it restarts `ffplay`
  with the new volume (~1s gap). Install `pycaw` for instant volume changes.

## v1.0.0 — 2026-09-09

- First public release: in-game toolbar panel for MSFS 2024 that plays live FM radio
  and real ATC feeds through a bundled `ffplay` audio engine.
