---
name: improv-live
description: >-
  Generatore rapido di improvvisazione live al tavolo per D&D 5e basato sulle tabelle Markdown
  in <Vault>/Tabelle/ (compatibili con Obsidian Dice Roller e Atlas VTT randomTables). Usala in
  sessione quando il Master chiede al volo PNG, locali, inseguimenti, meteo, pericoli, trappole,
  bottino rapido o incontri casuali.
---

# Improvvisazione Live al Tavolo (`improv-live`)

Questa skill trasforma la chat in un assistente lampo da tavolo: esegue tiri reali sulle tabelle Markdown in `<Vault>/Tabelle/` tramite `scripts/roll_tables.py` e restituisce risposte compatte, subito leggibili in gioco.

---

## Regole Operative Live

1. **Tira sempre con lo script prima di rispondere:** non inventare i tiri a mente; esegui:
   ```powershell
   python .agents/skills/improv-live/scripts/roll_tables.py --list
   ```
   oppure `--preset <nome>` / `--file "<nome>" --table <indice|all>`.
2. **Formato risposta ultra-sintetico (massimo 6–8 righe):** il Master sta arbitrando in diretta. Restituisci:
   - **Scena / Oggetto / PNG** in 1–2 righe leggibili a voce alta.
   - **Meccanica 5e** (CD, danni, statblock suggerito o regola di prova sociale/inseguimento) in 1–2 righe.
   - **Passive del Gruppo già valutate** (lette da `AGENTS.md` / `campaign.config.json`) in 1–2 righe, usando **`⚡ [Passiva Automatica — Nome PG]`** per CD ≤ passiva e **`🎲 [Tiro Attivo]`** per CD superiori o azioni fisiche dichiarate.
   - **Spunto o bivio immediato** in 1 riga.
3. **Autorità Narrativa, Adattamento Locale e Staging Master (`AGENTS.md` Regola 5 & `live-improv-and-boundaries.md`):**
   - **Contesto della campagna:** verifica la posizione corrente del party in `<Vault>/Campagna/Stato del mondo.md` (o chiedi al Master) e adatta tono e dettagli delle tabelle alla regione attuale.
   - **Canone protetto:** ciò che esce da `improv-live` è **materiale estemporaneo di scena**. **NON salvare** direttamente in `<Vault>/Personaggi/`, `<Vault>/Luoghi/` o `Stato del mondo.md` senza mandato esplicito del Master.
   - **Prompt Proattivo Obbligatorio (SEMPRE in chiusura):** al termine di ogni generazione rilevante, chiudi sempre chiedendo:
     > *«Vuoi che lo annoti in `Registro Improvvisazioni.md` (così non ne perdiamo traccia) o lo lasciamo sfumare?»*
   - Se il Master risponde sì, aggiungi 1 riga pulita nella tabella appropriata di `<Vault>/Campagna/Registro Improvvisazioni.md` con data in-game, wikilink al luogo e stato `effimero` o `ricorrente`.
   - **NON inventare** templi, fazioni o PNG canonici: ancora i risultati alle note esistenti del Vault o lascia segnaposto `[a scelta del DM]` con 2 opzioni brevi.

---

## Comandi CLI (`scripts/roll_tables.py`)

| Scopo | Comando |
|---|---|
| Elenca tutte le tabelle e i preset | `python .agents/skills/improv-live/scripts/roll_tables.py --list` |
| Tira un preset configurato (es. demo) | `python .agents/skills/improv-live/scripts/roll_tables.py --preset demo-scena` |
| Tira su un file specifico | `python .agents/skills/improv-live/scripts/roll_tables.py --file "Tabella Demo" --table 0` |
| Tira tutte le sotto-tabelle di un file | `python .agents/skills/improv-live/scripts/roll_tables.py --file "Tabella Demo" --table all` |
| Ripeti `N` volte con seed riproducibile | `python .agents/skills/improv-live/scripts/roll_tables.py --preset demo-npc --count 2 --seed 42` |

### Personalizzare i Preset
Aggiungi le tue tabelle Markdown (`| dN | ... |`) dentro `<Vault>/Tabelle/` e definisci i tuoi preset in `campaign.config.json` (chiave `roll_table_presets`) oppure in `<Vault>/Tabelle/presets.json`. Qualsiasi tabella con intestazione `| d6 |`, `| d8 |`, `| d10 |`, `| d12 |`, `| d20 |`, `| d100 |` o `| d% |` viene indicizzata automaticamente!

---

## Esempio di Risposta Compatta al Tavolo

> **PNG al Volo — Corvus il Battelliere (molo fluviale)**
> - **Aspetto & Voce:** Mantello cerato e lanterna spenta alla cintura; tamburella le dita sul remo quando nasconde qualcosa. *(Statblock: Popolano o `Predone di Strada` disarmato).*
> - **Atteggiamento:** **Indifferente** — Carisma **CD 15** per ottenere informazioni riservate (**Vantaggio** se i PG offrono discrezione o riparo).
> - **Passive:** `⚡ [Passiva Automatica — Mira (Intuiz. 15)]` Capisce subito che non è ostile, ma teme occhi indiscreti lungo il molo.
> - **Nota DM:** Comparsa improvvisata. *Vuoi che lo annoti nel `Registro Improvvisazioni` (così non ne perdiamo traccia) o lo lasciamo sfumare?*
