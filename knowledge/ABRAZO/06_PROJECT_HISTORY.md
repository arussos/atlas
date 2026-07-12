# 06 — Storia del Progetto

**Versione**: 1.0.0 | **Progetto**: ABRAZO MVP 0.9.0 | **Aggiornato**: Giugno 2026

---

> **Nota metodologica**: questo documento è ricostruito analizzando il codice sorgente, la struttura del repository, i messaggi dei commit git e il file `CLAUDE.md`. Dove non è possibile determinare con certezza la sequenza temporale, si indica esplicitamente. L'obiettivo è preservare la memoria delle decisioni prese, non produrre una cronologia precisa.

---

## Indice

1. [Contesto di partenza](#1-contesto-di-partenza)
2. [MVP 0.1 — Fondamenta](#2-mvp-01--fondamenta)
3. [MVP 0.2 — Iscrizioni e QR](#3-mvp-02--iscrizioni-e-qr)
4. [MVP 0.3 — Area Admin](#4-mvp-03--area-admin)
5. [MVP 0.4 — Check-in e Email](#5-mvp-04--check-in-e-email)
6. [MVP 0.5–0.8 — Maturazione](#6-mvp-050-8--maturazione)
7. [MVP 0.9.0 — Stato attuale](#7-mvp-090--stato-attuale)
8. [Decision Log](#8-decision-log)

---

## 1. Contesto di partenza

Prima di ABRAZO, Art&Tango gestiva le iscrizioni ai propri eventi con un processo interamente manuale:

- Email di iscrizione ricevute nella casella dell'Associazione
- Dati inseriti a mano in un foglio Excel
- Bonifici verificati manualmente sull'estratto conto
- Check-in con lista stampata e segni di spunta
- Nessuna comunicazione automatica ai partecipanti
- Nessun dato storico strutturato

Il problema era gestibile per eventi piccoli, ma con Epico Tango Fest — che può raggiungere centinaia di partecipanti su più giorni con decine di attività parallele — il sistema manuale diventava insostenibile.

**La decisione fondamentale**: costruire uno strumento digitale specifico per Art&Tango, non adattare strumenti generici (Eventbrite, Google Forms, ecc.) che non sarebbero mai stati abbastanza flessibili per la logica complessa degli eventi Tango (ruoli leader/follower, pacchetti, attività multiple, coppie di maestri).

---

## 2. MVP 0.1 — Fondamenta

### Obiettivo

Scegliere lo stack tecnologico, strutturare il progetto, verificare che i pezzi funzionassero insieme.

### Decisioni prese

**Next.js con App Router**: la scelta è caduta su Next.js per la sua natura full-stack. Un backend separato (Node.js API standalone, FastAPI, ecc.) avrebbe moltiplicato la complessità di deploy e manutenzione. App Router consente di avere SSR, API Routes e Server Components in un unico progetto.

**Supabase come backend**: la necessità di un database, di un sistema di storage per i QR e (in futuro) di autenticazione, ha suggerito un BaaS completo. Supabase offre tutti e tre con un SDK TypeScript di qualità, su un piano gratuito sufficiente per il MVP.

**Tailwind CSS senza librerie UI**: il design di ABRAZO ha un'identità visiva specifica (dark, elegante, serif+sans, palette oro/rosso). Librerie come MUI o Chakra avrebbero imposto stili difficili da sovrascrivere. Tailwind utility-first consente controllo totale.

**TypeScript strict**: decisione di usare TypeScript dal primo giorno, con strict mode. Il costo iniziale di setup è inferiore al debito tecnico che si accumula in un progetto JS non tipizzato che cresce nel tempo.

### Funzionalità introdotte

- Setup Next.js App Router con TypeScript
- Integrazione Supabase (client pubblico + admin)
- Prima versione dello schema DB (eventi, partecipanti)
- Home page con branding iniziale ABRAZO

### Debiti tecnici generati

- Nessuna autenticazione fin dall'inizio (scelta consapevole per velocizzare il MVP)

---

## 3. MVP 0.2 — Iscrizioni e QR

### Obiettivo

Il primo flusso funzionante end-to-end: un partecipante si iscrive e riceve un QR code.

### Funzionalità introdotte

**Schema DB esteso**:
- `packages` con `package_activities` (relazione molti-a-molti)
- `event_activities` con orari, sala, capienza, prezzo
- `event_participants` come modello principale dell'iscrizione
- `event_participant_activities` per tracciare le prenotazioni con source_type e pricing

**Form di iscrizione generico** (`/register/[eventId]/`):
- Primo tentativo, più semplice
- Usava il modello `registrations` / `registration_items` (ora legacy)
- Nessun supporto multilingua

**Generazione QR**:
- Prima implementazione con `qrcode` library
- Payload: `ABRAZO:REG:ABR-XXXXXX`
- Salvataggio su Supabase Storage

**API `/api/registrations`** (ora legacy):
- Prima POST API di iscrizione
- Creava participant, registration, QR, upload storage

### Decisioni importanti

**Separazione participants / event_participants**: fin dall'inizio è stata presa la decisione di non avere una sola tabella "iscrizione" con dentro i dati anagrafici. La separazione consente la riutilizzabilità dell'anagrafica e supporta il modello multi-evento.

**QR payload opaco**: già in questa fase il payload del QR non conteneva dati personali. La scelta era motivata tanto da design quanto da future considerazioni GDPR.

### Debiti tecnici generati

- Flusso generico legacy (`/api/registrations`) che sarebbe poi coesistito con il flusso avanzato

---

## 4. MVP 0.3 — Area Admin

### Obiettivo

Dare allo staff uno strumento per vedere le iscrizioni e gestire i pagamenti.

### Funzionalità introdotte

**Dashboard admin** (`/admin/`):
- Statistiche aggregate sull'evento attivo
- Link alle funzioni operative

**Lista eventi** (`/admin/events/`):
- Catalogo degli eventi nel DB
- Link alla gestione per ogni evento

**Hub evento** (`/admin/events/[id]/`):
- Dashboard con statistiche evento
- Grid con link a tutte le funzioni: partecipanti, check-in, attività, pagamenti, ricerca, comunicazioni, export

**Lista e scheda partecipanti**:
- Tabella con tutti gli iscritti, badge stato pagamento
- Scheda individuale con tutti i dettagli (dati, attività, GDPR, QR, audit)

**Gestione pagamenti**:
- Tabella con importi e stato per ogni partecipante
- Server Actions per aggiornamento stati: pending → deposit → paid
- Ogni cambio aggiorna il timestamp e produce audit

**Audit trail**:
- Introdotta la tabella `event_participant_audit`
- Ogni operazione admin genera un record audit

**Export Excel**:
- Primo export con `exceljs`
- Tre fogli: Iscrizioni, Attività, Riepilogo

### Decisioni importanti

**Server Components per l'admin**: tutte le pagine admin sono Server Components. Questo garantisce performance (nessun flash di contenuto) e sicurezza (la logica di fetch non è nel bundle client). I Client Components esistono solo dove l'interattività è necessaria.

**Server Actions per i pagamenti**: i bottoni di aggiornamento stato usano Server Actions di Next.js, che consentono di eseguire codice server-side da un click in un componente React senza dover creare endpoint API separati.

### Debiti tecnici generati

- Nessuna autenticazione sull'admin (critico, rimasto aperto)
- Event ID di Epico hardcoded nella dashboard admin

---

## 5. MVP 0.4 — Check-in e Email

### Funzionalità introdotte

**Check-in evento** (`/admin/events/[id]/checkin/`):
- Scanner QR via camera con `html5-qrcode`
- Input manuale payload
- Verifica duplicati
- Flash visivo su check-in riuscito
- Visualizzazione dati partecipante post-scan

**Check-in attività**:
- Stesso meccanismo ma scoped a singola attività
- Verifica che il partecipante sia prenotato per quell'attività
- Metriche Iscritti/Presenti/Assenti nella lista attività

**Email di conferma**:
- Primo invio email via Resend
- Template HTML bilingue IT/EN
- Layer astratto `emailService.ts`
- `buildRegistrationConfirmationEmail()` in `emailTemplates.ts`

**Pagina test QR** (`/test/qr/`):
- Per testare il flusso QR senza fare iscrizioni reali

### Decisioni importanti

**html5-qrcode per lo scanning**: libreria browser-based che usa la camera del dispositivo. L'alternativa (scanner hardware dedicato) avrebbe richiesto hardware aggiuntivo in sala. Con html5-qrcode, qualsiasi smartphone dello staff diventa uno scanner.

**Layer astratto emailService**: la decisione di non chiamare Resend direttamente dalle API Routes ma di passare sempre per `emailService.ts` è stata presa in questa fase. La motivazione era la sostituibilità del provider email in futuro.

### Debiti tecnici generati

- `checked_in_by: "staff-demo"` hardcoded nelle API (operatore non identificato)

---

## 6. MVP 0.5–0.8 — Maturazione

*Nota: le fasi 0.5-0.8 sono dedotte dalla struttura del codice e dai commit. La sequenza esatta degli incrementi non è ricostruibile con certezza.*

### Funzionalità introdotte progressivamente

**Form avanzato Epico Tango Fest 2027** (`/register/epico-tango-fest-2027/`):
- Sostituisce il flusso generico legacy per Epico
- Supporto bilingue IT/EN con toggle nel form
- Selezione visiva pacchetti con highlight delle attività incluse
- Visualizzazione coppie di maestri con card interattive
- Calcolo acconto/saldo in tempo reale

**API `/api/event-participants`**:
- Nuovo endpoint principale che sostituisce `/api/registrations` per Epico
- Logica avanzata: source_type, pricing, consensi GDPR, email, QR
- Usa il modello `event_participants` invece di `registrations`

**Pagina success avanzata**:
- QR code prominente
- Riepilogo finanziario dettagliato
- Istruzioni bonifico con IBAN, causale, scadenza
- Sezione consensi GDPR accettati
- Bilingue (via query param `?lang=`)

**Arricchimento email**:
- Lista pacchetti acquistati
- Lista attività prenotate con codice, tipo, sala, orario, maestri
- Riepilogo finanziario completo
- Dati bancari completi

**Ricerca partecipanti** (`/admin/events/[id]/search/`):
- Ricerca per nome, cognome, email, codice EVP

**Preview comunicazioni** (`/admin/events/[id]/communications/`):
- Anteprima del template email con dati campione
- Preview IT e EN

### Decisioni importanti

**Mantenere il flusso legacy**: invece di migrare tutti al nuovo flusso, il flusso generico (`/register/[eventId]/`, `/api/registrations`) è rimasto attivo. Questo ha creato la coesistenza di due sistemi, ma ha evitato rischi di regressione.

**teacher_pair_label come campo temporaneo**: introdotto come shortcut per visualizzare rapidamente i maestri nelle card senza costruire la join completa `activity_teachers → teachers`. Questo debito tecnico è stato accettato consapevolmente.

---

## 7. MVP 0.9.0 — Stato attuale

### Cosa rappresenta MVP 0.9.0

La versione 0.9.0 è il sistema completo nelle sue funzionalità core, funzionante in sviluppo e staging, pronto per essere portato in produzione a condizione di risolvere i blocchi critici (autenticazione admin, email dominio produzione).

La numerazione 0.9 riflette che il sistema è quasi completo per il primo deploy, ma mancano gli ultimi elementi di robustezza e sicurezza per considerarlo production-ready.

### Cosa distingue 0.9.0 da 1.0

- Nessuna autenticazione admin (M1)
- Prezzi non ricalcolati server-side (M2)
- Email da dominio non verificato (M3)
- Operator identity non reale (M4)

---

## 8. Decision Log

Registro delle principali decisioni architetturali prese nel corso del progetto, con la motivazione originale.

---

### DL-01: Next.js App Router come framework full-stack

**Data**: inizio progetto
**Decisione**: usare Next.js (App Router) invece di frontend separato + backend API standalone
**Motivazione**: un unico progetto, un unico deploy, condivisione dei tipi TypeScript tra frontend e backend, Server Components per performance. La complessità di coordinare due repository separati per un team piccolo non era giustificata.
**Alternative valutate**: React + Express/Fastify separato, Nuxt.js (Vue), SvelteKit
**Stato**: confermata ✓

---

### DL-02: Supabase come BaaS

**Data**: inizio progetto
**Decisione**: usare Supabase (PostgreSQL + Storage + Auth futura) invece di database standalone
**Motivazione**: database, storage e auth futura in un unico servizio con SDK TypeScript di qualità. Piano gratuito sufficiente per il MVP. Riduce la gestione infrastrutturale.
**Alternative valutate**: PlanetScale/Neon (solo DB), Firebase (diverso paradigma), MongoDB
**Stato**: confermata ✓

---

### DL-03: Due client Supabase con privilegi diversi

**Data**: prime fasi sviluppo
**Decisione**: separare esplicitamente `supabase.ts` (anon key) da `supabaseAdmin.ts` (service role)
**Motivazione**: la service role key bypassa la RLS e non deve mai essere esposta al browser. L'separazione esplicita nei file rende impossibile usare accidentalmente il client sbagliato.
**Stato**: confermata ✓

---

### DL-04: QR payload opaco (`ABRAZO:EVP:CODE`)

**Data**: MVP 0.2
**Decisione**: il payload del QR non contiene dati personali, solo un codice opaco namespacato
**Motivazione**: sicurezza e GDPR. Un QR che contenesse nome o email sarebbe un dato personale leggibile da chiunque. Il codice opaco richiede accesso autenticato al DB per essere risolto.
**Stato**: confermata ✓

---

### DL-05: Separazione `participants` / `event_participants`

**Data**: MVP 0.2
**Decisione**: tabella anagrafica separata dalla tabella di iscrizione a evento
**Motivazione**: supporto multi-evento (un partecipante può iscriversi a più eventi), minimizzazione GDPR (i dati anagrafici sono scritti una volta), possibilità di costruire nel tempo una base associativa.
**Stato**: confermata ✓

---

### DL-06: Layer astratto `emailService.ts`

**Data**: MVP 0.4
**Decisione**: isolare la chiamata a Resend in un modulo separato invece di chiamare l'SDK direttamente dalle API Routes
**Motivazione**: sostituibilità del provider email. Resend è la scelta attuale ma non necessariamente definitiva. Con il layer astratto, la sostituzione tocca un solo file.
**Stato**: confermata ✓

---

### DL-07: Audit trail su tabella dedicata

**Data**: MVP 0.3
**Decisione**: tabella `event_participant_audit` separata, con record immutabili
**Motivazione**: GDPR (tracciabilità), debugging operativo, compliance. Un log embedded in `event_participants` (es. campo JSONB) avrebbe reso l'audit modificabile e poco interrogabile.
**Stato**: confermata ✓

---

### DL-08: ExcelJS per export e non CSV

**Data**: MVP 0.3
**Decisione**: generare file `.xlsx` multi-foglio invece di CSV
**Motivazione**: l'export deve essere immediatamente utilizzabile dallo staff senza elaborazione manuale. Un CSV richiede importazione in Excel con gestione separatrice, encoding, ecc. Il file xlsx è un documento professionale pronto all'uso.
**Stato**: confermata ✓

---

### DL-09: Coesistenza flusso generico e flusso Epico

**Data**: MVP 0.5 (stimato)
**Decisione**: mantenere `/api/registrations` e `/register/[eventId]/` anche dopo l'introduzione del nuovo flusso Epico
**Motivazione**: evitare rischi di regressione durante lo sviluppo del nuovo flusso. Il vecchio flusso rimane funzionante come fallback.
**Conseguenza**: debito tecnico — due sistemi paralleli con modelli dati diversi.
**Stato**: da risolvere — il flusso legacy va deprecato e unificato.

---

### DL-10: `teacher_pair_label` come campo temporaneo

**Data**: durante sviluppo form avanzato
**Decisione**: aggiungere un campo testo flat per i maestri invece di costruire la join completa
**Motivazione**: velocità di sviluppo. La join `activity_teachers → teachers` richiedeva più logica e più dati da caricare. Il campo flat ha consentito di procedere senza bloccarsi.
**Conseguenza**: normalizzazione incompleta. La relazione corretta esiste (`activity_teachers`, `teachers`) ma non è pienamente sfruttata dal codice.
**Stato**: da completare — priorità bassa, non blocca funzionalità attuali.

---

### DL-11: QR Code come identità operativa, non prova di pagamento

**Data**: MVP 0.9.4 (Giugno 2026)
**Decisione**: il QR code viene generato al momento dell'iscrizione e non cambia mai; non riflette e non certifica lo stato del pagamento
**Motivazione**:
- Un QR generato solo dopo il pagamento completo costringerebbe il partecipante ad aspettare settimane prima di avere il proprio codice, complicando ogni comunicazione intermedia
- Lo stato del pagamento è dinamico (pending → deposit → paid): incorporarlo nel QR lo renderebbe obsoleto a ogni transizione, richiedendo rigenerazione e re-invio
- Includere dati finanziari nel payload QR esporrebbe informazioni personali a chiunque scansionasse il codice in sala
- La separazione identità/pagamento è più corretta semanticamente: il QR dice *chi sei*, non *quanto hai pagato*
**Conseguenze operative**:
- Il QR è inviato nella prima email (conferma iscrizione), non nella seconda (conferma pagamento)
- La seconda email ricorda di usare il QR già ricevuto — non ne genera uno nuovo
- L'API di check-in restituisce sempre `payment_status` insieme ai dati del partecipante
- Lo staff verifica il pagamento al check-in e decide come procedere in autonomia
- Un partecipante con acconto parziale ha un QR funzionante: la gestione dell'eccezione è operativa, non tecnica
**Alternative valutate**: QR generato solo a pagamento completo (scartata: ritarda l'identità operativa e complica le comunicazioni intermedie); QR con stato di pagamento embedded (scartata: obsolescenza, rischio GDPR)
**Stato**: confermata ✓
