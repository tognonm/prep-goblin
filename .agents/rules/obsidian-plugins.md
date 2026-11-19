# Regole per i Plugin di Obsidian

Questo file definisce le istruzioni operative per gli agenti quando interagiscono con i plugin comunitari consigliati per il vault di **{{CAMPAIGN_NAME}}**.

---

## 1. Fantasy Statblocks (`obsidian-5e-statblocks`)
- **Scopo:** Rendering visivo dei blocchi statistiche D&D 5e e gestione del bestiario in Obsidian.
- **Repository:** [Obsidian-TTRPG-Community/fantasy-statblocks](https://github.com/Obsidian-TTRPG-Community/fantasy-statblocks)
- **Regola per gli Agenti:** Usa il blocco di codice ```` ```statblock ```` con chiavi YAML compatibili con il plugin (riferimento alla skill `statblock-5e`). Inserisci `statblock: inline` nel frontmatter delle note in `<Vault>/Mostri/` così il bestiario viene indicizzato automaticamente.
- **Integrazione con Atlas VTT:** Atlas legge direttamente questi statblock (`statblockPath`) per calcolare i modificatori d'iniziativa, mostrare PF/CA e filtrare i mostri attivi in combattimento.

## 2. Obsidian Dice Roller (`obsidian-dice-roller`)
- **Scopo:** Lanciare dadi ed estrarre risultati da tabelle casuali Markdown direttamente dentro le note.
- **Repository:** [Obsidian-TTRPG-Community/dice-roller](https://github.com/Obsidian-TTRPG-Community/dice-roller)
- **Regola per gli Agenti:** Quando crei tabelle casuali in `<Vault>/Tabelle/` o `<Vault>/Incontri/`, aggiungi block-id Markdown (`^id-tabella`) e sintassi inline del Dice Roller:
  - Tiro semplice inline: `` `dice: 1d20+5` ``
  - Estrazione da tabella nella stessa nota o in un'altra nota: `` `dice: [[Nome Tabella#^id-tabella]]` ``

## 3. Atlas VTT (`atlas-vtt` `0.16.0`)
- **Scopo:** Virtual Tabletop local-first integrato in Obsidian per mappe tattiche, Dynamic Lighting, token, Note Pin, Encounter Builder, Quests e Player View.
- **Repository & Documentazione:** [atlas-vtt/atlas-vtt](https://github.com/atlas-vtt/atlas-vtt) — [atlas-vtt.dev](https://atlas-vtt.dev/)
- **Regola per gli Agenti:**
  - Rispetta sempre lo schema `.atlasmap` `v4` e il limite di **32 KB** per Dashboard e statblock.
  - Per generare e registrare token usa `atlas-token-art`; per dungeon canonici usa `dungeon-e-mappe`; per scontri improvvisati usa `griglia-lampo`.
  - Non modificare manualmente `.atlas-data/assets-metadata.json` a Obsidian aperto; lascia lavorare `reconcileWithVault`.

## 4. Iconize (`obsidian-icon-folder`) *(opzionale ma consigliato)*
- **Scopo:** Aggiungere icone visive a cartelle e note nel file explorer di Obsidian.
- **Regola per gli Agenti:** Includi sempre `icon: "emoji"` nel frontmatter YAML delle nuove note (vedi `AGENTS.md`) per mantenere coerenza visiva.

## 5. Extended Graph (`extended-graph`) *(opzionale)*
- **Scopo:** Visualizzazione avanzata del grafo semantico tra le note del vault.
- **Regola per gli Agenti:** Usa sempre `[[Wikilink]]` coerenti e liste YAML di relazioni nel frontmatter (es. `luogo: ["[[Nome Luogo]]"]`) per mantenere il grafo ricco e privo di nodi orfani.
