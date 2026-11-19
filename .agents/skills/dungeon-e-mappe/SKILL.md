---
name: dungeon-e-mappe
description: >-
  Crea, struttura e configura end-to-end dungeon, mappe tattiche, luci, muri, token e schede di stanza
  per D&D 5e con Obsidian e Atlas VTT 0.16.0. Gestisce l'analisi visiva della battlemap, il modello
  markdown a doppio livello (Nota di Luogo + DM Dashboard < 30 KB), gli H3 indicizzabili dai Note Pin,
  le passive pre-calcolate e la compilazione/validazione automatica dei file .atlasmap.
---

# Creazione e Montaggio Dungeon & Mappe (Atlas VTT `0.16.0`)

Questa skill governa l'intero ciclo di preparazione di un dungeon per **{{CAMPAIGN_NAME}}** e **Atlas VTT `0.16.0`**: dalla progettazione condivisa col Master fino al montaggio completo della scena `.atlasmap` (muri, porte, frane, luci ambientali, token e Note Pin) e alla verifica visiva.

---

## 1. Architettura a Doppio Livello & Regole Tecniche

```
<Vault>/
├── Luoghi/
│   └── [Nome Dungeon].md                                  <-- 1. NOTA DI COMPENDIO (Lore, storia, diagramma, ganci)
└── atlas-vtt/collections/{{ATLAS_COLLECTION}}/
    ├── notes/[Nome Dungeon] - Dashboard.md                <-- 2. DM DASHBOARD (< 30 KB, Linked Note Atlas, H3, statblock)
    ├── scenes/[Nome Scena].atlasmap                       <-- 3. SCENA ATLAS (muri, porte, luci, token, pin, drawings)
    └── encounters/encounter-*.json                        <-- 4. INCONTRI PRE-CONFIGURATI
```

### Vincoli Critici (`AGENTS.md` + Atlas `0.16.0`)
- **Limite 32 KB:** La DM Dashboard DEVE restare sotto i **30 KB** (limite hard Atlas `32768` byte).
- **Passive Pre-Calcolate & CD (`AGENTS.md` Regola 6):** Leggi i punteggi passivi del party in `AGENTS.md` / `campaign.config.json`. Usa sempre **`⚡ [Passiva Automatica — Nome PG]`** per CD ≤ passiva del PG e **`🎲 [Tiro Attivo — Abilità CD X]`** per tutto ciò che supera le passive o richiede azione attiva.
- **Statblock Ufficiali / SRD (`AGENTS.md` Regola 7):** Creature standard mantengono lo statblock di riferimento senza modifiche arbitrarie.
- **Coerenza Nomi Scena:** La proprietà `atlas_scene:` nella Nota di Compendio deve corrispondere al nome della scena in Atlas (`atlasRecord.name` in `scenes/scene-*.json`).
- **Tabella H3 Indicizzabili:** Ogni stanza o punto d'interesse pinnato sulla mappa deve avere un titolo `### N. Nome Stanza` identico (senza formattazione `*corsivo*` nel titolo) al `#Titolo` del relativo Note Pin.

---

## 2. Pipeline Operativa End-to-End (4 Fasi)

Usa lo script di supporto `.agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py`.

### Fase 1 — Analisi Visiva & Conferma Layout (Regola Master-as-Reviewer)
**Non compilare lore o stanze prima dell'OK del Master** (`AGENTS.md` Regola 5).
1. **Ispeziona la battlemap e verifica la griglia:**
   ```powershell
   python .agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py grid-preview "<path.atlasmap o immagine>" --out "scratch/grid_check.png"
   ```
   - **Check sfasamento mezza casella:** Controlla se i corridoi larghi 1 quadretto e i pilastri 1×1 cadono **dentro** le celle o a cavallo delle linee di griglia. Se sono sfasati di mezza casella (`size / 2`), aggiusta `grid.offsetX` o `grid.offsetY` (mantenendolo in `[0, size)`) finché i corridoi coincidono con le righe/colonne intere — così `snapToGrid` funzionerà senza far camminare i token sui muri.
2. **Proponi corrispondenza stanze al Master:**
   Identifica tutti gli ambienti reali disegnati, etichettali con lettere (`A`, `B1`, `C`, ...) in `scratch/` e concorda col Master:
   - Corrispondenza **Lettera sulla mappa ↔ Stanza / Encounter / Segreto**;
   - Eventuali **blocchi / frane / scorciatoie a senso unico** per guidare il ritmo dell'esplorazione.

### Fase 2 — Asset, Statblock, Token & Encounter
1. Verifica i file in `<Vault>/Mostri/` (statblock 5e conformi a `statblock-5e`).
2. Per creature senza token, genera/registra l'asset con `.agents/skills/atlas-token-art/scripts/register_token.py`.
3. Crea o verifica gli `encounters/encounter-*.json` in `<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`.

### Fase 3 — Nota di Compendio + DM Dashboard
1. Compila la Nota di Compendio (`<Vault>/Luoghi/...`) con diagramma Mermaid aggiornato ai collegamenti reali, descrizione sensoriale e agganci.
2. Compila la Dashboard usando `.agents/skills/dungeon-e-mappe/resources/dashboard_template.md`, assicurandoti che ogni Note Pin previsto abbia il suo `### H3` esatto e il file resti `< 30 KB`.

### Fase 4 — Montaggio della Scena `.atlasmap` & Verifica Visiva
> [!IMPORTANT] Prima di scrivere su `.atlasmap`
> Il tab della scena in Obsidian deve essere **chiuso PRIMA** di scrivere il file `.atlasmap` da script (altrimenti Atlas salva periodicamente o alla chiusura lo stato vecchio dalla RAM sopra le tue modifiche). Fai chiudere il tab al Master, esegui lo script e poi fai riaprire la scena.

1. **Rilevamento Luci Naturali dalla Mappa (cristalli, bracieri, torce, pozze):**
   ```powershell
   python .agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py detect-lights "<immagine>" --color amber --out "scratch/lights_check.png" --json "scratch/lights.json"
   ```
   - `color`: `cyan` (cristalli/quarzo), `amber` (torce/bracieri), `emerald` (acido/miasma), `purple` (rune arcane).
   - Imposta raggi realistici nell'unità della scena (es. metri: `1.5 m = 1 casella`, oppure piedi: `5 ft = 1 casella`).
   - **Regola anti-occlusione:** Ogni punto luce va tenuto ad almeno **`≥ 20 px`** (idealmente `≥ 25 px`) da qualsiasi muro o pilastro per evitare tagli del raycasting.
2. **Muri, Pilastri, Porte e Frane (`walls` + `drawings`):**
   - **`walls`:** Usa `"type": "solid"`, `"door"`, `"secret-door"` o `"window"`. Le porte sigillate usano `"door"` con `"locked": true`; le **porte segrete nascoste ai giocatori** devono usare `"type": "secret-door", "closed": true`. Disegna quadrati chiusi attorno ai pilastri interni per generare ombre tattiche reali.
   - **Frane Visive (`drawings` sul layer `"map"`):** Quando sigilli un corridoio disegnato come aperto sulla battlemap, disegna poligoni irregolari chiusi (`points[0] == points[-1]`, `"type": "pen"`, `"fill": "solid"`, `"layer": "map"`, `"locked": true`) subito davanti al muro solido.
3. **Illuminazione Dinamica vs Fog of War (`lighting` vs `fog`):**
   - **Preferisci un solo sistema:** Con muri, porte chiuse e `"lighting": {"enabled": true, "ambient": 0, "tokenVision": true, "exploredMemory": true}`, **lascia `fog: {}` vuoto**.
   - *(Usa la `fog` manuale solo su mappe aperte/senza muri o aree extra-segrete non schermate da muri.)*
4. **Token PG & Nemici (`tokens`):**
   - **Centratura:** Con `snapToGrid: true`, piazza tutti i token di taglia `1` sul centro esatto di caselle intere: `x = offsetX + (col + 0.5) * size`, `y = offsetY + (row + 0.5) * size`.
   - **PG:** Imposta `"assetId"`, `"playerCharacter": true`, `"vision": {"enabled": true}`, `"hp": {"current": ..., "max": ...}` e assegna una torcia `dnd5e-torch` a chi porta la luce nel party.
5. **Note Pin (`pins`):**
   - Collega ogni pin al formato `atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/<Nome> - Dashboard.md#<H3 Esatto>`.
6. **Verifica Visiva & Validazione Obbligatoria:**
   ```powershell
   python .agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py verify-scene "<path.atlasmap>" --out "scratch/verify.png"
   python .agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py validate "<path.atlasmap>" --dashboard "<path Dashboard.md>"
   ```
   Ispeziona `scratch/verify.png`, verifica zero errori e zero warning, e prima della sessione usa `--reset-test` per azzerare `exploredMask` e `diceLog` di eventuali prove.

---

## 3. Guida Rapida al Tavolo (Atlas `0.16.0`)

- **Tasto `H` (*Lighting Peek*):** Tienilo premuto per vedere la mappa con gli esatti occhi dei giocatori.
- **Aprire le Porte:** Clicca sulla porta sulla mappa — con Dynamic Lighting attivo, luce e vista attraversano subito la soglia.
- **Passare/Spegnere Torce:** Tasto destro sul token → *Carry light* → *None* / *Torch*.
- **Pulire Test di Esplorazione:** *Lighting settings → Forget explored areas* (oppure `--reset-test` via script).
- **Dashboard a Scomparsa:** Premi **`Tab`** (Linked Note) o clicca qualsiasi **Note Pin** sulla mappa.

---

## 4. Regole di Coerenza Narrativa (`AGENTS.md` Regola 5)

- **Nessuna Invenzione Spontanea di Nuovi Dungeon:** L'agente non inventa dungeon, santuari o cripte senza mandato esplicito del Master.
- **Flusso di approvazione:** Prima si concorda la mappa numerata con le lettere (`A`, `B`, `C`...) e la collocazione di nemici/segreti/blocchi; poi si generano testi e scena `.atlasmap`.
