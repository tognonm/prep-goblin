---
title: "{{DUNGEON_NAME}} - Dashboard"
icon: "🗺️"
tags: [atlas, dashboard, dungeon, incontro]
collection: "{{ATLAS_COLLECTION}}"
mappa_pulita: "[[{{MAP_IMAGE}}]]"
nota_principale: "[[{{DUNGEON_NAME}}]]"
stato: "bozza"
---

# 🛡️ DM Dashboard — {{DUNGEON_NAME}}
*(Modulo operativo per Atlas VTT 0.16.0 e Fantasy Statblocks — tenere rigorosamente sotto i 30 KB)*

> [!TIP] **Nota di Utilizzo in Atlas VTT**
> Apri la scena su Atlas, premi **`Tab`** per aprire la **GM Dashboard** e seleziona questa nota come **Linked Note**. Tieni premuto **`H`** per vedere ciò che vedono i giocatori con Dynamic Lighting attivo e clicca sulle porte per aprirle.

---

## ⚡ Scheda Rapida di Sessione

| Parametro | Dettaglio Operativo |
|---|---|
| **Livello Party** | {{PARTY_LEVEL}} |
| **👁️ Passive PG (Pre-Calcolate)** | **[[Mira la Chierica\|Mira]]:** Perc. **13**, Intuiz. **15** \| **[[Kael il Ladro\|Kael]]:** Indag. **14** \| **[[Bram il Guerriero\|Bram]]:** Intuiz. **12** *(Aggiorna con il tuo party!)* |
| **Committente / Gancio** | {{QUEST_HOOK}} |
| **Avversari Principali** | {{ENEMIES_SUMMARY}} |
| **Segreto Chiave** | {{KEY_SECRET}} |

---

## 🗺️ Guida alle Stanze (Tattica, Passive Pre-Calcolate & CD)

### 1. {{ROOM_1_NAME}}
> [!quote] 👁️ Cosa vedono i giocatori
> *{{ROOM_1_READ_ALOUD}}*

- **Atmosfera & Luce:** {{ROOM_1_ATMOSPHERE}}
- **Nemici:** {{ROOM_1_ENEMIES}}
- **Prove & Passive Pre-Calcolate:**
  - ⚡ **[Passiva Automatica — {{PG_PASSIVE}}]:** {{PASSIVE_OBSERVATION}}
  - 🎲 **[Tiro Attivo — Percezione CD {{DC_1}}]:** {{ACTIVE_PERCEPTION}}
- **Tesoro / Indizi:** {{ROOM_1_LOOT}}
- **Uscite:** {{ROOM_1_EXITS}}

### 2. {{ROOM_2_NAME}}
- **Incontro Atlas pronto al click:** `{{ENCOUNTER_2_NAME}}`
- **Atmosfera & Luce:** {{ROOM_2_ATMOSPHERE}}
- **Nemici / Pericoli:** {{ROOM_2_HAZARDS}}
- **Prove & Passive Pre-Calcolate:**
  - 🎲 **[Tiro Attivo — Indagare CD {{DC_2}}]:** {{ACTIVE_INVESTIGATE}}
- **Tesoro / Indizi:** {{ROOM_2_LOOT}}
- **Uscite:** {{ROOM_2_EXITS}}

### 3. {{ROOM_3_NAME}}
- **Incontro Atlas pronto al click:** `{{ENCOUNTER_3_NAME}}`
- **Atmosfera & Luce:** {{ROOM_3_ATMOSPHERE}}
- **Scontro Tattico:** {{ROOM_3_TACTICS}}
- **Prove & Passive Pre-Calcolate:**
  - 🎲 **[Tiro Attivo — Arcano / Religione CD {{DC_3}}]:** {{CLIMAX_CHECK}}
- **Ricompensa Finale:** {{ROOM_3_TREASURE}}

---

## 👹 Statblock 5e per il Combattimento

```statblock
layout: Basic 5e Layout
name: "{{MONSTER_NAME}}"
size: "Medium"
type: "humanoid"
alignment: "any"
ac: 12
hp: 11
hit_dice: "2d8 + 2"
speed: "9 m"
stats: [11, 12, 12, 10, 10, 10]
senses: "Percezione passiva 10"
cr: "1/8"
actions:
  - name: "Arma da mischia"
    desc: "*Attacco con arma da mischia:* +3 al tiro per colpire, portata 1,5 m. *Colpisce:* 4 (1d6 + 1) danni."
```
