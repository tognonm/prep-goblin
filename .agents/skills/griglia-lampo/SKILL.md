---
name: griglia-lampo
description: >-
  Genera al volo in 2-3 secondi battlemap tattiche e scene complete Atlas VTT 0.16.0 (schema v4) per
  combattimenti improvvisati, oppure indirizza il Master a 5 preset Jolly (lavagna, vicolo, strada,
  colline, interno) configurati con griglia metrica/personalizzabile, muri, porte, luci dinamiche,
  token PG da campaign.config.json e nemici da <Vault>/Mostri/.
---

# Griglia di Battaglia Lampo (`griglia-lampo` — Atlas VTT `0.16.0`)

Questa skill risolve i combattimenti improvvisati durante le sessioni su **Atlas VTT `0.16.0`** con due modalità complementari: **0 secondi di attesa** tramite scene Jolly pre-pronte, oppure **generazione on-demand in 2–3 secondi** con nemici, dimensioni e illuminazione su misura.

---

## 1. Quando Usare le Scene Jolly vs Generazione On-Demand

### Modalità A — Zero Attesa: le 5 Scene Jolly Pre-Pronte
Puoi pre-generare nella tua collezione Atlas (`campaign.config.json` -> `atlas_collection`) **5 scene Jolly** sempre pronte all'uso (nessun nemico fisso, token PG del party già posizionati, muri/porte/luci già montati e scheda DM collegata):

| Scena Jolly Consigliata | Preset | Griglia | Luce Default | Uso Tipico al Tavolo |
| :--- | :--- | :---: | :---: | :--- |
| **`Jolly - Lavagna Tattica`** | `lavagna` | `16x12` | `giorno` | Tela avorio dry-erase quasi libera: il DM disegna muri/fiumi live con gli strumenti *Drawing* |
| **`Jolly - Vicolo Cittadino`** | `vicolo` | `16x12` | `crepuscolo` | Imboscate urbane, vicolo a T, coperture di casse/barili, magazzino con **2 porte apribili** e 2 lampioni |
| **`Jolly - Strada di Campagna`** | `strada` | `18x12` | `giorno` | Incontri su strada fluviale, carro fermo con coperture, 2 massi alti e canneti |
| **`Jolly - Colline Rocciose`** | `colline` | `18x12` | `crepuscolo` | Brughiera calcarea con 3 affioramenti rocciosi (linea di vista spezzata), menhir antico e focolare |
| **`Jolly - Interno Edificio`** | `interno` | `14x10` | `notte` | Bottega/locanda/casa generica: sala con bancone, tavoli e 2 colonne, retrobottega e **1 porta segreta** sul vicolo |

- **Come usarle in sessione:** Apri la scena dalla libreria *Scenes* di Atlas VTT, trascina i token nemici dalla libreria *Tokens* e gioca subito. Al termine, usa *Lighting settings -> Forget explored areas* per resettarla.

### Modalità B — Generazione On-Demand (2–3 Secondi)
Quando il Master chiede in chat una scena dedicata con nemici già piazzati, dimensioni diverse o una fascia oraria precisa, esegui lo script:

```powershell
python .agents/skills/griglia-lampo/scripts/quick_battlemap.py --preset <preset> [opzioni]
```

> [!IMPORTANT] Watcher Automatico di Atlas VTT e Sovrascrittura
> - **Nuove scene:** Atlas VTT `0.16.0` rileva e indicizza automaticamente via `reconcileWithVault` ogni nuovo `maps/map-*.json`, `scenes/scene-*.json` e `scenes/*.atlasmap` scritto nella collezione (**NON** modificare mai manualmente `assets-metadata.json` o `collection.json`).
> - **Sovrascrittura di scene esistenti (`--slug`):** Se rigeneri o sovrascrivi una scena già aperta in Obsidian, fai **chiudere prima il tab della scena** al Master, esegui lo script e poi falla riaprire.

---

## 2. Esempi di Richieste Rapide in Chat -> Comandi CLI

| Richiesta del Master in Chat | Comando Rapido |
| :--- | :--- |
| *"Griglia vicolo di notte con 2 predoni"* | `python .agents/skills/griglia-lampo/scripts/quick_battlemap.py --preset vicolo --name "Imboscata nel Vicolo" --lighting notte --enemies "Predone di Strada:2"` |
| *"Lavagna 16x12"* | `python .agents/skills/griglia-lampo/scripts/quick_battlemap.py --preset lavagna --name "Lavagna Rapida" --cols 16 --rows 12 --lighting giorno` |
| *"Colline con 3 scheletri"* | `python .agents/skills/griglia-lampo/scripts/quick_battlemap.py --preset colline --name "Scontro sulle Colline" --lighting crepuscolo --enemies "Scheletro Sentinella:3"` |
| *"Interno bottega con 2 guardie"* | `python .agents/skills/griglia-lampo/scripts/quick_battlemap.py --preset interno --name "Bottega - Scontro" --lighting notte --enemies "Guardia:2@11"` |
| *"Simula strada con 3 lupi da 11 PF"* | `python .agents/skills/griglia-lampo/scripts/quick_battlemap.py --preset strada --name "Strada - Lupi" --lighting crepuscolo --enemies "Lupo:3@11" --seed 77 --dry-run` |

---

## 3. Riferimento Parametri CLI (`scripts/quick_battlemap.py`)

- `--preset {lavagna,vicolo,strada,colline,interno}` *(obbligatorio)*: sceglie geometria, arte procedurale, muri, porte, luci e pin.
- `--name "<Nome Scena>"`: nome visibile in Atlas VTT e nome base di `.atlasmap`, `.thumb.jpg` e `notes/<Nome>.md`.
- `--cols <int>`, `--rows <int>`, `--cell <int>`: dimensioni griglia (min `10x8`, cella default `70` px).
- `--lighting {giorno,crepuscolo,notte}`: regola `ambient` (`1.0` / `0.35` / `0.0`), attiva la torcia `dnd5e-torch` sul PG portaluce configurato in `campaign.config.json` e accende lampioni/focolari.
- `--enemies "<Spec>"`: elenco separato da virgole, es. `"Predone di Strada:2,Scheletro Sentinella:1"`, `"Lupo:3@11"`. Legge dinamicamente `<Vault>/Mostri/*.md` e abbina i token registrati nella collezione (oppure i token fallback di `campaign.config.json`).
- `--collection <Nome>` / `--vault <Path>` / `--config <File>`: sovrascrivono i default di `campaign.config.json`.
- `--seed <int>`: varia la disposizione organica di rocce, cespugli e dettagli.
- `--slug <str>`: genera nomi file e ID deterministici e sovrascrivibili (es. `--slug jolly_vicolo`).
- `--no-pcs`: omette i token PG.
- `--dry-run`: simula, valida e stampa il riepilogo senza scrivere file.

---

## 4. Verifica e Regole di Sicurezza

1. **Validazione Post-Generazione:** Per scene destinate a rimanere nel Vault, verifica sempre zero errori e zero warning con:
   ```powershell
   python .agents/skills/dungeon-e-mappe/scripts/atlas_scene_tools.py validate "<Vault>/atlas-vtt/collections/<Collection>/scenes/<Nome>.atlasmap" --dashboard "<Vault>/atlas-vtt/collections/<Collection>/notes/<Nome>.md"
   ```
2. **Garanzie Tecniche Integrate:**
   - Schema Atlas VTT `0.16.0` (`version: 4`), `snapToGrid: true`, `offsetX/Y: 0`.
   - Tutti i token centrati su caselle intere percorribili, mai dentro muri o edifici chiusi.
   - Tutte le luci a `>= 25 px` da qualunque segmento muro.
   - Nessuna `fog` manuale sovrapposta al Dynamic Lighting (`fog: {}`).
   - Scheda collegata `< 5 KB` (ben sotto il limite `32 KB`) con `### H3` allineati 1:1 ai Note Pin e passive pre-calcolate lette da `campaign.config.json`.
3. **Prompt Proattivo Obbligatorio (`live-improv-and-boundaries.md`):**
   - Dopo aver generato una nuova scena on-demand, chiedi sempre al Master:
     > *«Vuoi che annoti questa scena in `Registro Improvvisazioni.md` (così a fine sessione decidiamo se tenerla o ripulirla)?»*
