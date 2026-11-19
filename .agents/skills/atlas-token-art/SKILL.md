---
name: atlas-token-art
description: >-
  Genera illustrazioni coerenti per mostri e PNG della campagna, deducendo armi ed equipaggiamento
  caratteristici dallo statblock o dalla lore, inserisce il riferimento immagine nella scheda Obsidian
  e registra il token per Atlas VTT 0.16.0.
---

# Generazione Ritratti e Registrazione Token (Atlas VTT `0.16.0`)

Questa skill governa la creazione delle illustrazioni per creature e personaggi, il loro collegamento nelle schede Obsidian e la registrazione del token nella collezione di **Atlas VTT `0.16.0`**.

---

## 1. Distinzione: Mostri Standard vs PNG Narrativi

### Caso A: Mostri e Creature Generiche (`<Vault>/Mostri/<Nome>.md`)
Usato per creature, guardie, banditi, bestie e gregari.
1. **Lettura dello Statblock:** Leggi la nota del mostro in `<Vault>/Mostri/`.
2. **Deduzione Intelligente dell'Arma/Aspetto:**
   - Analizza `actions:` e `traits:` per individuare l'arma più caratteristica (es. scimitarra, alabarda, arco corto).
   - *Armi naturali:* Se la creatura usa morso, artigli, corna o tentacoli, **non** disegnare armi impugnate; enfatizza fisionomia e posa.
   - Considera l'armatura implicata da `ac:` e la taglia (`size:`).
3. **Generazione Immagine:** Genera con il tool di generazione immagini in formato quadrato (`1:1`), seguendo `.agents/rules/art-style.md` e `resources/prompt_template.md`.
4. **Salvataggio File:** Salva l'immagine in `<Vault>/Mostri/Ritratti/<nome_file>.webp` (o `.jpg`/`.png`).
5. **Inserimento Automatico nella Nota:** Aggiorna la nota del mostro con:
   - Frontmatter: `image: "[[<nome_file>.webp]]"` e `statblock: inline` (obbligatorio per l'indicizzazione nel Bestiary di Fantasy Statblocks e i tooltip interattivi di Atlas VTT).
   - Dentro il blocco ```` ```statblock ````: `image: [[<nome_file>.webp]]`.
6. **Registrazione Token per Atlas VTT `0.16.0`:**
   ```powershell
   python .agents/skills/atlas-token-art/scripts/register_token.py "<path_immagine>" --name "<Nome>" --statblock "Mostri/<Nome>.md"
   ```
   Lo script ritaglia l'immagine a `400x400` WebP, crea la miniatura `128x128` e scrive il record `tokens/token-*.json` nella collezione configurata in `campaign.config.json` (indicizzato automaticamente da Atlas `0.16.0` via `reconcileWithVault`).
   - **Token PG (`--player`):** Imposta `"playerCharacter": true` e sincronizza i PF tramite `<Vault>/atlas-vtt/campaigns/<campaign_slug>/characters.json`.

---

### Caso B: PNG di Trama con Nome (`<Vault>/Personaggi/<Nome>.md`)
I PNG narrativi hanno un'identità propria (e talvolta un travestimento diverso dal loro statblock segreto).
1. **Lettura della Lore:** Leggi la descrizione fisica nella nota del PNG.
2. **Generazione Immagine:** Genera il ritratto in base all'aspetto visibile ai giocatori.
3. **Salvataggio File:** Salva in `<Vault>/Personaggi/Ritratti/<nome_file>.webp`.
4. **Collegamento alla Nota:** Inserisci `image: "[[<nome_file>.webp]]"` nel frontmatter e `![[<nome_file>.webp]]` nel corpo della nota.
5. **Registrazione Token:** Usa `register_token.py` (con `--statblock` opzionale se usa una scheda di combattimento) oppure lascia al Master la creazione dal tab *From vault* di Atlas VTT.

---

## 2. Regole per il Prompt di Generazione
- Accoda sempre il suffisso stilistico definito in `.agents/rules/art-style.md`.
- **Inquadratura:** Mezzo busto o tre quarti, soggetto centrato e leggibile anche rimpicciolito sulla griglia.
- **Nessuna Cornice/Anello:** Non disegnare cerchi o bordi (Atlas VTT applica l'anello dinamico del token).
- **Sfondo:** Pulito o scuro/atmosferico per far risaltare la sagoma.
