# Standard per Note di Scena, Luoghi e Dashboard di Atlas VTT (`< 32 KB`)

Questo documento definisce le linee guida obbligatorie per la creazione e strutturazione delle note di luogo e delle DM Dashboard del vault, garantendo fluidità al tavolo e piena compatibilità con **Atlas VTT `0.16.0`**.

---

## 1. Il Modello a Doppio Livello: Luogo vs Scena / Dashboard

Nel vault distinguiamo chiaramente tra due livelli:
1. **Nota di Luogo (`<Vault>/Luoghi/...`)**: Descrizione generale, storia, fazioni, diagrammi e collegamenti macroscopici del compendio. Nessun limite rigido di dimensione.
2. **Dashboard di Scena (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/<Nome> - Dashboard.md`)**: Il modulo operativo ultra-compatto che il Master apre premendo **`Tab`** direttamente dentro Atlas VTT sulla mappa (Linked Note) e tramite i **Note Pin**.

---

## 2. Vincolo Tecnico Hard: Limite 32 KB di Atlas VTT
> [!IMPORTANT] Limite 32 KB (`32768 byte`)
> Atlas VTT `0.16.0` ignora file Markdown di Dashboard, statblock o note collegate che superano **32 KB** (`32768 byte`).
> - **Soglia operativa raccomandata:** Mantieni ogni DM Dashboard sotto i **30 KB** (idealmente tra `3 KB` e `24 KB`).
> - **Verifica automatica:** Controlla sempre con `python .agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py validate <scena.atlasmap> --dashboard <dashboard.md>` e `python scripts/lint_vault.py`.

---

## 3. Requisiti Obbligatori per le Note di Luogo / Compendio

Ogni nota di luogo canonica creata o espansa dagli agenti contiene:

### A. Frontmatter e Visibilità Schermo
```yaml
---
title: "Nome del Luogo"
icon: "🗺️"
tags: [luogo, insediamento]
visibilita_mappa: "player" # player (condivisibile), master (solo DM), teatro_della_mente (senza battlemap)
atlas_scene: "Nome Scena in Atlas" # opzionale
atlas_dashboard: "[[Nome Dashboard]]" # opzionale
stato: "bozza"
---
```

### B. Banner di Quick Link (in cima alla nota)
```markdown
> [!TIP] **Atlas VTT Quick Link**
> 🗺️ **Scena Atlas:** `Nome Scena` | 🛡️ **Dashboard Operativa:** [[Nome Dashboard]]
```

### C. Sezione "5 Secondi di Descrizione Sensoriale (Lettura per il DM)"
Un paragrafo breve leggibile ad alta voce quando il party arriva:
- **Vista:** Illuminazione, architettura, ombre e primo dettaglio notabile.
- **Udito:** Suoni di fondo, rumori improvvisi, eco o silenzio anomalo.
- **Olfatto / Atmosfera:** Odori caratteristici e temperatura.

### D. 3 Contatti Rapidi Improvvisati
Tre comparse pronte da giocare al volo se il party parla con qualcuno (solo se approvate dal Master o marcate come spunti opzionali):
- Nome/ruolo, dettaglio visivo in 1 frase, cosa vuole, frase tipica.

### E. Tabella Casuale `d6` (Obsidian Dice Roller)
Una tabella `d6` di eventi o spunti rapidi attivabile con `` `dice: 1d6` ``.

---

## 4. Requisiti per le Dashboard di Scena Atlas (`<Vault>/atlas-vtt/.../notes/`)
Le Dashboard caricate come **Linked Note** in Atlas VTT devono essere sintetiche, leggibili al volo e **rigorosamente `< 30 KB`**:
1. **Scheda Rapida di Sessione:** Tabella compatta con Livello Party, **Passive Pre-Calcolate dei PG** (`AGENTS.md` Regola 6), nemici presenti, CD principali e segreto chiave.
2. **Guida Tattica alle Stanze con Titoli `### H3` Indicizzabili:**
   - Ogni stanza o punto d'interesse collegato a un **Note Pin** sulla mappa deve avere un titolo `### <Etichetta>. <Nome>` (senza formattazione corsivo/grassetto nel titolo) **identico 1:1** all'ancora `#...` del `notePath` del pin.
   - Annota ogni prova con **`⚡ [Passiva Automatica — Nome PG]`** oppure **`🎲 [Tiro Attivo — Abilità CD X]`**.
3. **Statblock Inline 5e (o Link Diretti):** Blocchi ```` ```statblock ```` compatti per i nemici chiave (o link alle note in `<Vault>/Mostri/`), evitando duplicazioni inutili che gonfiano il file verso i 32 KB.
