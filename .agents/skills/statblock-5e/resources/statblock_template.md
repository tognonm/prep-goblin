# Template Fantasy Statblocks (D&D 5e)

````markdown
---
title: "{{NOME_CREATURA}}"
icon: "⚔️"
tags: [mostro, statblock]
tipo: "Creatura"
statblock: inline
stato: "bozza"
---

# {{NOME_CREATURA}}

```statblock
layout: Basic 5e Layout
name: "{{NOME_CREATURA}}"
size: Medium
type: umanoide
subtype: qualsiasi specie
alignment: neutrale
ac: 13
hp: 16
hit_dice: 3d8 + 3
speed: 9 m
stats: [12, 14, 12, 10, 11, 10]
saves:
  - dex: 4
skillsaves:
  - perception: 2
damage_vulnerabilities: ""
damage_resistances: ""
damage_immunities: ""
condition_immunities: ""
senses: Percezione passiva 12
languages: Comune
cr: "1/2"
traits:
  - name: Tratto di Esempio
    desc: Breve descrizione meccanica del tratto.
actions:
  - name: Spada corta
    desc: "*Attacco con arma da mischia:* +4 al tiro per colpire, portata 1,5 m. *Colpisce:* 5 (1d6 + 2) danni perforanti."
reactions: []
legendary_actions: []
```

*Fonte: Template generico (compila con dati SRD 5.1 o Homebrew).*
````

## Note sul Formato
- Le chiavi YAML (`name`, `ac`, `hp`, `stats`, `actions`, ...) sono lette direttamente da **Fantasy Statblocks** e **Atlas VTT `0.16.0`**: mantienile in inglese e localizza solo i valori.
- `stats` segue l'ordine `[FOR, DES, COS, INT, SAG, CAR]`.
- `cr` va sempre scritto come stringa (es. `"1/4"`, `"1/2"`, `"3"`).
- Includi `statblock: inline` nel frontmatter per rendere la creatura indicizzabile dal Bestiary e da Atlas VTT.
- Mantieni la nota rigorosamente sotto i **32 KB**.
