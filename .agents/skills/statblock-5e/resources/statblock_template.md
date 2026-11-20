# Fantasy Statblocks Template (D&D 5e)

````markdown
---
title: "{{CREATURE_NAME}}"
icon: "⚔️"
tags: [monster, statblock]
type: "Creature"
statblock: inline
status: "draft"
---

# {{CREATURE_NAME}}

```statblock
layout: Basic 5e Layout
name: "{{CREATURE_NAME}}"
size: Medium
type: humanoid
subtype: any race
alignment: neutral
ac: 13
hp: 16
hit_dice: 3d8 + 3
speed: 30 ft.
stats: [12, 14, 12, 10, 11, 10]
saves:
  - dex: 4
skillsaves:
  - perception: 2
damage_vulnerabilities: ""
damage_resistances: ""
damage_immunities: ""
condition_immunities: ""
senses: passive Perception 12
languages: Common
cr: "1/2"
traits:
  - name: Example Trait
    desc: Brief mechanical description of the trait.
actions:
  - name: Shortsword
    desc: "*Melee Weapon Attack:* +4 to hit, reach 5 ft., one target. *Hit:* 5 (1d6 + 2) piercing damage."
reactions: []
legendary_actions: []
```

*Source: Generic template (populate with SRD 5.1 or Homebrew stats).*
````

## Format Notes
- Keep YAML keys (`name`, `ac`, `hp`, `stats`, `actions`, etc.) exact for **Fantasy Statblocks** and **Atlas VTT `0.16.0`**.
- `stats` order is `[STR, DEX, CON, INT, WIS, CHA]`.
- Always quote `cr` as a string (e.g., `"1/4"`, `"1/2"`, `"3"`).
- Always include `statblock: inline` in YAML frontmatter for automatic Bestiary & Atlas VTT indexing.
- Keep the note strictly under **32 KB**.
