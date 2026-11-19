---
name: mondo-vivo
description: >-
  Gestisce le fazioni, gli orologi di progresso (clocks) e gli eventi fuori scena della campagna.
  Usala post-sessione o durante il downtime per far reagire il mondo alle scelte dei giocatori
  e manifestare conseguenze concrete sul territorio.
---

# Mondo Vivo: Motore delle Fazioni e degli Orologi (`mondo-vivo`)

I giocatori non sono gli unici attori del mondo di gioco: le fazioni definite in `<Vault>/Campagna/Fazioni/` e `<Vault>/Campagna/Archi Narrativi.md` portano avanti le proprie agende mentre il party esplora, riposa o sceglie di occuparsi di un fronte invece di un altro.

---

## 1. Lettura dello Stato Attivo
Prima di proporre avanzamenti:
1. Leggi `<Vault>/Campagna/Stato del mondo.md` (data in-game, posizione, orologi attivi).
2. Leggi le schede presenti in `<Vault>/Campagna/Fazioni/`.
3. Consulta la Matrice di Reazione in `<Vault>/Campagna/Archi Narrativi.md`.

Formato standard degli orologi (clocks) in Markdown:
- Orologio a 4 segmenti: `[X] [ ] [ ] [ ]` (`1/4`)
- Orologio a 6 segmenti: `[X] [X] [ ] [ ] [ ] [ ]` (`2/6`)
- Orologio a 8 segmenti: `[X] [X] [X] [ ] [ ] [ ] [ ] [ ]` (`3/8`)

---

## 2. Procedura di Valutazione Reattiva (Post-Sessione / Downtime)
Per ciascuna fazione attiva:
1. **I PG hanno interferito direttamente col suo piano?** L'orologio rallenta, arretra o la fazione cambia strategia.
2. **I PG hanno ignorato quel fronte per dedicarsi ad altro?** Proponi l'avanzamento di `1` segmento (o `2` se la fazione aveva via libera totale).
3. **È trascorso tempo significativo di viaggio/downtime?** Valuta l'avanzamento proporzionale per tutte le fazioni non contrastate.

> [!IMPORTANT] Approvazione del Master
> Presenta sempre al Master il riepilogo proposto degli avanzamenti prima di consolidare modifiche irreversibili al canone (`master-reviewer-autorita-narrativa.md`).

---

## 3. Conseguenze nel Mondo di Gioco (Living World Fallout)
Per ogni segmento riempito, genera almeno **1 segnale osservabile** dal party:
- **Dicerie e Notizie:** Voci in taverna, bandi cittadini, lettere intercettate, viaggiatori impauriti.
- **Mutamenti Ambientali ed Economici:** Prezzi alterati, pattuglie aumentate, strade chiuse, atteggiamento cambiato dei PNG locali.
- **Completamento dell'Orologio:** Quando l'ultimo segmento si riempie, si verifica un evento irreversibile (conquista di un avamposto, caduta di un alleato, inizio di una crisi regionale) che apre un nuovo fronte o trasforma la campagna.

---

## 4. Aggiornamento delle Fonti
Dopo conferma del Master:
- Aggiorna i segmenti in `<Vault>/Campagna/Stato del mondo.md`.
- Aggiorna le relative schede in `<Vault>/Campagna/Fazioni/`.
- Riporta le ripercussioni nella sezione *Living World Fallout* della prossima `prep-sessione`.
