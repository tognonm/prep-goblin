---
name: atlas-sound-moods
description: >-
  Creates, validates, and manages Moods (music playlists + ambient sound layers + spatial reverb)
  and automatic scene/combat mood links for Atlas VTT 0.19.0+ Music & Ambience. Use when the DM
  wants to configure soundtracks for dungeons, taverns, roads, or combat encounters, or audit
  audio records and .atlasmap sound bindings.
---

# Soundtracks & Moods for Atlas VTT (`0.19.0+`)

This skill manages the native **Music & Ambience** mixer introduced in **Atlas VTT `0.19.0`**:
- indexing local audio files into `<Vault>/atlas-vtt/sounds/records/sound-*.json`,
- building **Moods** (shuffled playlists + layered ambience + room reverb) in `<Vault>/atlas-vtt/sounds/moods/mood-*.json`,
- linking scenes automatically via `state.sound` (`mood` on scene open and `combatMood` when combat starts).

---

## 1. Folder Layout & Git Safeguards

```text
<Vault>/atlas-vtt/sounds/
├── music/      <-- Local audio binaries (.opus/.mp3/...)   [GITIGNORED]
├── ambience/   <-- Ambient loop binaries (.opus/.mp3/...)  [GITIGNORED]
├── records/    <-- Lightweight sound JSON (sound-*.json)   [TRACKED IN GIT]
└── moods/      <-- Lightweight mood JSON (mood-*.json)     [TRACKED IN GIT]
```

> [!CAUTION] Never Commit Heavy Audio Binaries
> `**/atlas-vtt/sounds/music/` and `**/atlas-vtt/sounds/ambience/` are excluded in `.gitignore` so large `.opus`/`.mp3` libraries stay local while lightweight JSON definitions (`records/` and `moods/`) remain versioned in Git.

---

## 2. Native Atlas VTT `0.19.0+` Schema

### A. Sound Record (`<Vault>/atlas-vtt/sounds/records/<id>.json`)
```json
{
  "format": 1,
  "id": "sound-campfire-1a2b3c4d5e",
  "name": "Campfire",
  "tags": [],
  "createdAt": 1795342117154,
  "modifiedAt": 1795342117154,
  "audioPath": "atlas-vtt/sounds/ambience/Campfire.opus",
  "audioSize": 1245184,
  "kind": "ambience"
}
```
- `kind`: `"music"` or `"ambience"`.
- **Idempotent ID Reuse:** Always check whether `records/` already contains a record for the same `audioPath` and reuse its `id` to avoid duplicate entries.

### B. Mood (`<Vault>/atlas-vtt/sounds/moods/<id>.json`)
```json
{
  "format": 1,
  "id": "mood-tavern",
  "name": "Cozy Tavern",
  "order": 0,
  "fadeSeconds": 4,
  "icon": "beer-stein",
  "tone": "amber",
  "room": "room",
  "music": {
    "tracks": ["sound-..."],
    "shuffle": true,
    "levelDb": -2
  },
  "layers": [
    { "sound": "sound-...", "levelDb": -10 }
  ]
}
```
- **Valid `room` values:** `room`, `hall`, `cave`, `cathedral`.
- **Valid `tone` values:** `gules`, `tenne`, `or`, `amber`, `vert`, `sea`, `azure`, `indigo`, `purpure`, `rose`, `earth`, `stone`.
- **Recommended `icon` crests:** `beer-stein`, `inn`, `city`, `hood`, `horse-head`, `campfire`, `forest`, `swamp`, `tombstone`, `coffin`, `dungeon`, `cave`, `crystal-ball`, `holy-symbol`, `combat`, `boss`, `skull-crossed-bones`, `candles`, `night-sky`.
- **`music`:** Playlist object (`tracks`, `shuffle`, `levelDb`, optional `reverb` `0..1`, optional `repeat`: `"one"`/`"off"`), or `"none"` (ambience-only), or `"keep"` (preserve current music while swapping ambience).
- **`layers`:** Up to 8 ambient layers, each with `sound`, `levelDb` (`-60..12`), and optional `reverb` (`0..1`).

### C. Automatic Scene Binding (`.atlasmap`)
Inside `state.sound`:
```json
"sound": {
  "mood": "mood-alley-shadows",
  "combatMood": "mood-combat-skirmish"
}
```
With **Follow scenes** enabled (*Atlas Settings → Music and ambience → Follow scenes*), Atlas crossfades automatically when switching scenes and shifts to `combatMood` the moment combat starts in the Initiative Tracker.

> [!IMPORTANT] Close Scene Tab Before `link-scene` / `link-all`
> Just like `dungeons-and-maps`, always **close the scene tab in Obsidian FIRST** before writing `state.sound` into an `.atlasmap` file (otherwise Atlas may overwrite disk edits from RAM). Running `build-moods` (which only writes to `sounds/records/` and `sounds/moods/`) is safe while Obsidian is open.

---

## 3. Tabletop Sound-Design Guidelines

1. **Prefer Instrumental Tracks During Play:** Pick `Instrumental/` subfolders when available so sung lyrics never compete with DM narration or roleplay.
2. **dB Mixing Targets (`levelDb`):**
   - **Music:** `0 dB` for combat; `-2 dB` for exploration, taverns, and investigation.
   - **Primary Ambience** (e.g., `Cave`, `Campfire`, `Quiet Forest`): **`-4 dB` to `-10 dB`**.
   - **Secondary Ambience** (e.g., distant `Thunderstorm`, night wind): **`-12 dB` to `-16 dB`**.
3. **Room Acoustics (`room` + `reverb`):**
   - Taverns, interiors, streets: `room` (no extra reverb).
   - Open hills, roads, large halls: `hall`.
   - Crypts, caves, subterranean ruins: `cave` with `reverb: 0.25–0.35`.
   - Monumental temples/cathedrals: `cathedral` with `reverb: 0.4`.
4. **Playlist Size:** Aim for 6–9 tracks with `shuffle: true` — varied enough for multi-hour sessions while keeping a coherent sonic identity.

---

## 4. CLI Workflow (`scripts/atlas_sound_tools.py`)

Starter template config: `.agents/skills/atlas-sound-moods/resources/moods_template.json`.

```bash
# 1. Inspect available local audio files, records, and moods
python .agents/skills/atlas-sound-moods/scripts/atlas_sound_tools.py inventory --list-ambience

# 2. Build/update sound records and moods from your campaign moods JSON
python .agents/skills/atlas-sound-moods/scripts/atlas_sound_tools.py build-moods path/to/campaign_moods.json

# 3. Link scene moods and combatMoods (close scene tabs in Obsidian first!)
python .agents/skills/atlas-sound-moods/scripts/atlas_sound_tools.py link-all path/to/campaign_moods.json
# Or link a single scene:
python .agents/skills/atlas-sound-moods/scripts/atlas_sound_tools.py link-scene "<path.atlasmap>" --mood mood-alley-shadows --combat-mood mood-combat-skirmish

# 4. Validate all sound records, moods, and scene links
python .agents/skills/atlas-sound-moods/scripts/atlas_sound_tools.py validate
```

---

## 5. Quick Table Hotkeys (Atlas VTT `0.19.0+`)

- **`S`** on the map → toggle the **Sound** tab in the DM Screen.
- **`Shift + S`** → fade out / resume all audio cleanly.
- **Online Player Audio:** Click **`Send sound to players`** in the Sound tab (and run **`Store all moods for players now`** before game night to pre-cache tracks).
