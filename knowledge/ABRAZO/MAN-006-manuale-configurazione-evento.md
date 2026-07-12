# Manuale operativo — Configurazione Evento

**Per chi è questo manuale**: amministratore Art&Tango e responsabile tecnico, incaricato di aprire e configurare un nuovo evento su ABRAZO.

---

## Scopo del modulo

Il modulo **Configurazione Evento** consentirà alla Segreteria di creare autonomamente un nuovo evento su ABRAZO — nome, date, sede, pacchetti, attività, coppie di maestri, prezzi — direttamente dall'interfaccia admin, senza accesso a Supabase Dashboard né script SQL.

A pieno regime, questo modulo sarà il punto di partenza di ogni evento Art&Tango: Festival, Milonga, Workshop o Serata a tema, configurabili con un processo guidato e verificabile passo per passo dall'amministratore, senza coinvolgere il responsabile tecnico.

---

## Stato attuale

Alla versione RC1, ABRAZO non dispone ancora di un'interfaccia grafica per la creazione e modifica degli eventi. **Epico Tango Fest 2027** è l'unico evento attivo, configurato tramite inserimento diretto nelle tabelle Supabase.

**Cosa è già parametrizzato nel database:**

| Elemento | Tabella Supabase | Dinamico |
|---|---|---|
| Dati evento (nome, date, sede, IBAN) | `events` | ✓ |
| Pacchetti (nome, prezzo, acconto) | `packages` | ✓ |
| Attività (tipo, sala, orario, capienza) | `event_activities` | ✓ |
| Collegamento attività ↔ pacchetti | `package_activities` | ✓ |
| Coppie di maestri | `teacher_couples` | ✓ |
| URL di registrazione pubblica | Percorso `/register/epico-tango-fest-2027/` | ✗ — hardcoded |

Il form di iscrizione pubblica legge i dati dal database in modo dinamico: tutti i pacchetti, le attività e le coppie di maestri visibili nel form sono quelli con `is_active = true` e `is_public = true` nella rispettiva tabella.

**Modificare dati oggi** richiede accesso a Supabase Dashboard, conoscenza dello schema del database e attenzione alle relazioni tra tabelle. Non è un'operazione adatta allo staff di Segreteria.

> **Funzionalità prevista nella RC1** — L'interfaccia di configurazione sostituirà l'accesso diretto a Supabase per tutte le operazioni di gestione evento. Fino alla disponibilità di questa interfaccia, qualsiasi modifica alla configurazione richiede il coinvolgimento del responsabile tecnico.

---

## Creazione nuovo evento

> **Funzionalità prevista nella RC1** — La creazione di un evento tramite interfaccia admin non è ancora disponibile. Il flusso descritto in questa sezione rappresenta il comportamento previsto.

Il flusso previsto per la creazione di un nuovo evento:

### Dati principali

- **Nome evento** — visualizzato nella dashboard admin e nel form pubblico (es. "Epico Tango Fest 2027")
- **Slug URL** — identificativo breve usato nelle URL pubbliche (es. `epico-tango-fest-2027`). Deve essere univoco, senza spazi, e non modificabile dopo la pubblicazione
- **Data inizio** e **data fine** — utilizzate anche nell'header della dashboard e nelle email
- **Sede** — nome della location (es. "Villa La Personala") e città
- **Lingue disponibili** — italiano, inglese, o entrambe; determina le schede visibili nel form di iscrizione

### Testi e coordinate bancarie

- **Descrizione breve** — testo presentato nella pagina pubblica dell'evento
- **Note pagamento** — istruzioni per il bonifico bancario incluse nell'email di conferma iscrizione
- **IBAN** — conto su cui ricevere i pagamenti
- **Beneficiario** — intestatario del conto (es. "Art&Tango ASD")

### Stato di attivazione

Un evento può trovarsi in tre stati:

| Stato | Visibilità pubblica | Iscrizioni |
|---|---|---|
| **Bozza** | Non visibile | Non accessibili |
| **Iscrizioni aperte** | Visibile | Attive |
| **Chiuso** | Visibile (sola lettura) | Non accessibili |

Il passaggio a **Iscrizioni aperte** rende il form pubblicamente accessibile. Prima di attivare, completare l'intera checklist in fondo a questo manuale.

---

## Configurazione pacchetti

> **Funzionalità prevista nella RC1** — La gestione dei pacchetti tramite interfaccia admin non è ancora disponibile. Attualmente i pacchetti sono configurati direttamente nella tabella `packages` su Supabase.

I **pacchetti** definiscono le opzioni acquistabili nel form di iscrizione. Ogni pacchetto copre automaticamente un insieme di attività a prezzo fisso.

**Pacchetti tipici per un festival tango:**

| Pacchetto | Attività incluse | Uso |
|---|---|---|
| **Full Pass** | Stage + Milonghe + Show | Accesso completo — sconto implicito rispetto alle singole attività |
| **Stage Pass** | Solo stage | Per chi frequenta esclusivamente le lezioni |
| **Milonga Pass** | Solo milonghe | Per i ballerini che preferiscono le serate |
| **Personalizzato** | Definite dall'organizzatore | Per esigenze specifiche o pacchetti promozionali |

**Campi per ogni pacchetto:**

- **Nome IT** e **Nome EN** — visualizzato nel form pubblico nella lingua selezionata dal partecipante
- **Slug** — identificativo interno non modificabile dopo la pubblicazione (es. `full-pass`)
- **Prezzo intero** — importo per la prenotazione standard (vedi sezione Prezzi)
- **Acconto** — quota versata all'iscrizione; il saldo è dovuto entro la scadenza configurata
- **Attività incluse** — quali `event_activities` sono coperte senza costo aggiuntivo
- **Visibile al pubblico** — se attivo, il pacchetto appare nel form di iscrizione
- **Attivo** — se disattivato, il pacchetto non accetta nuove iscrizioni ma rimane visibile per le pratiche già create

Quando un partecipante seleziona un pacchetto, le attività incluse vengono marcate automaticamente come coperte: non aggiungono importo al totale. Le attività non incluse nel pacchetto possono essere aggiunte singolarmente con il proprio prezzo.

---

## Configurazione attività

> **Funzionalità prevista nella RC1** — La gestione delle attività tramite interfaccia admin non è ancora disponibile. Attualmente le attività sono inserite direttamente nella tabella `event_activities`.

Le **attività** sono le singole sessioni che compongono l'evento. Ogni attività appare nella lista del form di iscrizione e ha il proprio scanner di check-in.

**Tipi di attività supportati:**

| Tipo | Codice | Caratteristiche |
|---|---|---|
| **Stage** | `stage` | Lezione con coppia di maestri, tipicamente a capienza limitata |
| **Milonga** | `milonga` | Serata di ballo libero, capienza ampia o illimitata |
| **Show** | `show` | Spettacolo, di norma accessibile a tutti gli iscritti all'evento |
| **Workshop** | `workshop` | Laboratorio tematico, formato ridotto |

**Campi per ogni attività:**

- **Codice** — identificativo breve univoco nell'evento (es. `ST01`, `ML03`, `SHOW1`). Appare nei badge del check-in e nella lista attività
- **Titolo IT** e **Titolo EN** — nome della sessione nelle due lingue
- **Tipo** — uno dei quattro tipi sopra
- **Sala** — nome della location specifica (es. "Sala Romantica", "Sala Blu")
- **Data e ora inizio** / **Data e ora fine** — con fuso orario; usati nel form e nei display del check-in
- **Prezzo singolo** — importo per l'acquisto individuale, fuori dai pacchetti
- **Capienza massima** — numero massimo di partecipanti. Raggiunta la capienza, l'attività non è più selezionabile nel form
- **Visibile al pubblico** — controlla la visibilità nel form di iscrizione

**Capienza aperta vs. limitata:**

Gli stage hanno tipicamente una capienza numerica definita (es. 40 posti). Milonghe e show possono avere capienza illimitata — in quel caso il campo viene lasciato vuoto.

> **Funzionalità prevista nella RC1** — La waiting list automatica per attività a capienza esaurita non è ancora implementata. Quando i posti si esauriscono, l'attività scompare dal form senza informare il partecipante dell'esistenza di una lista d'attesa.

---

## Coppie di maestri

> **Funzionalità prevista nella RC1** — La gestione delle coppie di maestri tramite interfaccia admin non è ancora disponibile. Attualmente i dati sono inseriti direttamente nella tabella `teacher_couples`.

Le **coppie di maestri** (o insegnanti singoli) sono le figure artistiche ospitate all'evento. Appaiono nel form di iscrizione pubblico per aiutare il partecipante a orientarsi tra le attività.

**Campi per ogni coppia:**

- **Nome visualizzato** — come appare nel form (es. "Juan & Maria", "Carlos Pérez")
- **Foto** — immagine profilo nella card del form pubblico
- **Sito web** — URL del profilo o del sito personale della coppia
- **Ordine di visualizzazione** — numero che determina la posizione nella griglia del form

**Come funziona nel form di iscrizione:**

Quando il partecipante sfoglia le coppie nel form, può cliccare su un nome per evidenziare le attività condotte da quella coppia. Questo semplifica la selezione degli stage senza richiedere la conoscenza dei codici attività.

> **Funzionalità prevista nella RC1** — Il caricamento della foto tramite interfaccia admin è previsto con l'integrazione di Supabase Storage. Attualmente la foto viene caricata direttamente nello storage con percorso `teachers/{teacher_id}.jpg`.

---

## Prezzi

> ⚠ **Sezione da aggiornare** — I valori di prezzo verranno definiti dopo la riunione organizzativa di Epico Tango Fest 2027. I campi segnati con *Da definire* sono predisposti per essere completati senza modificare il resto del manuale.

### Fasce di prezzo per pacchetto

Il sistema supporta due fasce di prezzo per ogni pacchetto:

| Fascia | Descrizione | Valore |
|---|---|---|
| **Prezzo Early Booking** | Tariffa ridotta per iscrizioni entro la data limite | *Da definire* |
| **Prezzo intero** | Tariffa standard dopo la chiusura dell'Early Booking | *Da definire* |

Il sistema applica automaticamente il prezzo Early Booking se la data di iscrizione è antecedente alla scadenza configurata. Non richiede codici promozionali né intervento manuale.

### Acconti e saldi

| Parametro | Descrizione | Valore |
|---|---|---|
| **Acconto** | Quota versata all'iscrizione (importo fisso o percentuale del totale) | *Da definire* |
| **Data scadenza saldo** | Entro quando deve pervenire il saldo | *Da definire* |
| **Saldo** | Differenza tra totale dovuto e acconto già versato | Calcolato automaticamente |

### Calendario Early Booking

| Parametro | Valore |
|---|---|
| Data apertura Early Booking | *Da definire* |
| Data chiusura Early Booking | *Da definire* |

> **Funzionalità prevista nella RC1** — La configurazione dei prezzi e delle fasce Early Booking tramite interfaccia admin non è ancora disponibile. I valori sono attualmente inseriti direttamente nel database. L'aggiornamento dei prezzi dopo la riunione organizzativa richiede il coinvolgimento del responsabile tecnico.

---

## Checklist prima della pubblicazione

Prima di impostare l'evento su **Iscrizioni aperte**, verificare ogni punto. Ogni voce deve essere confermata da chi ha eseguito l'operazione.

- □ **Date corrette** — Inizio e fine evento corrispondono alle date ufficiali. L'orario di inizio e fine è nel fuso orario corretto.

- □ **Pacchetti verificati** — Tutti i pacchetti necessari sono presenti, attivi e visibili al pubblico. Il collegamento attività ↔ pacchetti è corretto per ognuno.

- □ **Attività complete** — Tutte le sessioni hanno sala, orario, capienza e coppie di maestri collegati. I titoli IT e EN sono compilati.

- □ **Prezzi verificati** — Prezzo intero e prezzo Early Booking sono inseriti per ogni pacchetto. Gli acconti corrispondono a quanto deliberato.

- □ **Early Booking verificato** — La data di scadenza Early Booking è impostata. Il sistema mostra il prezzo ridotto per iscrizioni antecedenti alla scadenza.

- □ **Traduzioni IT/EN** — Tutti i campi bilingui sono compilati in entrambe le lingue. Il toggle IT/EN nel form pubblico funziona correttamente.

- □ **Email confermate** — L'email di conferma iscrizione arriva con mittente corretto, IBAN, beneficiario e importi esatti. Testata con un'iscrizione di prova su indirizzo email interno.

- □ **Evento pubblicato** — Lo stato dell'evento è impostato su Iscrizioni aperte. La pagina pubblica è accessibile e il form è funzionante da mobile e desktop.

---

## Rimandi ai manuali operativi

| Manuale | Contenuto | Quando consultarlo |
|---|---|---|
| **MAN-001** — Start here | Panoramica di ABRAZO e mappa dei manuali | Prima di iniziare la configurazione, per avere il quadro d'insieme |
| **MAN-002** — Gestione Partecipante | Ricerca iscritti, scheda completa, modifica iscrizione | Dopo la pubblicazione, per gestire le iscrizioni in arrivo |
| **MAN-003** — Check-in | Accoglienza evento e accesso attività via scanner QR | Per configurare gli scanner e formare lo staff di sala prima dell'evento |
| **MAN-004** — Segreteria e Pagamenti | Gestione pagamenti, pratiche partecipanti | Per formare lo staff di Segreteria che registrerà i pagamenti |

---

*Manuale operativo ABRAZO — Configurazione Evento · Art&Tango · Versione RC1 · Luglio 2026*
