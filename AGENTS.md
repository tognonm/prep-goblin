# Convenzioni del Vault: {{CAMPAIGN_NAME}}

> **Template di Governance:** Sostituisci `{{CAMPAIGN_NAME}}`, il percorso del vault (`Vault/` oppure `template-vault/`), il nome della collezione Atlas (`Campaign`) e i dati del party qui sotto e in `campaign.config.json` per adattare il framework alla tua campagna.

Questo file definisce le regole base che tutti gli agenti (e il Dungeon Master) devono seguire quando operano nel vault di **{{CAMPAIGN_NAME}}** con **Obsidian** e **Atlas VTT `0.16.0`**.

---

## 1. Struttura delle Directory e Nomenclatura
*(Sostituisci `template-vault/` con `Vault/` quando inizi la tua campagna vera e aggiorna `vault_dir` in `campaign.config.json`.)*

- **`<Vault>/DM Screen.md`**: Pannello centrale di consultazione live del Master.
- **`<Vault>/Lore/`, `<Vault>/Luoghi/`, `<Vault>/Personaggi/`**: Note di compendio canoniche. I ritratti dei PNG vengono salvati in `<Vault>/Personaggi/Ritratti/`.
- **`<Vault>/Campagna/`**: Stato del mondo, archi narrativi, fazioni (`Fazioni/`), schede giocatori (`Giocatori/`), missioni (`Quest/`) e `Registro Improvvisazioni.md`.
- **`<Vault>/Sessioni/`**: Prep modulari di sessione, recap e `Diario di Campagna.md`.
- **`<Vault>/Oggetti/`**: Oggetti magici, equipaggiamento, artefatti e database di bottino (`.base`). Le immagini vengono salvate in `<Vault>/Oggetti/Immagini/`.
- **`<Vault>/Mostri/`**: Note contenenti statblock per Obsidian Fantasy Statblocks. I ritratti dei mostri vengono salvati in `<Vault>/Mostri/Ritratti/`.
- **`<Vault>/Incontri/`**: Piani degli incontri bilanciati e ricompense.
- **`<Vault>/Tabelle/`**: Tabelle casuali in formato Markdown rollabile (compatibile con Obsidian Dice Roller, Atlas `randomTables` e `roll_tables.py`).
- **`<Vault>/Handout/`**: Materiale da mostrare ai giocatori senza segreti DM.
- **`<Vault>/atlas-vtt/`**: Asset, mappe, scene, token, dashboard ed encounter gestiti dal plugin **Atlas VTT `0.16.0`**.
- **`Fonti/`** *(opzionale, locale, in `.gitignore`)*: Eventuali manuali personali protetti da copyright (sola lettura, **MAI** committare su Git).
- **Nomenclatura file:** Nomi chiari e coerenti nella lingua della campagna (spazi consentiti). Evita caratteri riservati (`< > : " / \ | ? *`).

---

## 2. Formattazione Frontmatter
Tutte le note Markdown devono avere un frontmatter YAML valido. Le proprietà che indicano relazioni devono essere formattate come liste di wikilink tra virgolette (es. `luogo: ["[[Borgo di Oakhaven]]"]`).

**Schema base:**
```yaml
title: "Nome della nota"
icon: "🗺️" # Emoji coerente per Iconize
tags: [tipo_entita] # es: luogo, personaggio, lore, oggetto
tipo: "Sottotipo" # es: Taverna, Dungeon, Oggetto Meraviglioso
stato: "bozza" # bozza, pronto, giocato. Le note nuove nascono in bozza.
```

---

## 3. Scrittura e Stile
- **Lingua:** Coerente con la lingua scelta per la campagna (default di questo template: Italiano). Nessuna emoji invasiva nel corpo del testo narrativo, salvo nei titoli o callout operativi per leggibilità al tavolo.
- **Wikilink:** Collega sempre nomi propri a note esistenti usando `[[Nome]]` o `[[Nome|Alias]]`. Verifica l'integrità dei link con `python scripts/lint_vault.py`.
- **Segreti del DM:** Qualsiasi informazione nascosta ai giocatori DEVE essere isolata in un callout (es. `> [!danger] Segreto del DM`) oppure contrassegnata nel frontmatter con `visibilita: master`.

---

## 4. Workflow e Autonomia
1. L'agente legge prima il contesto attivo (`Stato del mondo.md` e note collegate).
2. Modifica o crea file rispettando tutte le regole in `.agents/rules/`.
3. Le nuove note create dall'agente nascono di default con `stato: "bozza"`, salvo diversa indicazione esplicita del Master.
4. Nessuna modifica a cartelle di riferimento in sola lettura (es. `Fonti/`).

---

## 5. Autorità Narrativa e Master-as-Reviewer (Regola Assoluta)
- **Il Master è l'unica autorità canonica:** L'agente NON introduce né dà MAI per scontati elementi narrativi nuovi o non approvati (nomi di PNG, contatti, legami tra fazioni, nuovi dungeon con lore, o il testo esatto di lettere e handout).
- **Divieto di Invenzione di Luoghi, Templi o Istituzioni:** L'agente non può presumere o inventare edifici, templi, santuari o confraternite non documentati nel Vault o non confermati dal Master. Prima di citare qualsiasi luogo o istituzione, verifica sempre con una ricerca nel Vault.
- **Distinzione tra Meta-Intento e Contenuto:** Se il Master esprime un'idea aperta (es. *«vorrei che indagassero in città, magari in un tempio»*), l'agente NON la trasforma arbitrariamente in un'entità specifica, ma chiede a quale istituzione esistente agganciarla o propone 2–3 opzioni da approvare.
- **Chiedere e proporre sempre prima:** Quando manca un elemento narrativo, l'agente presenta 2–3 opzioni sintetiche o una bozza circoscritta e attende l'approvazione del Master prima di scrivere nel canone.
- **Autonomia limitata agli aspetti tecnici:** L'agente agisce in autonomia solo su aspetti tecnici e regolistici (budget PE, statblock 5e, script VTT, validazione `.atlasmap`, sintassi YAML/wikilink) e su lore già approvata dal Master.

---

## 6. Prove di Abilità e Passive Pre-Calcolate nelle Dashboard
Per evitare che il Master debba confrontare a mente i punteggi passivi durante la sessione, in tutte le **DM Dashboard** (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/* - Dashboard.md`) e nelle note di **Prep Sessione**:

- **Valori Passivi di Riferimento del Gruppo (Esempio fittizio — Liv. 3, aggiorna in `campaign.config.json`):**
  - **[[Mira la Chierica|Mira]]:** Percezione Passiva **13** | Indagare Passivo **10** | Intuizione Passiva **15**
  - **[[Kael il Ladro|Kael]]:** Percezione Passiva **11** | Indagare Passivo **14** | Intuizione Passiva **10**
  - **[[Bram il Guerriero|Bram]]:** Percezione Passiva **10** | Indagare Passivo **9** | Intuizione Passiva **12**
- **Annotazione Esplicita nelle Stanze/Sezioni:**
  - Quando una CD di Percezione, Indagare o Intuizione è **minore o uguale** al valore passivo di un PG (e non richiede di aprire/rovistare fisicamente un contenitore), segnalala inline con **`⚡ [Passiva Automatica — Nome PG]`** indicando cosa il Master rivela direttamente senza tiri.
  - Quando una prova supera le passive del gruppo o richiede un'azione attiva dichiarata (rovistare, scassinare, forzare), indicala con **`🎲 [Tiro Attivo — Abilità CD X]`**.

---

## 7. Fedeltà agli Statblock Ufficiali / SRD per le Creature Standard
- **Creature esistenti nel regolamento (`SRD 5.1` / `MM`):** Le creature standard presenti nei manuali mantengono esattamente i propri parametri ufficiali (CA, PF, caratteristiche, azioni e tratti, senza aggiungere *Multiattack* o capacità arbitrarie), anche inline nelle Dashboard.
- **Creature custom o ruoli non coperti:** Per varianti o boss dedicati non presenti nel manuale di riferimento, è consentito creare uno statblock bilanciato marcandolo chiaramente come *Homebrew*.
- **Personaggi Giocanti (PG):** Non creare statblock da mostro per i PG; Atlas VTT `0.16.0` traccia nativamente i Punti Ferita dei PG tramite `playerCharacter: true` sui token e il file `<Vault>/atlas-vtt/campaigns/{{ATLAS_CAMPAIGN_SLUG}}/characters.json`.

---

## 8. Convenzioni Atlas VTT `0.16.0` (Campaign, Quests, Encounters & Limite 32 KB)
- **Limite Tecnico di 32 KB:** Atlas VTT ignora file di note, dashboard, statblock o loot più grandi di **32 KB** (`32768` byte). Tutte le note collegate e gli statblock devono restare snelli e sotto i **30 KB**.
- **Integrazione Nativa Quest (`<Vault>/Campagna/Quest/*.md`):** Le note di missione includono nel frontmatter YAML le proprietà lette dal pannello *Quests* di Atlas:
  ```yaml
  atlas-type: "quest"
  campaign: "00000000-0000-4000-8000-000000000001"
  kind: "main" # "main" oppure "side"
  status: "open" # "open", "active", "done", "failed"
  experience: 300 # opzionale
  rewards:
    - "Ricompensa 1"
  ```
- **Encounters Pre-Configurati (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`):** Gli scontri tattici preparati in una Dashboard possono avere il proprio file Encounter registrato nella collezione Atlas, così il Master può piazzarli con anteprima, collegarli ai Note Pin e avviare l'Initiative Tracker con filtro *"In this fight"*.
- **Watcher Automatico (`reconcileWithVault`):** In Atlas VTT `0.16.0` evita di modificare manualmente `.atlas-data/assets-metadata.json` mentre Obsidian è aperto; scrivi i record canonici `maps/`, `scenes/`, `tokens/` e lascia riconciliare Atlas automaticamente. Prima di modificare via script una `.atlasmap` già esistente, fai **chiudere il tab della scena** in Obsidian.
