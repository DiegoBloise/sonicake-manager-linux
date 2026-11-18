# Preset JSON format

`sonicake-manager export [file]` writes the current edit buffer as JSON. With no file argument it prints the document to stdout.

```json
{
  "format": "sonicake-manager-preset",
  "version": 1,
  "app": { "name": "sonicake-manager", "version": "0.1.0" },
  "exportedAt": "2026-11-18T00:00:00Z",
  "slot": { "index": 61, "label": "F12", "name": "Chorus CL" },
  "state": { "...": "decoded state dump" }
}
```

`state` is the same object produced by `decode_state()`.

## Importing

`sonicake-manager import-preset FILE --yes` replays the replayable parts of the export into the **edit buffer**:

1. amp mode (`cloneMode`)
2. effect types from `selectedEffects`
3. parameters from `parameters`
4. module on/off from `moduleStates`
5. signal chain from `signalChain`
6. preset volume from `presetVolume`

It deliberately does **not**:

- set BPM — the device accepts BPM frames but does not persist the value;
- replay footswitch assignments — those frames are not hardware-validated yet;
- save to a user slot unless you also pass `--save-slot N --name NAME`.

Always inspect the export with a JSON viewer before importing. `--yes` is required because every write goes straight to the device's live edit buffer.

## Full backup/restore

A complete 100-slot backup is not implemented yet. It requires repeatedly selecting each preset (or another reliable dump path) and would create many device writes; it should be designed and validated separately.
