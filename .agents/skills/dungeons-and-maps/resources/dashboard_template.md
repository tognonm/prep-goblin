---
title: "{{DUNGEON_NAME}} - Dashboard"
icon: "🗺️"
tags: [atlas, dashboard, dungeon, encounter]
collection: "{{ATLAS_COLLECTION}}"
clean_map: "[[{{MAP_IMAGE}}]]"
main_note: "[[{{DUNGEON_NAME}}]]"
status: "draft"
---

# 🛡️ DM Dashboard — {{DUNGEON_NAME}}
*(Operational module for Atlas VTT 0.16.0 & Fantasy Statblocks — keep strictly under 30 KB)*

> [!TIP] **Atlas VTT Quick Controls**
> Open the scene in Atlas, press **`Tab`** to toggle the **GM Dashboard**, and link this note as the **Linked Note**. Hold **`H`** to preview Dynamic Lighting through the players' eyes and click doors to open them live.

---

## ⚡ Quick Session Reference

| Parameter | Operational Detail |
| :--- | :--- |
| **Party Level** | {{PARTY_LEVEL}} |
| **👁️ Pre-Calculated PC Passives** | **[[Mira the Cleric\|Mira]]:** Perc. **13**, Ins. **15** \| **[[Kael the Rogue\|Kael]]:** Inv. **14** \| **[[Bram the Fighter\|Bram]]:** Ins. **12** *(Customize for your party!)* |
| **Quest Hook / Patron** | {{QUEST_HOOK}} |
| **Primary Foes** | {{ENEMIES_SUMMARY}} |
| **Key Secret** | {{KEY_SECRET}} |

---

## 🗺️ Tactical Room Guide (Passives & DCs)

### 1. {{ROOM_1_NAME}}
> [!quote] 👁️ Read-Aloud Description
> *{{ROOM_1_READ_ALOUD}}*

- **Atmosphere & Light:** {{ROOM_1_ATMOSPHERE}}
- **Enemies:** {{ROOM_1_ENEMIES}}
- **Checks & Pre-Calculated Passives:**
  - ⚡ **[Automatic Passive — {{PC_PASSIVE}}]:** {{PASSIVE_OBSERVATION}}
  - 🎲 **[Active Roll — Perception DC {{DC_1}}]:** {{ACTIVE_PERCEPTION}}
- **Treasure / Clues:** {{ROOM_1_LOOT}}
- **Exits:** {{ROOM_1_EXITS}}

### 2. {{ROOM_2_NAME}}
- **Atlas Encounter (1-Click):** `{{ENCOUNTER_2_NAME}}`
- **Atmosphere & Light:** {{ROOM_2_ATMOSPHERE}}
- **Enemies / Hazards:** {{ROOM_2_HAZARDS}}
- **Checks & Pre-Calculated Passives:**
  - 🎲 **[Active Roll — Investigation DC {{DC_2}}]:** {{ACTIVE_INVESTIGATE}}
- **Treasure / Clues:** {{ROOM_2_LOOT}}
- **Exits:** {{ROOM_2_EXITS}}

### 3. {{ROOM_3_NAME}}
- **Atlas Encounter (1-Click):** `{{ENCOUNTER_3_NAME}}`
- **Atmosphere & Light:** {{ROOM_3_ATMOSPHERE}}
- **Tactics:** {{ROOM_3_TACTICS}}
- **Checks & Pre-Calculated Passives:**
  - 🎲 **[Active Roll — Arcana / Religion DC {{DC_3}}]:** {{CLIMAX_CHECK}}
- **Final Reward:** {{ROOM_3_TREASURE}}

---

## 👹 Inline 5e Combat Statblocks

```statblock
layout: Basic 5e Layout
name: "{{MONSTER_NAME}}"
size: "Medium"
type: "humanoid"
alignment: "any"
ac: 12
hp: 11
hit_dice: "2d8 + 2"
speed: "30 ft."
stats: [11, 12, 12, 10, 10, 10]
senses: "passive Perception 10"
cr: "1/8"
actions:
  - name: "Melee Weapon"
    desc: "*Melee Weapon Attack:* +3 to hit, reach 5 ft., one target. *Hit:* 4 (1d6 + 1) slashing damage."
```
