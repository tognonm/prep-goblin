---
name: statblock-5e
description: >-
  Compila statblock D&D 5e nel formato YAML del plugin Fantasy Statblocks (Obsidian)
  e pienamente compatibili con Atlas VTT 0.16.0 (iniziativa automatica, tooltip e limite 32 KB).
  Usala quando il Master chiede lo statblock di un mostro o PNG, o di adattare una creatura.
---

# Statblock 5e per Fantasy Statblocks & Atlas VTT `0.16.0`

Atlas VTT `0.16.0` legge nativamente i blocchi ```` ```statblock ```` di **Fantasy Statblocks**, consentendo tooltip rapidi, tiri di dadi diretti e calcolo automatico dell'iniziativa quando `statblockPath` è collegato al token.

---

## 1. Fonti e Regola Anti-Invenzione
1. **SRD 5.1 / Materiale Locale del Master:** Se il Master dispone di un manuale di riferimento nella cartella locale esclusa da Git (`Fonti/`, mai committata) oppure usa l'SRD 5.1, verifica sempre i valori reali senza tirare a indovinare.
2. **Creature Homebrew / Custom:** Se la creatura non esiste nel riferimento del tavolo, dichiaralo esplicitamente e costruisci un blocco bilanciato secondo i parametri di GS, marcandolo come `*Homebrew*`.
3. Non inventare numeri spacciandoli per ufficiali: se manca un dato, segnalalo al Master.

---

## 2. Creature Standard vs Custom vs PG
- **Creature Standard (`AGENTS.md` Regola 7):** Mantengono CA, PF, caratteristiche, azioni e tratti originali senza modifiche arbitrarie; personalizza solo il testo descrittivo nella stanza.
- **Creature Custom / Boss:** Consentite per colmare ruoli o GS non coperti, esplicitando chiaramente le modifiche in una breve lista.
- **Personaggi Giocanti (PG):** Non creare statblock da mostro per i PG; usa `"playerCharacter": true` sui token e `<Vault>/atlas-vtt/campaigns/<campaign_slug>/characters.json`.

---

## 3. Integrazione con Atlas VTT `0.16.0`
- **Frontmatter Bestiary:** Includi sempre `statblock: inline` nel frontmatter YAML della nota in `<Vault>/Mostri/` affinché Fantasy Statblocks indicizzi la creatura.
- **Collegamento Token (`statblockPath`):** Nel record token (`tokens/*.json`), `statblockPath: "Mostri/<Nome>.md"` attiva il modificatore d'iniziativa automatico e il filtro *"In this fight"* del DM Screen di Atlas.
- **Limite 32 KB:** Ogni file contenente uno statblock deve restare sotto i **32 KB** (`32768` byte), verificabile con `python scripts/lint_vault.py`.
- **Formule & Riferimenti:** Compatibile con formule dadi (`2d20kh1`, `1d8+3`) e immagini collegate (`image: [[<ritratto>.webp]]`).

---

## 4. Procedura Operativa
1. Parti dal template in `.agents/skills/statblock-5e/resources/statblock_template.md`.
2. Mantieni le chiavi YAML in inglese (richieste dal plugin) e traduci/adatta solo i valori nella lingua della campagna.
3. Verifica la coerenza matematica: PF vs dadi vita medi, bonus di competenza per GS, CD = `8 + competenza + modificatore`.
4. Salva la nota in `<Vault>/Mostri/<Nome>.md` (o in `<Vault>/Personaggi/` per PNG chiave) con frontmatter YAML valido.
5. Se serve un ritratto/token, usa `atlas-token-art` e `register_token.py`.
6. Chiudi la nota con l'indicazione della fonte (es. `*Fonte: SRD 5.1 (CC-BY-4.0).*` oppure `*Homebrew — variante originale.*`).
