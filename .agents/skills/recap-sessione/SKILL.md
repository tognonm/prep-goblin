---
name: recap-sessione
description: >-
  Crea il diario ufficiale della sessione partendo dagli appunti grezzi del Master.
  Separa le informazioni segrete da quelle pubbliche, aggiorna Stato del mondo.md,
  esegue il triage di Registro Improvvisazioni.md e prepara i ganci per la sessione successiva.
---

# Recap Sessione (`recap-sessione`)

Trasforma appunti grezzi, scalette o trascrizioni del Master in un diario ordinato, mantenendo sincronizzato il resto del vault.

---

## Output Richiesto: `<Vault>/Sessioni/Sessione NN.md`

Usa il frontmatter YAML:
```yaml
---
title: "Sessione NN - Titolo"
icon: "📜"
tags: [sessione, recap]
tipo: "Sessione"
data_reale: "YYYY-MM-DD"
data_gioco: "Giorno X"
stato: "giocato"
---
```

Struttura della nota:
1. **Recap per i Giocatori:** Un riassunto narrativo scorrevole (privo di segreti DM, solo ciò che i PG hanno visto o scoperto), pronto da leggere o condividere prima della sessione successiva.
2. **Diario del Master:**
   - Cronologia sintetica dei fatti chiave.
   - Segreti svelati, sfiorati o ancora nascosti (isolati in callout `> [!danger] Segreto del DM`).
3. **Aggiornamento Mondo:**
   - Bottino acquisito e PE/milestone distribuiti.
   - Stato delle Quest (Aperte, Avanzate, Completate, Fallite).
   - Nuovi PNG o luoghi incontrati (con link `[[Nome]]` se promossi nel canone).
4. **Fili Aperti per la Prossima Sessione:** Domande aperte, conseguenze imminenti o cliffhanger.

---

## Effetti Collaterali (Side Effects Obbligatori)
Dopo aver scritto `Sessione NN.md`, aggiorna:
1. `<Vault>/Sessioni/Diario di Campagna.md`: Nuova riga nella tabella cronologica.
2. `<Vault>/Campagna/Stato del mondo.md`: Nuova data in-game, posizione del gruppo e risorse.
3. `<Vault>/Campagna/Quest/*.md`: Aggiorna la proprietà `status` (`open`, `active`, `done`, `failed`) letta da Atlas VTT `0.16.0`.
4. `<Vault>/Campagna/Registro Improvvisazioni.md`: Esegui il triage con il Master per decidere quali comparse/luoghi promuovere a nota canonica, quali lasciare come `ricorrente`/`effimero` e quali scene lampo ripulire (`live-improv-and-boundaries.md`).
5. Se è trascorso tempo in-game o si sono mosse fazioni, attiva `mondo-vivo`.

---

## Regole & Checklist
- Correggi eventuali refusi nei nomi propri confrontandoli con le note esistenti nel Vault.
- **Non inventare mai** eventi non presenti negli appunti del Master.
- [ ] Creato `<Vault>/Sessioni/Sessione NN.md` e aggiornato `Diario di Campagna.md`?
- [ ] Aggiornato `Stato del mondo.md` e gli stati delle Quest?
- [ ] Completato il triage di `Registro Improvvisazioni.md` con il Master?
- [ ] Eseguito `python scripts/lint_vault.py`?
