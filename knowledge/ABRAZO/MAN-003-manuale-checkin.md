# Manuale operativo — Check-in

**Per chi è questo manuale**: staff di front desk che gestisce l'accoglienza all'ingresso e staff di sala che gestisce l'accesso alle singole attività.

---

## Due funzioni distinte

ABRAZO distingue due operazioni di verifica QR con scopi diversi:

| Funzione | Dove si usa | Chi la usa | Cosa verifica |
|---|---|---|---|
| **Accoglienza evento** | Ingresso principale | Front desk | Iscrizione + stato pagamento |
| **Accesso attività** | Ogni sala | Staff di sala | Prenotazione attività specifica |

Le due funzioni sono **indipendenti**: puoi fare una senza l'altra, nell'ordine che preferisci. Entrambe sono accessibili dalla dashboard dell'evento (Fig. SCN-301).

<div class="fig-ref"
     data-scn="SCN-301"
     data-title="Dashboard operativa — accesso alle funzioni di check-in"
     data-caption="Dalla dashboard dell'evento si accede a tutte le funzioni operative. Accoglienza e Accesso attività hanno scopi distinti e indipendenti: la prima gestisce l'ingresso generale, la seconda verifica la prenotazione di una singola sala."
     data-markers="1:64%:39%:Accoglienza;QR, accredito e verifica dello stato pagamento all'ingresso principale dell'evento|2:64%:59%:Accesso attività;Scanner dedicato per sale, stage e milonghe — verifica solo la prenotazione dell'attività">
</div>

---

## Accoglienza evento

Questa funzione serve al **front desk** per registrare l'ingresso dei partecipanti all'evento principale. È il punto di primo contatto con l'iscritto.

### Come aprire la console

1. Vai al **Centro Operativo** di ABRAZO (area admin).
2. Clicca sull'evento (es. Epico Tango Fest 2027).
3. Clicca su **Accoglienza** nella griglia delle funzioni.
4. Scegli la modalità di lettura.

### Tre modalità di lettura

La console offre tre modi per leggere il codice del partecipante, selezionabili al momento dell'apertura (Fig. SCN-302):

<div class="fig-ref"
     data-scn="SCN-302"
     data-title="Accoglienza evento — modalità di lettura"
     data-caption="La console di accoglienza propone tre modalità di lettura del codice. Scanner USB è quella consigliata per le postazioni fisse; fotocamera e codice manuale coprono l'uso da smartphone e i partecipanti senza QR."
     data-markers="1:57%:20%:Scanner USB;Lettore QR HID collegato al computer. Il badge Consigliato indica la modalità ottimale per il front desk|2:57%:47%:Fotocamera;Camera posteriore del dispositivo. Per smartphone o tablet quando non è disponibile un lettore USB|3:57%:75%:Codice manuale;Digita il codice EVP quando il partecipante non ha il QR con sé">
</div>

**Scanner USB (consigliato)** — collegare un lettore QR USB HID al computer. Il lettore simula la tastiera: invia il codice nel campo e preme Invio automaticamente. Nessuna configurazione richiesta. Posiziona il cursore nel campo e scansiona.

**Fotocamera** — usa la camera posteriore del dispositivo. Si attiva solo dopo click esplicito sul pulsante "Avvia fotocamera". Consigliata da smartphone o tablet quando non c'è un lettore USB.

**Codice manuale** — digita il codice iscrizione (`EVP-A3K9P2`) o il payload completo (`ABRAZO:EVP:EVP-A3K9P2`). Utile quando il partecipante non ha il QR con sé.

### Come scansionare un QR

1. Inquadra il QR personale del partecipante con la camera.
2. Appena il codice viene letto, lo scanner si ferma e mostra il risultato.

**Risultato verde — primo ingresso:**
```
✓ Check-in effettuato
Nome Cognome — EVP-XXXXXX
Ruolo: Leader / Follower / Entrambi
Stato pagamento: Saldato / Acconto ricevuto / Da verificare
```

**Risultato ambra — già registrato:**
```
⚠ Già presente
Nome Cognome — EVP-XXXXXX
Primo ingresso: gg/mm/aa hh:mm
```

### Cosa significa lo stato pagamento

Il QR personale del partecipante (codice EVP) non cambia a seconda del pagamento — viene emesso al momento dell'iscrizione. All'accoglienza, lo scanner mostra lo stato attuale:

- **Saldato** (verde): ha pagato tutto. Nessuna pendenza.
- **Acconto ricevuto** (ambra): ha pagato l'acconto, deve ancora saldare. La scadenza è indicata nel profilo.
- **Da verificare** (rosso): non risulta nessun pagamento registrato.

La **decisione su cosa fare** con i casi non saldati è dello staff: far entrare comunque il partecipante, o indirizzarlo alla Segreteria/cassa. ABRAZO mostra l'informazione, non blocca l'accesso.

### Il partecipante non ha il QR con sé

Passa alla modalità **"Codice manuale"**. Digita il codice iscrizione (formato `EVP-A3K9P2`) o il codice completo (`ABRAZO:EVP:EVP-A3K9P2`). Il risultato è identico.

### Il QR non viene letto

- Schermo del partecipante alla massima luminosità.
- Tieni il telefono fermo a circa 15–20 cm dal QR.
- Se il problema persiste, usa l'input manuale con il codice iscrizione.

---

## Accesso attività

Questa funzione serve allo **staff di sala** per verificare che un partecipante abbia prenotato una specifica attività (stage, milonga, spettacolo). Non gestisce il pagamento — solo la prenotazione.

### Lista attività e contatori

La pagina **Accesso attività** elenca tutte le attività dell'evento con i contatori aggiornati in tempo reale. Per ogni riga è visibile quanti partecipanti sono attesi, quanti hanno già fatto check-in e quanti risultano ancora assenti (Fig. SCN-303).

<div class="fig-ref"
     data-scn="SCN-303"
     data-title="Lista attività — contatori e accesso allo scanner"
     data-caption="Ogni attività mostra in tempo reale iscritti, presenti e assenti. Il bottone Apri accesso attività apre la pagina scanner dedicata a quella sala, da inviare al volontario assegnato."
     data-markers="1:38%:9%:Iscritti;Totale partecipanti che hanno prenotato questa attività|2:38%:19%:Presenti;Partecipanti che hanno già effettuato il check-in alla sala|3:38%:28%:Assenti;Iscritti che non hanno ancora fatto check-in — si aggiorna in tempo reale|4:33%:74%:Apri accesso attività;Apre lo scanner QR dedicato a questa sala da distribuire allo staff">
</div>

### Come distribuire il link dello scanner

Ogni attività ha una pagina dedicata con il proprio scanner QR. Il responsabile può distribuire il link direttamente al volontario assegnato alla sala, senza che quest'ultimo debba navigare tutta l'area admin.

**Dal Centro Operativo:**
1. Vai all'evento → **Accesso attività**.
2. Trova l'attività da assegnare.
3. Clicca **"Copia link staff"** sulla riga corrispondente.
4. Il link viene copiato negli appunti.
5. Invialo al volontario di sala via WhatsApp, Telegram o altro canale.

Il volontario apre il link sul proprio cellulare e vede direttamente lo scanner per quella specifica attività. La pagina mostra in modo prominente il codice, il titolo, la sala e l'orario — così il volontario è sicuro di avere la pagina giusta.

**Nota**: l'accesso richiede l'autenticazione staff. Il volontario deve essere loggato per usare lo scanner.

Ogni sala usa il proprio scanner, indipendente dagli altri. Più operatori possono gestire scanner diversi contemporaneamente senza interferenze.

> **Futuro**: in una versione successiva sarà possibile assegnare nominativamente un operatore a ogni attività, con audit automatico dell'identità di chi ha effettuato ogni check-in.

### Come scansionare

Ogni attività ha la propria pagina di accesso con il riepilogo dell'attività e il campo di lettura del codice (Fig. SCN-304).

<div class="fig-ref"
     data-scn="SCN-304"
     data-title="Accesso attività — pagina scanner"
     data-caption="La pagina di accesso mostra il riepilogo dell'attività assegnata e offre due modalità di lettura: campo manuale per codice o payload QR, oppure fotocamera tramite il bottone Apri Scanner QR."
     data-markers="1:29%:43%:Dati attività;Codice, titolo, sala e orario. Il volontario verifica qui di avere aperto la pagina corretta|2:70%:44%:Campo codice / QR;Incolla il payload QR o digita il codice EVP manualmente, poi premi Cerca e registra|3:82%:34%:Apri Scanner QR;Attiva la fotocamera del dispositivo per scansionare il QR personale del partecipante">
</div>

I possibili risultati sono:

**Verde — primo accesso all'attività:**
```
✓ Accesso registrato
Nome Cognome — EVP-XXXXXX
Attività: [codice e titolo]
```

**Ambra — già registrato per questa attività:**
```
⚠ Già presente a questa attività
Nome Cognome — EVP-XXXXXX
Registrato alle: hh:mm
```

**Rosso — non prenotato:**
```
✕ Non iscritto a questa attività
Nome Cognome — EVP-XXXXXX
Il partecipante non ha prenotato questa sessione.
```

Il messaggio rosso significa che il partecipante è iscritto all'evento ma non ha questa specifica attività nel suo programma. Tocca a te decidere come gestire il caso.

### Accesso negato — saldo aperto

Nell'accesso attività, se il partecipante ha ancora un saldo residuo non regolato, il sistema mostra il messaggio "Accesso non consentito" in rosso (Fig. SCN-305). Il check-in **non viene registrato**. Indirizza il partecipante alla Segreteria prima di consentire l'ingresso.

<div class="fig-ref"
     data-scn="SCN-305"
     data-title="Accesso negato — saldo aperto"
     data-caption="Il sistema blocca il check-in quando il partecipante ha ancora un saldo aperto. Il messaggio è bilingue (IT/EN). Il check-in non viene registrato: il partecipante deve prima regolarizzare il pagamento in Segreteria."
     data-markers="1:37%:45%:Accesso non consentito;Messaggio di blocco bilingue: saldo ancora aperto, il check-in non viene registrato|2:85%:79%:Saldo residuo;Importo che il partecipante deve regolarizzare in Segreteria prima di accedere alla sala">
</div>

### Check-in riuscito

Quando il check-in va a buon fine, il sistema mostra una conferma verde con il riepilogo del partecipante verificato (Fig. SCN-306).

<div class="fig-ref"
     data-scn="SCN-306"
     data-title="Check-in attività — accesso confermato"
     data-caption="La conferma verde indica che il partecipante è iscritto all'attività e il check-in è stato registrato. Il sistema mostra nome, codice, stato del pagamento e orario dell'operazione."
     data-markers="1:48%:53%:Conferma verde;Check-in registrato correttamente. Il partecipante può accedere alla sala|2:59%:32%:Partecipante verificato;Nome e codice iscrizione del partecipante ammesso, con stato del pagamento">
</div>

> Per i casi di doppio check-in (partecipante già presente), vedi MAN-008 — Risoluzione problemi.

### Metriche in tempo reale

Nella pagina **Accesso attività**, i contatori Iscritti / Presenti / Assenti si aggiornano man mano che si effettuano i check-in.

---

## Domande frequenti

**Devo fare prima l'accoglienza e poi l'accesso attività?**
No. Sono indipendenti. Un partecipante può accedere a una singola attività anche senza essere passato dall'ingresso principale.

**Il QR del partecipante cambia nel tempo?**
No. Il codice iscrizione (EVP) viene generato al momento della registrazione online e non cambia mai. Il partecipante usa sempre lo stesso QR durante tutto l'evento.

**Cosa è il codice EVP?**
EVP sta per "Event Participant" — è il codice iscrizione personale del partecipante. Ha formato `EVP-XXXXXX` (sei caratteri alfanumerici). Il partecipante lo riceve nell'email di conferma iscrizione insieme al QR.

**Quante persone possono usare lo scanner contemporaneamente?**
Quante ne servono. Non ci sono limiti sul numero di scanner attivi in parallelo.

**Il check-in è reversibile?**
No, dalla UI non è disponibile l'annullamento di un check-in. Per correzioni, contatta il responsabile tecnico.

---

*Manuale operativo ABRAZO — Check-in · Art&Tango · Versione RC1 · Luglio 2026*
