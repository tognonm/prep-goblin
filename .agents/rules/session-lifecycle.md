# Regola del Ciclo di Vita delle Sessioni e Aggiornamento Mondo Vivo

Questa regola definisce la procedura obbligatoria che ogni agente deve seguire al primo messaggio di una conversazione con il Master per mantenere il vault sincronizzato con il tavolo di gioco.

---

## 1. Check di Avvio Conversazione (Session Check)
All'inizio di una sessione di chat o quando il Master riprende il lavoro sul vault:
1. **L'agente verifica lo stato delle sessioni:**
   - Chiedere garbatamente al Master:
     > *«Dall'ultima volta che abbiamo lavorato insieme, avete giocato una o più sessioni? Se sì, quante sessioni e quanti giorni in-game sono trascorsi?»*
2. **Se NESSUNA sessione è stata giocata:**
   - Procedere normalmente con la richiesta o la preparazione.
3. **Se UNA O PIÙ sessioni sono state giocate:**
   - Raccogliere gli appunti grezzi o il breve riassunto del Master sugli eventi accaduti.
   - Attivare la procedura di aggiornamento post-sessione (`recap-sessione` + `mondo-vivo`).

---

## 2. Procedura di Aggiornamento Post-Sessione
Se sono state giocate sessioni o è trascorso del tempo in-game:
1. **Aggiornare `<Vault>/Sessioni/Diario di Campagna.md`:**
   - Aggiungere una nuova riga nella tabella riassuntiva (N° sessione, data reale, data in-game, luogo, eventi, orologi).
   - Aggiungere (o collegare) il recap dettagliato in `<Vault>/Sessioni/Sessione NN.md`.
2. **Aggiornare `<Vault>/Campagna/Stato del mondo.md`:**
   - Avanzare la data in-game secondo il calendario della campagna.
   - Aggiornare la posizione corrente del gruppo e le risorse (oro, pozioni, oggetti chiave).
3. **Avanzare gli Orologi delle Fazioni (`<Vault>/Campagna/Fazioni/`):**
   - Leggere tutte le fazioni attive elencate in `Stato del mondo.md` e in `<Vault>/Campagna/Fazioni/`.
   - Valutare l'avanzamento dei rispettivi clock in base alle scelte del party e al tempo trascorso (`mondo-vivo`).
   - Segnalare al Master quali conseguenze visibili si manifestano nel mondo (dicerie, prezzi, pattuglie, reazioni dei PNG).
4. **Aggiornare i Fronti Personali dei Giocatori (`<Vault>/Campagna/Giocatori/`):**
   - Aggiornare obiettivi personali, legami, debiti, promesse o progressi di ciascun PG documentato nel Vault.
5. **Triage di `<Vault>/Campagna/Registro Improvvisazioni.md`:**
   - Rivedere insieme al Master i PNG, i locali/eventi e le scene lampo annotate durante la sessione (`live-improv-and-boundaries.md`).
   - Proporre cosa promuovere a nota canonica in `<Vault>/Personaggi/` o `<Vault>/Luoghi/`, cosa lasciare nel registro come `ricorrente`/`effimero` e quali scene lampo temporanee archiviare o rimuovere.
   - Se il gruppo si sta spostando verso una nuova regione o bioma della campagna, valutare l'aggiunta di nuove scene `Jolly - *` dedicate alla nuova area (`griglia-lampo`).
6. **Verifica Integrità Finale:**
   - Eseguire `python scripts/lint_vault.py` per controllare sintassi YAML, wikilink e limite 32 KB delle note Atlas VTT.
