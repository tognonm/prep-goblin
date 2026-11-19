# Regole di Sincronizzazione: Obsidian ↔ Atlas VTT `0.16.0`

Questo documento definisce i confini chiari su cosa deve rimanere solo come testo nel vault di Obsidian e cosa invece **deve obbligatoriamente** avere una rappresentazione grafica o meccanica all'interno di **Atlas VTT `0.16.0`**.

---

## 1. Il Principio della "Scena Attiva"
La regola d'oro è la **Scena Attiva**. Tutto ciò che fa parte del "mondo sullo sfondo" (Lore, storia passata, personaggi distanti, fazioni fuori scena) vive solo in Obsidian. Tutto ciò che i giocatori possono **vedere, combattere o esplorare ora** deve avere un asset pronto in Atlas VTT.

---

## 2. Cosa vive SOLO in Obsidian (Nessun asset VTT richiesto)
- **Lore e Storia:** Miti di creazione, guerre passate, note sui pantheon e sull'ambientazione.
- **PNG di Sfondo:** Autorità lontane, contatti menzionati ma assenti, familiari dei PG fuori scena.
- **Fazioni e Orologi (Clocks):** I progressi segreti delle fazioni (salvo quando un evento del clock si manifesta fisicamente davanti al party).
- **Luoghi a Livello Macro:** Note su nazioni, regioni o città nel complesso (salvo eventuale mappa regionale interattiva su Atlas).
- **Oggetti Comuni / Inventario:** Equipaggiamento standard, monete e documenti puramente narrativi.

---

## 3. Cosa DEVE essere sincronizzato in Atlas VTT (Obbligo di Asset)
Quando si prepara una sessione o un incontro tattico, gli elementi seguenti devono avere il corrispettivo asset VTT:

### A. Mostri e PNG da Combattimento / Interazione Diretta
Se una creatura (es. uno *Scheletro Sentinella* in una cripta) o un PNG chiave è fisicamente presente nella scena:
- **In Obsidian:** Esiste la nota con blocco statistiche (```` ```statblock ````) in `<Vault>/Mostri/` (o la scheda PNG in `<Vault>/Personaggi/`).
- **Ritratti / Token:** L'agente genera o seleziona l'immagine (in `<Vault>/Mostri/Ritratti/` o `<Vault>/Personaggi/Ritratti/`) e la inserisce nella nota (`image: "[[...]]"`).
- **In Atlas VTT:** Registra il token nella collezione configurata (`atlas-token-art/scripts/register_token.py`) oppure usa il comando rapido di Atlas per creare e collegare il token con `statblockPath` valorizzato.
- **Personaggi Giocanti (PG):** I token dei PG usano `"playerCharacter": true` e sincronizzano i PF tramite `<Vault>/atlas-vtt/campaigns/<campaign_slug>/characters.json`.

### B. Mappe e Dungeon
Se i giocatori stanno esplorando un luogo tattico passo-passo (un dungeon, una taverna, un accampamento):
- **In Obsidian:** Nota di Compendio (`<Vault>/Luoghi/`) + DM Dashboard operativa (`< 30 KB`) nella collezione Atlas.
- **In Atlas VTT:** Scena `.atlasmap` (schema `v4`) con battlemap scalata, griglia coerente, muri, porte, luci dinamiche e Note Pin validati con `atlas_scene_tools.py`.

### C. Handout Visivi ed Enigmi
Se esiste un elemento visivo che i giocatori devono studiare (lettera cifrata, simbolo, bassorilievo):
- **In Obsidian:** Trascrizione e chiave di lettura del DM (in callout segreto).
- **In Atlas VTT (o `<Vault>/Handout/`):** Immagine o handout pulito condivisibile a schermo senza spoiler.

---

## 4. Regole Tecniche di Integrità su Disco (Atlas `0.16.0`)
- **Chiusura tab prima di edit scriptati:** Non scrivere su un file `.atlasmap` mentre quella scena è aperta in un tab di Obsidian, altrimenti Atlas può sovrascrivere il file con lo stato in RAM.
- **Nessun edit manuale ai file interni di stato:** Evita modifiche manuali a `.atlas-data/assets-metadata.json` mentre Obsidian è attivo; scrivi i record canonici in `collections/<Collection>/{maps,scenes,tokens,encounters}` e lascia che `reconcileWithVault` indicizzi automaticamente.
- **Eccezione controllata per `griglia-lampo`:** Vedi `live-improv-and-boundaries.md` per le scene tattiche usa-e-getta.
