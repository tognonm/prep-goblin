# Regola di Improvvisazione Live, Confini tra Skill ed Evoluzione Regionale

Questa regola integra `master-reviewer-autorita-narrativa.md`, `vtt-sync-boundaries.md`, `scene-and-dashboard-standards.md` e `session-lifecycle.md` per evitare sovrapposizioni tra le skill del repository e garantire che nulla vada perso durante il gioco improvvisato.

---

## 1. Matrice Anti-Sovrapposizione delle Skill

Ogni skill del workspace ha un perimetro distinto; gli agenti non devono mescolare i flussi:

| Skill | Quando si usa | Dove scrive | Cosa NON fa |
|---|---|---|---|
| **`improv-live`** | In diretta al tavolo per PNG, botteghe, inseguimenti, meteo, pericoli, trappole, bottino rapido e tabelle casuali. | Output in chat; su conferma del Master, 1 riga in `<Vault>/Campagna/Registro Improvvisazioni.md`. | Non crea note canoniche in `<Vault>/Luoghi/`, `<Vault>/Personaggi/` o `<Vault>/Lore/`. |
| **`griglia-lampo`** | Scontri improvvisati o deviazioni non previste (scene Jolly pre-pronte o generazione procedurale in 2–3s). | Scena `.atlasmap` + nota operativa breve in `<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/`. | Non crea Note di Compendio in `<Vault>/Luoghi/` né ritratti custom (usa token già presenti o fallback). |
| **`dungeon-e-mappe`** | Dungeon e luoghi tattici canonici preparati per la campagna. | Modello doppio livello completo (`<Vault>/Luoghi/...` + Dashboard `< 30 KB` + `.atlasmap` + Encounter). | Non si attiva per imboscate improvvisate usa-e-getta. |
| **`incontri-e-bottino`** | Bilanciamento PE formale, Hoard Treasure ed Encounter `.json` permanenti in Atlas. | `<Vault>/Incontri/`, `<Vault>/atlas-vtt/.../encounters/`. | Non sostituisce i tiri rapidi live di `improv-live`. |
| **Compendio Vault (`Luoghi/` / `Personaggi/` / `Lore/`)** | Unica via per promuovere o espandere luoghi, PNG e lore nel canone permanente (dopo OK Master). | `<Vault>/Luoghi/`, `<Vault>/Personaggi/`, `<Vault>/Lore/`. | Non registra comparse effimere prima della conferma del Master. |
| **`recap-sessione` & `mondo-vivo`** | Post-sessione: diario, avanzamento tempo/fazioni e triage del `Registro Improvvisazioni.md`. | `<Vault>/Sessioni/`, `<Vault>/Campagna/Stato del mondo.md`, `Fazioni/`, `Registro Improvvisazioni.md`. | Non inventa fatti non accaduti in sessione. |

---

## 2. Eccezione Controllata per `griglia-lampo` (VTT Sync & Dashboard)
In deroga circoscritta a `vtt-sync-boundaries.md` e `scene-and-dashboard-standards.md`, una scena generata con `griglia-lampo` o una scena `Jolly - *`:
- **Non richiede** una Nota di Luogo in `<Vault>/Luoghi/` né la generazione di nuovi ritratti in `<Vault>/Mostri/Ritratti/` o `<Vault>/Personaggi/Ritratti/`.
- Mantiene comunque tutti i vincoli tecnici di Atlas VTT `0.16.0` (schema `v4`, griglia coerente, `snapToGrid: true`, luci `>= 25 px` dai muri, `fog: {}`, scheda collegata `< 30 KB`, nessun edit manuale a `assets-metadata.json`).
- Se un luogo nato su una Griglia Lampo diventa ricorrente nella storia, viene promosso in un secondo momento a Nota di Luogo / `dungeon-e-mappe` dopo conferma del Master.

---

## 3. Staging Wiki Master & Prompt Proattivo Obbligatorio
Per tenere pulito il compendio canonico senza perdere mai traccia delle improvvisazioni di gioco:
1. **Staging unico del Master:** tutto ciò che entra realmente in gioco durante l'improvvisazione viene tracciato in `<Vault>/Campagna/Registro Improvvisazioni.md` (`visibilita: master`), collegato dal `DM Screen.md`.
2. **Prompt Proattivo Obbligatorio (Sempre):** ogni volta che l'agente genera un elemento tramite `improv-live` (PNG, locale, evento, documento/bottino rilevante) oppure una nuova scena on-demand tramite `griglia-lampo`, **DEVE SEMPRE** chiedere esplicitamente in chiusura di risposta:
   > *«Vuoi che lo annoti nel Registro Improvvisazioni (così non ne perdiamo traccia) o lo lasciamo sfumare?»*
3. **Scrittura solo su conferma:** l'agente non scrive nel registro finché il Master non conferma (così il Master può tirare più volte finché trova il risultato giusto); al sì del Master aggiunge 1 riga pulita con wikilink al luogo/regione reale.
4. **Triage Post-Sessione:** durante `recap-sessione` / `session-lifecycle.md`, l'agente passa in rassegna le voci recenti di `Registro Improvvisazioni.md` e propone al Master quali:
   - **Promuovere a compendio** (nota dedicata in `<Vault>/Personaggi/` o `<Vault>/Luoghi/`),
   - **Mantenere nel registro** come `ricorrente` / `effimero`,
   - **Archiviare / pulire** (es. scene lampo temporanee non più necessarie).

---

## 4. Respiro dell'Ambientazione & Scene Jolly Evolutive
- **Adattamento alla posizione del party:** le tabelle in `<Vault>/Tabelle/` e le scene procedurali sono agnostiche o adattabili: l'agente legge sempre la **posizione corrente del gruppo** in `<Vault>/Campagna/Stato del mondo.md` (o indicata dal Master) e modella i dettagli di tono, clima e autorità locale sulla regione attuale.
- **Scene Jolly evolutive per bioma / arco narrativo:** le scene `Jolly - *` di `griglia-lampo` evolvono insieme alla campagna:
  - **Set base universale:** `lavagna` (dry-erase), `vicolo` (urbano), `strada` (viaggio/fiume), `colline` (brughiera/rocce), `interno` (bottega/locanda).
  - **Espansione progressiva:** quando la campagna raggiunge nuovi biomi (paludi, foreste fitte, navi, ghiacciai, fortezze), l'agente può proporre nuovi preset e scene Jolly coerenti con la nuova area.
