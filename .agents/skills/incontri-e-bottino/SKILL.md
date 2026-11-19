---
name: incontri-e-bottino
description: >-
  Bilancia gli incontri D&D 5e tramite budget PE per livello del party, genera bottino coerente
  con il Tier e configura Encounter JSON, Random Tables e Quests per Atlas VTT 0.16.0.
---

# Incontri e Bottino (`incontri-e-bottino`)

Questa skill assicura che gli scontri pianificati siano meccanicamente bilanciati, interessanti sul piano tattico e integrati con **Atlas VTT `0.16.0`**.

---

## 1. Bilanciamento (Budget PE)
Quando prepari un incontro:
1. Verifica numero e livello dei PG in `campaign.config.json` / `<Vault>/Campagna/Giocatori/`.
2. Calcola il budget PE di difficoltà (*Low*, *Moderate*, *High*) secondo le regole 5e di riferimento del tuo tavolo.
3. Scegli le creature dalle note in `<Vault>/Mostri/` (o dal manuale di riferimento) evitando squilibri eccessivi nell'economia delle azioni.
4. Produci una tabella riassuntiva: **Creatura | Quantità | GS | PE cadauno | Totale PE | Difficoltà stimata**, accompagnata da almeno 1 elemento di terreno tattico (copertura, luce, dislivello, obiettivo secondario).

---

## 2. Bottino e Tesori
- **Bottino Individuale:** Monete, equipaggiamento recuperabile e piccoli oggetti coerenti con il ruolo dei nemici.
- **Tesoro Principale (Hoard):** Riservato a boss, camere del tesoro o traguardi d'arco; verifica che rarità e potere degli oggetti magici siano coerenti con il Tier del party.
- Formatta sempre il bottino come tabella Markdown chiara per facilitare la copia nel diario o nei handout.

---

## 3. Integrazione con Atlas VTT `0.16.0`
- **Priorità agli Statblock Standard / SRD:** Per creature da manuale mantieni i parametri originali senza modifiche arbitrarie (`AGENTS.md` Regola 7); usa il reskin narrativo per adattarle alle fazioni della campagna.
- **Encounter Builder (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`):** Registra gli scontri ricorrenti o pianificati come file `encounter-*.json` nella collezione Atlas così il Master può trascinarli sulla mappa con anteprima e agganciarli ai Note Pin.
- **Random Tables (`collection.json`):** Le tabelle Markdown in `<Vault>/Tabelle/` possono essere registrate in `settings.randomTables` (`{"path": "Tabelle/<Nome>.md", "index": 0}`) della collezione Atlas per tirarle direttamente dalla UI del VTT.
- **Quests Native (`<Vault>/Campagna/Quest/*.md`):** Ogni nota di missione usa nel frontmatter:
  ```yaml
  atlas-type: "quest"
  campaign: "<atlas_campaign_id da campaign.config.json>"
  kind: "main" # oppure "side"
  status: "open" # open | active | done | failed
  experience: 300
  rewards:
    - "Ricompensa 1"
  ```
