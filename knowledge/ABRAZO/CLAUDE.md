@AGENTS.md

---

# ABRAZO — Documento Architetturale Ufficiale

**Versione documento**: 1.0.0
**Versione progetto**: MVP 0.9.2
**Ultimo aggiornamento**: Giugno 2026
**Maintainer**: Art&Tango

---

## Documentazione ufficiale

La directory [`docs/`](docs/) contiene la documentazione estesa del progetto. Consultarla quando serve un approfondimento specifico — `CLAUDE.md` è la memoria operativa sintetica per Claude, `docs/` è il manuale di riferimento.

| File | Quando usarlo |
|---|---|
| [`docs/01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) | Capire lo stack, le cartelle, le motivazioni delle scelte tecniche |
| [`docs/02_DATABASE.md`](docs/02_DATABASE.md) | Consultare lo schema DB, le relazioni, i debiti tecnici sul modello dati |
| [`docs/03_API_AND_FLOWS.md`](docs/03_API_AND_FLOWS.md) | Capire un flusso applicativo specifico o il contratto di una API Route |
| [`docs/04_GDPR_AND_SECURITY.md`](docs/04_GDPR_AND_SECURITY.md) | Valutare implicazioni GDPR di una nuova funzionalità; sicurezza; fornitori |
| [`docs/05_ROADMAP.md`](docs/05_ROADMAP.md) | Capire cosa manca, le prossime milestone, le priorità di sviluppo |
| [`docs/06_PROJECT_HISTORY.md`](docs/06_PROJECT_HISTORY.md) | Capire perché una decisione è stata presa; leggere il Decision Log |
| [`docs/07_ASSOCIATION_PRESENTATION.md`](docs/07_ASSOCIATION_PRESENTATION.md) | Presentare ABRAZO a Presidente, Vicepresidente o amministrazione |

**Regola**: quando una modifica cambia l'architettura in modo significativo (nuove tabelle, nuovi flussi, nuove dipendenze), aggiornare sia `CLAUDE.md` sia il file `docs/` pertinente.

---

## Indice

1. [Descrizione del progetto](#1-descrizione-del-progetto)
2. [Visione del progetto](#2-visione-del-progetto)
3. [Architettura tecnica](#3-architettura-tecnica)
4. [Principi architetturali](#4-principi-architetturali)
5. [Database](#5-database)
6. [Flussi applicativi](#6-flussi-applicativi)
7. [Conformità GDPR](#7-conformità-gdpr)
8. [Convenzioni del progetto](#8-convenzioni-del-progetto)
9. [Roadmap architetturale](#9-roadmap-architetturale)
10. [Stato attuale del progetto](#10-stato-attuale-del-progetto)
11. [Indicazioni per Claude](#11-indicazioni-per-claude)
12. [Report tecnico](#12-report-tecnico)

---

## 1. Descrizione del progetto

**ABRAZO** è la piattaforma digitale di gestione eventi dell'Associazione **Art&Tango**.

Il nome ABRAZO — l'abbraccio del Tango — riflette l'intenzione del progetto: avvolgere l'intera esperienza dell'evento, dalla prima iscrizione fino al momento in cui il partecipante sale in pista.

### Il problema che risolve

Prima di ABRAZO, la gestione degli eventi Art&Tango era interamente manuale:

- Iscrizioni raccolte via email o moduli cartacei
- Elenchi partecipanti su fogli Excel
- Pagamenti tracciati a mano, bonifici verificati uno per uno
- Check-in con liste stampate, segni di spunta, confusione
- Comunicazioni inviate individualmente
- Nessun dato storico aggregato né reportistica

Questo sistema diventava insostenibile con eventi di centinaia di partecipanti su più giorni, con decine di attività parallele (stage, milonghe, show, workshop), gestione di coppie leader/follower, e necessità di conformità GDPR.

### Cosa fa ABRAZO

ABRAZO digitalizza e automatizza l'intero ciclo di vita di un evento:

- Iscrizione online con selezione pacchetti e attività
- Calcolo automatico di totali, acconti e saldi
- Generazione di codici univoci e QR code personali
- Email di conferma automatizzata e bilingue
- Dashboard amministrativa per lo staff
- Check-in digitale via scanner QR (evento e singola attività)
- Tracciamento stati pagamento e aggiornamento in tempo reale
- Export dati in Excel per reportistica
- Audit trail completo di tutte le operazioni
- Conformità GDPR documentata

---

## 2. Visione del progetto

### ABRAZO non è solo Epico Tango Fest

Il primo caso d'uso concreto di ABRAZO è **Epico Tango Fest 2027**, il festival annuale di Art&Tango. Ma ABRAZO è stato progettato fin dall'inizio per essere **il gestionale completo dell'Associazione Art&Tango**, capace di gestire qualsiasi tipo di evento organizzato durante l'anno.

### Tipologie di eventi da gestire

| Tipo evento | Caratteristiche |
|---|---|
| **Festival** (es. Epico Tango Fest) | Multi-giorno, pacchetti complessi, coppie maestri, capienza limitata per attività |
| **Milonghe** | Serate di ballo, biglietteria semplice, check-in rapido |
| **Workshop / Stage** | Singola attività didattica, capienza limitata, spesso con quota di iscrizione |
| **Corsi** | Abbonamenti ricorrenti, gestione iscritti abituali, ruoli leader/follower |
| **Serate a tema** | Evento unico, registrazione libera o su invito |
| **Eventi futuri** | Qualunque format che Art&Tango vorrà introdurre |

### Principio guida della visione

> **Ogni funzionalità aggiunta a ABRAZO deve essere pensata per tutti gli eventi, non solo per Epico.**

L'architettura tecnica è multi-evento fin dai fondamenti: tutte le tabelle hanno `event_id`, tutti i flussi sono parametrici. Qualsiasi hardcoding verso un singolo evento è un debito tecnico da eliminare.

### Obiettivo a lungo termine

ABRAZO dovrà diventare lo strumento operativo quotidiano di Art&Tango: la segreteria utilizza la dashboard, i partecipanti si iscrivono online, lo staff fa check-in via smartphone, la direzione legge le statistiche aggregate su tutti gli eventi dell'anno.

---

## 3. Architettura tecnica

### Stack tecnologico

| Livello | Tecnologia | Versione | Motivazione |
|---|---|---|---|
| Framework | Next.js (App Router) | 16.2.x | SSR, API routes, Server Components integrati |
| UI Runtime | React | 19.x | Server/Client Component model maturo |
| Linguaggio | TypeScript | 5.x | Type safety, manutenibilità a lungo termine |
| Styling | Tailwind CSS | 4.x | Utility-first, nessuna dipendenza UI esterna |
| Database | Supabase (PostgreSQL) | 2.x SDK | BaaS completo: DB, Auth, Storage, Realtime |
| Email | Resend | 6.x | Deliverability affidabile, API semplice |
| QR Generation | `qrcode` | 1.5.x | Generazione PNG server-side |
| QR Scanning | `html5-qrcode` | 2.3.x | Scanner browser-based, camera posteriore |
| Export | ExcelJS | 4.4.x | Generazione xlsx multi-foglio server-side |
| Storage | Supabase Storage | — | S3-compatible, integrato con il DB |
| Deploy | Vercel | — | Deploy zero-config per Next.js |
| Font display | Cormorant Garamond | — | Eleganza tipografica per l'identità visiva |
| Font sistema | Geist Sans / Mono | — | Leggibilità e modernità |

### Variabili d'ambiente

```bash
# Client-side (esposte al browser)
NEXT_PUBLIC_SUPABASE_URL=          # URL del progetto Supabase
NEXT_PUBLIC_SUPABASE_ANON_KEY=     # Chiave pubblica (Row Level Security attiva)

# Server-side only (mai esposte al client)
SUPABASE_SERVICE_ROLE_KEY=         # Chiave admin (bypass RLS)
RESEND_API_KEY=                    # Chiave API per invio email
```

### Organizzazione delle cartelle

```
abrazo-prototype/
├── src/
│   ├── app/                           # Next.js App Router
│   │   ├── layout.tsx                 # Root layout (font, metadata)
│   │   ├── page.tsx                   # Home page pubblica
│   │   │
│   │   ├── admin/                     # Area amministrativa (futura auth)
│   │   │   ├── page.tsx               # Dashboard operativa principale
│   │   │   └── events/
│   │   │       ├── page.tsx           # Lista tutti gli eventi
│   │   │       └── [id]/              # Hub di un evento specifico
│   │   │           ├── page.tsx       # Dashboard evento (stats, link funzioni)
│   │   │           ├── participants/
│   │   │           │   ├── page.tsx              # Lista partecipanti
│   │   │           │   └── [participantId]/
│   │   │           │       └── page.tsx          # Scheda partecipante
│   │   │           ├── checkin/
│   │   │           │   ├── page.tsx
│   │   │           │   └── CheckinClient.tsx     # Scanner QR evento
│   │   │           ├── activities/
│   │   │           │   ├── page.tsx              # Lista attività + metriche
│   │   │           │   └── [activityId]/
│   │   │           │       ├── page.tsx
│   │   │           │       └── ActivityCheckinClient.tsx  # Scanner QR attività
│   │   │           ├── payments/
│   │   │           │   └── page.tsx              # Gestione stati pagamento
│   │   │           ├── search/
│   │   │           │   └── page.tsx              # Ricerca partecipanti
│   │   │           └── communications/
│   │   │               └── page.tsx              # Preview template email
│   │   │
│   │   ├── register/                  # Area pubblica iscrizioni
│   │   │   ├── [eventId]/             # Flusso generico (legacy)
│   │   │   │   ├── page.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   └── epico-tango-fest-2027/ # Flusso Epico (avanzato)
│   │   │       ├── page.tsx           # Server loader
│   │   │       ├── RegisterClient.tsx # Form bilingue con pacchetti/attività
│   │   │       └── success/[id]/
│   │   │           └── page.tsx       # Conferma + QR + istruzioni pagamento
│   │   │
│   │   ├── api/                       # API Routes (business logic server-side)
│   │   │   ├── registrations/
│   │   │   │   └── route.ts           # POST iscrizione generica (legacy)
│   │   │   ├── event-participants/
│   │   │   │   └── route.ts           # POST iscrizione Epico (principale)
│   │   │   ├── checkin/
│   │   │   │   ├── event/route.ts     # POST check-in evento
│   │   │   │   └── activity/route.ts  # POST check-in attività
│   │   │   └── events/[id]/
│   │   │       └── export-xlsx/
│   │   │           └── route.ts       # GET export Excel
│   │   │
│   │   └── test/
│   │       └── qr/page.tsx            # Pagina test QR (sviluppo)
│   │
│   ├── components/
│   │   └── AbrazoLogo.tsx             # Logo SVG component
│   │
│   └── lib/
│       ├── supabase.ts                # Client Supabase (anon key, browser-safe)
│       ├── supabaseAdmin.ts           # Client Supabase (service role, server-only)
│       ├── emailService.ts            # Invio email via Resend
│       ├── emailTemplates.ts          # Template HTML bilingue IT/EN
│       └── qr.ts                     # Generazione PNG QR code (Buffer)
│
├── public/
│   └── brand/
│       └── abrazo-logo.svg            # Logo vettoriale
│
├── CLAUDE.md                          # Questo documento
├── AGENTS.md                          # Regole Next.js per Claude
├── next.config.ts
├── tsconfig.json
├── tailwind.config.* (se presente)
└── package.json
```

---

## 4. Principi architetturali

Questa sezione documenta le decisioni progettuali fondamentali di ABRAZO e le motivazioni che le hanno generate. Queste decisioni non devono essere modificate senza una riflessione esplicita sul perché erano state prese.

### 4.1 Separazione tra Partecipante ed Evento

**Decisione**: la tabella `participants` contiene solo i dati anagrafici (nome, cognome, email). La relazione con un evento specifico è gestita da `event_participants`.

**Motivazione**: un partecipante può iscriversi a più eventi nel corso degli anni. Avere un'anagrafica separata consente di:
- riconoscere un iscritto che torna all'evento successivo
- evitare duplicazioni di dati personali
- costruire nel tempo una base partecipanti dell'Associazione
- applicare la minimizzazione GDPR: i dati anagrafici sono scritti una volta sola

**Implicazione**: qualsiasi funzionalità futura che riguarda un partecipante specifico (storico iscrizioni, comunicazioni, fidelizzazione) si appoggia a `participants.id` come chiave stabile.

### 4.2 QR Code come identità operativa, non prova di pagamento

**Decisione**: il QR code contiene un payload opaco (`ABRAZO:EVP:EVP-XXXXXX`) senza nessun dato personale leggibile. Il QR rappresenta l'**identità operativa** del partecipante dentro ABRAZO, non il suo stato di pagamento.

**Motivazione**:
- Un QR code che contenesse nome, email o altri dati sarebbe un rischio GDPR: chiunque scansionasse il codice otterrebbe dati personali anche senza autenticazione
- Il payload è un riferimento interno al database, non un documento d'identità e non una ricevuta di pagamento
- Il formato `ABRAZO:EVP:CODE` è namespace-safe: consente di distinguere diversi tipi di codice (`ABRAZO:REG:`, `ABRAZO:EVP:`) in futuro
- Separare identità da pagamento permette al partecipante di avere un codice stabile dall'iscrizione in poi, indipendentemente dall'evoluzione del suo stato di pagamento

**Conseguenze operative**:
- Il QR viene **generato al momento dell'iscrizione**, non quando il pagamento è completato
- Viene inviato nella **prima email di conferma iscrizione** (non nella seconda)
- Rimane **sempre lo stesso** per tutta la durata della relazione con l'evento
- È **valido anche se il partecipante ha versato solo l'acconto**
- Al check-in, il sistema restituisce il `payment_status` insieme ai dati del partecipante; lo staff può vedere se il pagamento è incompleto e indirizzare il partecipante alla Segreteria/cassa
- La **seconda email** (inviata al completamento del pagamento) non genera un nuovo QR: conferma l'iscrizione e ricorda di usare il QR già ricevuto

**Implicazione per il codice**: il QR PNG è generato nella POST di `/api/event-participants`, subito dopo la creazione del record. La risoluzione del payload in dati personali avviene sempre server-side tramite lookup autenticato.

### 4.3 Utilizzo di Supabase come BaaS

**Decisione**: Supabase è usato come backend completo (database PostgreSQL, storage, potenziale auth e realtime).

**Motivazione**:
- Evita di dover gestire infrastruttura database separata
- Storage S3-compatible integrato per i PNG dei QR code
- Row Level Security per future politiche di accesso per ruolo
- Potenziale evoluzione verso realtime (presenze live)
- SDK TypeScript maturo e manutenuto

**Implicazione**: non introdurre un database secondario o un ORM esterno. Tutta la persistenza passa per Supabase.

### 4.4 Due client Supabase con privilegi diversi

**Decisione**: esistono due istanze client distinte:
- `supabase.ts`: chiave anonima, usabile lato client, soggetta a Row Level Security
- `supabaseAdmin.ts`: service role key, esclusivamente server-side, bypass RLS

**Motivazione**:
- Evitare che la service role key venga esposta al browser (rischio sicurezza critico)
- Il client anon è sicuro per query pubbliche in fase di registrazione
- Il client admin è necessario per operazioni che richiedono visibilità completa (dashboard, check-in, export)

**Implicazione**: in qualsiasi Server Component o API Route che scrive dati o legge dati admin, usare `supabaseAdmin`. Mai usare `supabaseAdmin` in codice che viene eseguito lato browser.

### 4.5 Storage separato per i QR code

**Decisione**: i PNG dei QR code sono generati server-side e salvati su Supabase Storage, non inline nel database.

**Motivazione**:
- I BLOB binari nel database degradano le performance delle query
- Lo storage su S3 consente URL firmati con scadenza (sicurezza)
- La generazione una-tantum evita ricalcoli ripetuti
- Il path `events/{event_id}/event-participants/{participant_id}.png` è strutturato e prevedibile

**Implicazione**: il QR PNG è generato una volta al momento dell'iscrizione. Se si deve rigenerare (cambio codice, errore), va gestita la sovrascrittura esplicita del file sullo storage.

### 4.6 Audit trail immutabile

**Decisione**: ogni operazione significativa genera un record in `event_participant_audit`. I record di audit non vengono mai modificati o eliminati.

**Motivazione**:
- Conformità GDPR: tracciabilità di chi ha fatto cosa e quando
- Debugging operativo: lo staff può ricostruire la storia di ogni iscrizione
- Responsabilità: in caso di contestazione, l'audit è la prova
- Il valore dell'audit è zero se può essere alterato

**Implicazione**: le API che modificano stato devono sempre inserire un record audit. L'audit non è opzionale. Quando si aggiunge una nuova operazione, aggiungere anche il relativo evento audit.

### 4.7 Email automatizzate con template bilingue

**Decisione**: l'email di conferma è generata e inviata automaticamente al completamento dell'iscrizione, in italiano o inglese in base alla lingua scelta dal partecipante.

**Motivazione**:
- Art&Tango ospita partecipanti internazionali; una comunicazione in lingua corretta è un segnale di professionalità
- L'automazione elimina il lavoro manuale dello staff per ogni iscrizione
- Il template HTML branded rafforza l'identità visiva di ABRAZO/Art&Tango

**Implicazione**: il template in `emailTemplates.ts` deve essere aggiornato ogni volta che cambiano i dati esposti (nuovi campi, nuovo layout finanziario, nuovi consensi). Le modifiche al template devono essere testate su entrambe le lingue.

### 4.8 Business logic esclusivamente server-side

**Decisione**: tutta la logica che produce effetti permanenti (creazione iscrizioni, check-in, aggiornamento pagamenti, generazione QR, invio email) risiede nelle API Routes o nei Server Actions. Il client calcola solo ciò che serve per l'UX (preview totale, validazioni locali).

**Motivazione**:
- Il client non è affidabile: un utente malintenzionato può manipolare i valori inviati
- In particolare, i prezzi devono essere ricalcolati server-side attingendo dal database, non accettati dal client così come sono
- Le API Routes sono il confine di sicurezza dell'applicazione

**Implicazione**: una future evoluzione prioritaria è spostare il calcolo di totale/acconto/saldo nella POST di `/api/event-participants`, ignorando i valori inviati dal client e calcolandoli autonomamente dal DB.

### 4.9 Design mobile-first

**Decisione**: ogni interfaccia è progettata prima per smartphone, poi per desktop.

**Motivazione**:
- I partecipanti si iscrivono tipicamente da mobile
- Lo staff fa check-in con smartphone in mano in sala
- La dashboard admin è usata anche in mobilità
- Il Tango è un mondo fisico: l'interfaccia digitale segue le persone, non le scrivania

**Implicazione**: qualsiasi nuovo componente UI deve essere testato su viewport mobile (≤390px). Griglie a colonne singola su mobile, multi-colonna su desktop con breakpoint `md:` o `lg:`.

### 4.10 Sviluppo incrementale e validazione rapida

**Decisione**: il progetto avanza per milestone verticali (funzionalità complete end-to-end) piuttosto che per strati orizzontali.

**Motivazione**:
- Art&Tango ha bisogno di testare funzionalità reali su eventi reali prima di investire nell'infrastruttura completa
- Ogni milestone deve produrre valore operativo immediato
- Il feedback dello staff sul campo vale più di mesi di pianificazione teorica

**Implicazione**: non costruire infrastruttura generica in anticipo se non serve a nessuna funzionalità attuale. Aggiungere generalizzazione quando il secondo caso d'uso concreto appare.

---

## 5. Database

### Tabelle principali

#### `events`
Il catalogo degli eventi dell'Associazione.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | Identificativo univoco |
| `name` | text | Nome dell'evento |
| `slug` | text | URL-friendly identifier |
| `description` | text | Descrizione |
| `start_date` | date | Data inizio |
| `end_date` | date | Data fine |
| `venue_name` | text | Nome della sede |
| `city` | text | Città |
| `iban` | text | IBAN per bonifici |
| `beneficiary` | text | Beneficiario del pagamento |
| `payment_notes` | text | Note aggiuntive per il pagamento |
| `early_booking_*` | vari | Campi per sconti early booking |

#### `participants`
Anagrafica permanente dei partecipanti dell'Associazione.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | Identificativo univoco |
| `first_name` | text | Nome |
| `last_name` | text | Cognome |
| `email` | text | Email (identificatore univoco di fatto) |

#### `event_participants`
Il cuore del sistema: l'iscrizione di un partecipante a un evento specifico.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `participant_id` | UUID FK | → `participants.id` |
| `event_participant_code` | text | Codice univoco (es. `EVP-A3K9P2`) |
| `qr_payload` | text | Payload QR (es. `ABRAZO:EVP:EVP-A3K9P2`) |
| `qr_png_url` | text | URL del PNG su Supabase Storage |
| `role` | text | `leader` / `follower` / `entrambi` / `n_a` |
| `language` | text | `it` / `en` |
| `registration_status` | text | Stato iscrizione |
| `payment_status` | text | `pending` / `deposit` / `paid` |
| `total_amount` | numeric | Importo totale |
| `deposit_amount` | numeric | Acconto dovuto |
| `balance_amount` | numeric | Saldo residuo |
| `payment_method` | text | `bank_transfer` / altri futuri |
| `payment_deadline` | date | Scadenza pagamento saldo |
| `deposit_received_at` | timestamptz | Quando è stato ricevuto l'acconto |
| `paid_received_at` | timestamptz | Quando è stato ricevuto il saldo |
| `privacy_accepted` | boolean | Consenso privacy GDPR |
| `privacy_accepted_at` | timestamptz | Timestamp accettazione |
| `terms_accepted` | boolean | Accettazione regolamento evento |
| `terms_accepted_at` | timestamptz | Timestamp accettazione |
| `media_accepted` | boolean | Consenso foto/video |
| `media_accepted_at` | timestamptz | Timestamp accettazione |
| `created_at` | timestamptz | Data iscrizione |

#### `packages`
I pacchetti acquistabili per un evento (Full Pass, Stage Pass, ecc.).

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `name` | text | Nome del pacchetto |
| `price` | numeric | Prezzo intero |
| `deposit_amount` | numeric | Acconto specifico del pacchetto |
| `slug` | text | Identifier programmatico |
| `is_active` | boolean | Visibile e acquistabile |
| `is_public` | boolean | Visibile nella pagina pubblica |
| `sort_order` | integer | Ordine di visualizzazione |

#### `event_activities`
Le singole attività che compongono un evento (stage, milonga, show, workshop).

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `code` | text | Codice breve (es. `ST01`, `ML03`) |
| `activity_type` | text | `stage` / `milonga` / `show` / `workshop` |
| `title_it` | text | Titolo in italiano |
| `title_en` | text | Titolo in inglese |
| `room_name` | text | Sala / venue |
| `start_datetime` | timestamptz | Inizio |
| `end_datetime` | timestamptz | Fine |
| `price_amount` | numeric | Prezzo singola attività |
| `capacity_total` | integer | Capienza massima |
| `teacher_pair_label` | text | Etichetta coppia insegnanti |
| `performance_label_it` | text | Etichetta performance (italiano) |
| `is_public` | boolean | Visibile nella registrazione pubblica |

#### `event_participant_activities`
Le attività prenotate da ogni iscritto, con logica di pricing.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `event_participant_id` | UUID FK | → `event_participants.id` |
| `activity_id` | UUID FK | → `event_activities.id` |
| `price_amount` | numeric | Prezzo di listino |
| `discount_amount` | numeric | Sconto applicato |
| `final_amount` | numeric | Importo effettivo pagato |
| `source_type` | text | `package` / `single_selection` |
| `package_id` | UUID FK | → `packages.id` (se coperta da pacchetto) |
| `status` | text | Stato prenotazione |
| `created_at` | timestamptz | |

#### `package_activities`
Molti-a-molti: quali attività sono incluse in ciascun pacchetto.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `package_id` | UUID FK | → `packages.id` |
| `activity_id` | UUID FK | → `event_activities.id` |

#### `teacher_couples`
Le coppie di maestri ospitate a un evento, con dati per la visualizzazione nel form.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `display_name` | text | Nome visualizzato (es. "Juan & Maria") |
| `website_url` | text | Sito web della coppia |
| `photo_url` | text | Foto (futura) |
| `sort_order` | integer | Ordine di visualizzazione |
| `is_active` | boolean | Visibile nel form |

#### `teachers` / `activity_teachers`
Molti-a-molti tra attività e insegnanti singoli.

#### `checkins`
Registro delle presenze fisiche verificate con QR scanner.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | |
| `event_participant_id` | UUID FK | → `event_participants.id` |
| `event_id` | UUID FK | → `events.id` |
| `checkin_type` | text | `event` / `session` |
| `checked_in_at` | timestamptz | Momento del check-in |
| `checked_in_by` | text | Identificativo operatore (futuro: da auth) |
| `context_type` | text | Tipo di contesto (es. `activity`) |
| `context_label` | text | Etichetta leggibile del contesto |
| `context_id` | UUID | ID dell'attività (per checkin_type=session) |
| `created_at` | timestamptz | |

#### `event_participant_audit`
Log immutabile di tutte le operazioni su ogni iscrizione.

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id` | UUID PK | |
| `event_participant_id` | UUID FK | |
| `event_id` | UUID FK | |
| `event_type` | text | Tipo di evento (es. `registration_created`, `payment_status_changed`) |
| `event_description` | text | Descrizione leggibile |
| `operator_name` | text | Chi ha eseguito l'operazione |
| `context_type` | text | Contesto aggiuntivo |
| `context_id` | UUID | ID risorsa coinvolta |
| `context_label` | text | Etichetta leggibile |
| `created_at` | timestamptz | Timestamp immutabile |

### Storage

**Bucket**: `registration-qr`
**Path pattern**: `events/{event_id}/event-participants/{participant_id}.png`
**Formato**: PNG 512×512 px, margine 2, error correction "M"
**Accesso**: URL pubblico o firmato (da valutare per sicurezza)

### Relazioni principali

```
events (1)
  ├── event_participants (N)    ← ogni iscrizione
  │     ├── participants (1)   ← anagrafica
  │     ├── event_participant_activities (N)
  │     │     ├── event_activities (1)
  │     │     └── packages (1, opzionale)
  │     ├── checkins (N)
  │     └── event_participant_audit (N)
  │
  ├── packages (N)
  │     └── package_activities (N)
  │           └── event_activities (1)
  │
  ├── event_activities (N)
  │     └── activity_teachers (N)
  │           └── teachers (1)
  │
  └── teacher_couples (N)
```

### State machine del pagamento

```
[pending] ──→ [deposit] ──→ [paid]
    ↑               │           │
    └───────────────┘           │
    └───────────────────────────┘
```

Ogni transizione viene registrata in `event_participant_audit` con timestamp `deposit_received_at` o `paid_received_at` su `event_participants`.

---

## 6. Flussi applicativi

### 6.1 Iscrizione (flusso Epico Tango Fest)

```
[Browser] RegisterClient.tsx
  │
  ├─ Utente seleziona: pacchetto, attività, ruolo, lingua
  ├─ Calcolo locale (preview): totale, acconto, saldo
  ├─ Utente accetta: privacy, termini, media
  │
  └─ POST /api/event-participants
        │
        ├─ Valida consensi obbligatori (privacy + terms)
        ├─ Upsert participants (find or create by email)
        ├─ Genera codice EVP-XXXXXX (6 char alfanumerici)
        ├─ Crea event_participants con tutti i campi
        ├─ Inserisce event_participant_activities
        │    ├─ Attività coperte dal pacchetto → source_type="package", final_amount=0
        │    └─ Attività singole → source_type="single_selection", final_amount=price
        ├─ Genera QR PNG via generateQrPngBuffer()
        ├─ Carica PNG su Supabase Storage
        ├─ Inserisce audit "registration_created"
        ├─ Invia email di conferma via Resend
        │
        └─ Response: { id, code, qr_payload, qr_png_url, totali }

[Browser] → redirect a /success/[id]?lang=it|en
```

### 6.2 Generazione QR Code

```
generateQrPngBuffer(payload: string): Promise<Buffer>
  │
  ├─ Input: "ABRAZO:EVP:EVP-XXXXXX"
  ├─ qrcode library → PNG 512×512, margine 2, errorCorrectionLevel "M"
  ├─ Output: Buffer PNG
  │
supabaseAdmin.storage
  .from("registration-qr")
  .upload("events/{event_id}/event-participants/{participant_id}.png", buffer)
```

### 6.3 Email di conferma

```
buildRegistrationConfirmationEmail(data: RegistrationEmailData)
  │
  ├─ language "it" | "en" → seleziona stringhe
  ├─ Costruisce subject, text, html
  │
sendRegistrationConfirmationEmail({ to, subject, html, text })
  │
  ├─ Resend.emails.send()
  ├─ From: "ABRAZO <onboarding@resend.dev>"  ← da aggiornare con dominio reale
  └─ Return: { ok: boolean, data?, error? }
```

**Contenuto email**:
- Dati iscrizione (nome, codice, ruolo)
- Lista pacchetti acquistati
- Lista attività prenotate
- Riepilogo finanziario (totale, acconto, saldo)
- Istruzioni bonifico (beneficiario, IBAN, causale, scadenza)
- Consensi GDPR accettati (con timestamp)
- Nota lingua (bilingue IT/EN)

### 6.4 Verifica e gestione pagamenti

```
Admin: /admin/events/[id]/payments
  │
  ├─ Lista partecipanti con stato corrente (pending / deposit / paid)
  │
  ├─ "Segna acconto" → Server Action
  │    ├─ UPDATE event_participants SET payment_status="deposit", deposit_received_at=now()
  │    └─ INSERT audit "payment_status_changed" → deposit
  │
  ├─ "Segna saldato" → Server Action
  │    ├─ UPDATE event_participants SET payment_status="paid", paid_received_at=now()
  │    └─ INSERT audit "payment_status_changed" → paid
  │
  └─ "Rimetti pending" → Server Action
       ├─ UPDATE event_participants SET payment_status="pending"
       └─ INSERT audit "payment_status_changed" → pending
```

### 6.5 Check-in evento

```
Admin: /admin/events/[id]/checkin (CheckinClient.tsx)
  │
  ├─ Staff scansiona QR con camera posteriore (html5-qrcode)
  │   oppure digita payload manualmente
  │
  └─ POST /api/checkin/event { qr_payload, event_id }
        │
        ├─ SELECT event_participants WHERE qr_payload = ?
        ├─ SELECT checkins WHERE event_participant_id = ? AND checkin_type = "event"
        │
        ├─ Se già presente → { already_checked_in: true, participant }
        │
        └─ Se nuovo:
             ├─ INSERT checkins (checkin_type="event")
             ├─ INSERT audit "event_checkin_completed"
             └─ { already_checked_in: false, participant, checkin }
```

### 6.6 Check-in attività

```
Admin: /admin/events/[id]/activities/[activityId] (ActivityCheckinClient.tsx)
  │
  └─ POST /api/checkin/activity { qr_payload, event_id, activity_id }
        │
        ├─ SELECT event_participants WHERE qr_payload = ?
        ├─ SELECT event_participant_activities WHERE event_participant_id = ? AND activity_id = ?
        │    └─ Se non prenotato → errore 400
        ├─ SELECT checkins WHERE ... AND checkin_type="session" AND context_id=activity_id
        │
        ├─ Se già presente → { already_checked_in: true }
        │
        └─ Se nuovo:
             ├─ INSERT checkins (checkin_type="session", context_id=activity_id)
             ├─ INSERT audit "activity_checkin_completed"
             └─ { already_checked_in: false, participant, activity, checkin }
```

### 6.7 Export Excel

```
GET /api/events/[id]/export-xlsx
  │
  ├─ Sheet 1 "Iscrizioni": dati master partecipanti
  │    Colonne: Codice, Nome, Email, Ruolo, Totale, Acconto, Saldo, Stato, Data
  │
  ├─ Sheet 2 "Attività": cross-reference prenotazioni
  │    Colonne: Codice, Nome, Attività, Tipo, Sala, Data/Ora, Maestri, Sorgente, Prezzo
  │
  ├─ Sheet 3 "Riepilogo": statistiche aggregate
  │    Righe: Totale iscritti, Per stato pagamento, Totali economici
  │
  └─ Response: attachment "epico-tango-fest-2027-iscrizioni.xlsx"
```

---

## 7. Conformità GDPR

La conformità GDPR è un **requisito progettuale non negoziabile** di ABRAZO, non una funzionalità aggiuntiva. Ogni nuova funzione deve essere valutata alla luce dei principi descritti in questa sezione.

### 7.1 Minimizzazione dei dati

**Principio**: raccogliere solo i dati strettamente necessari per la funzione specifica.

- Nel form di iscrizione: solo nome, cognome, email, ruolo nel ballo, lingua preferita
- Nessuna data di nascita, numero di telefono, indirizzo o altro dato non necessario
- Se in futuro si volessero raccogliere dati aggiuntivi, documentare la finalità specifica

### 7.2 QR Code privo di dati personali

**Principio**: il QR code non deve contenere né rivelare dati personali.

- Il payload `ABRAZO:EVP:EVP-XXXXXX` è un identificatore opaco
- Non contiene nome, email, ruolo né alcun dato personale
- La risoluzione avviene solo tramite lookup server-side autenticato
- Chiunque fotografasse un QR code non otterrebbe alcuna informazione personale

### 7.3 Consenso esplicito e tracciato

**Principio**: ogni consenso deve essere esplicito, separato e con timestamp.

Tre consensi distinti raccolti al momento dell'iscrizione:
1. **Privacy notice** (`privacy_accepted`, `privacy_accepted_at`): trattamento dati per gestione evento
2. **Event terms** (`terms_accepted`, `terms_accepted_at`): regolamento dell'evento
3. **Media release** (`media_accepted`, `media_accepted_at`): utilizzo foto e video

- I consensi privacy e termini sono **obbligatori** per completare l'iscrizione
- Il consenso media è raccolto ma non obbligatorio (da verificare con legale)
- I timestamp sono salvati con timezone nel database
- I consensi e i timestamp sono visibili nella scheda partecipante admin e nell'email di conferma

### 7.4 Audit delle operazioni

**Principio**: ogni operazione sui dati personali deve essere tracciata.

La tabella `event_participant_audit` registra:
- Chi ha effettuato l'operazione (`operator_name`)
- Quando (`created_at`)
- Cosa ha fatto (`event_type`, `event_description`)
- Su quale partecipante (`event_participant_id`)

I record di audit **non devono mai essere modificati o eliminati**. Sono la prova documentale delle operazioni effettuate.

### 7.5 Separazione dati pubblici e amministrativi

**Principio**: i dati personali sono accessibili solo alle funzioni che ne hanno bisogno.

- Il client Supabase con chiave anonima (`supabase.ts`) è usato solo per query pubbliche
- Tutte le operazioni su dati personali usano `supabaseAdmin.ts` (service role) esclusivamente lato server
- L'area admin è (futura) protetta da autenticazione staff
- Il QR code pubblico non espone dati personali (vedi 7.2)

### 7.6 Export controllati

**Principio**: il download di dati personali in massa deve essere tracciabile e controllato.

- L'export Excel è disponibile solo nell'area admin
- In futuro, l'export dovrebbe essere limitato a utenti autenticati con ruolo appropriato
- Considerare di loggare gli export in audit (chi ha scaricato cosa e quando)

### 7.7 Conservazione dei dati

**Principio**: i dati personali non devono essere conservati oltre il necessario.

- Definire una policy di conservazione (es. dati eliminati X anni dopo l'evento)
- Valutare con il DPO/legale Art&Tango i termini di conservazione appropriati
- Predisporre una funzione di cancellazione account/iscrizione (non ancora implementata)

### 7.8 Cancellazione su richiesta

**Principio**: il partecipante ha diritto alla cancellazione dei propri dati (Art. 17 GDPR).

- Non ancora implementato in MVP 0.9.0
- Da prevedere: procedura admin per anonimizzare o eliminare un record partecipante
- L'anonimizzazione (sostituzione dei dati personali con placeholder) è preferibile all'eliminazione per preservare la coerenza dei dati aggregati e dell'audit trail
- I consensi e i timestamp devono essere conservati anche dopo cancellazione (prova del trattamento)

### 7.9 Sicurezza tecnica

- Comunicazioni HTTPS in tutti gli ambienti
- Variabili d'ambiente per tutte le credenziali (mai hardcoded)
- Service role key mai esposta al client
- URL dei QR su storage: valutare signed URL con scadenza invece di URL pubblici permanenti

---

## 8. Convenzioni del progetto

### Naming

| Tipo | Convenzione | Esempio |
|---|---|---|
| Componenti React | PascalCase | `RegisterClient.tsx`, `CheckinClient.tsx` |
| File di libreria | camelCase | `emailService.ts`, `supabaseAdmin.ts` |
| API Route files | `route.ts` in cartelle REST | `app/api/event-participants/route.ts` |
| Server Actions | funzione `async` nel file della pagina | `async function updatePaymentStatus()` |
| Codici partecipante | `EVP-XXXXXX` (6 char alfanumerici maiuscoli) | `EVP-A3K9P2` |
| Codici generici legacy | `ABR-XXXXXX` | Usato in flusso generico obsoleto |
| QR payload | `ABRAZO:EVP:CODE` | `ABRAZO:EVP:EVP-A3K9P2` |
| Storage path | `events/{event_id}/{type}/{participant_id}.png` | |
| Colonne DB | snake_case | `first_name`, `payment_status`, `created_at` |
| Variabili env public | `NEXT_PUBLIC_` prefix | `NEXT_PUBLIC_SUPABASE_URL` |
| Variabili env server | Senza prefix | `SUPABASE_SERVICE_ROLE_KEY` |

### Pattern React

**Server Components** (default per i loader di dati):
```tsx
// page.tsx — nessun "use client", fetch dati direttamente
export default async function ParticipantsPage({ params }) {
  const data = await supabaseAdmin.from("event_participants").select(...)
  return <Table data={data} />
}
```

**Client Components** (solo dove serve interattività):
```tsx
"use client"
// CheckinClient.tsx, RegisterClient.tsx, form con useState
export default function CheckinClient({ eventId }) {
  const [result, setResult] = useState(null)
  // scanner, bottoni, fetch
}
```

**API Routes** (business logic di mutazione):
```tsx
// route.ts
export async function POST(request: Request) {
  const body = await request.json()
  // validazione, logica, DB writes, return Response
}
```

**Server Actions** (aggiornamenti admin semplici):
```tsx
"use server"
async function updatePaymentStatus(participantId: string, status: string) {
  await supabaseAdmin.from("event_participants").update({ payment_status: status })
  revalidatePath(...)
}
```

### Palette colori

| Token | Valore | Uso |
|---|---|---|
| Background principale | `#0f0f0f` | Sfondi pagina, card |
| Testo primario | `#f4efe7` | Corpo testo |
| Testo secondario | `#d8d0c8`, `#b8b0a8` | Label, testo attenuato |
| Oro (accent) | `#c89a4a` | Bordi, highlight, importi |
| Rosso alert | `#c52b3c`, `#ef3340` | CTA primario, importi totale |
| Verde successo | Tailwind `green-200` / `green-900` | Badge "pagato", check-in ok |
| Ambra avviso | Tailwind `amber-200` / `amber-900` | Badge "acconto" |
| Rosso errore | Tailwind `red-200` / `red-900` | Badge "da pagare" |
| Bordo sottile | `border-[#c89a4a]/20` | Separatori eleganti |

### Tipografia

- **Display / titoli**: Cormorant Garamond (serif), pesi 300-600
- **Body / UI**: Geist Sans (sans-serif)
- **Codice / monospace**: Geist Mono
- **Sizing responsivo**: `clamp()` per titoli, classi Tailwind per body

### Stile del codice TypeScript

- TypeScript strict, evitare `any`
- Nessun ORM: query Supabase dirette con `.from().select().eq()`
- Nessuna libreria UI component (no shadcn, no MUI, no Radix): tutto Tailwind custom
- Gestione errori con `try/catch` nelle API routes, return `Response` con status appropriato
- Nessun commento per ovvietà: commentare solo il perché non-ovvio

---

## 9. Roadmap architetturale

Questa sezione descrive l'evoluzione prevista di ABRAZO, organizzata per aree funzionali. Non è una pianificazione temporale ma una mappa delle direzioni architetturali.

### 9.1 Autenticazione e controllo accessi *(priorità critica)*

L'assenza di autenticazione è l'unico blocco al deploy in produzione reale.

- Login staff con Supabase Auth (email + password, o magic link)
- Middleware Next.js per proteggere tutte le route `/admin/*`
- Ruoli: `admin` (direzione), `staff` (segreteria), `checkin` (solo scanner)
- Row Level Security su Supabase per enforcement lato DB
- Identità operatore reale nel campo `checked_in_by` dei check-in

### 9.2 Area pubblica — Iscrizioni generalizzate

- Unificare il flusso Epico e il flusso generico in un'unica architettura parametrica
- Rimuovere l'hardcoding dell'event ID: ogni evento ha la propria URL derivata dallo `slug`
- Ricalcolo prezzi server-side (vedi principio 4.8)
- Pagina lista eventi pubblici per partecipanti
- Portale partecipante: "cerca la mia iscrizione" via email + codice

### 9.3 Segreteria — Gestione dati

- Pannello CRUD per eventi: creazione, modifica, attivazione/disattivazione
- Pannello CRUD per pacchetti e attività
- Gestione coppie di maestri e teacher couples
- Waiting list per attività a capienza limitata
- Gestione coppie leader/follower (matching, bilanciamento ruoli)
- Modifica iscrizione post-registrazione (cambio pacchetto, aggiunta attività)

### 9.4 Check-in — Operazioni in sala

- Check-in real-time con Supabase Realtime (live dashboard presenze)
- Notifica visiva su schermo condiviso (es. monitor in sala) a ogni check-in
- Modalità offline con sync differito (per venue con connessione instabile)
- Stampa badge QR personalizzati
- Dashboard presenze per sala / attività in tempo reale

### 9.5 Comunicazioni — Email e notifiche

- Invio email in batch (comunicazioni di massa a tutti gli iscritti di un evento)
- Template multipli per diversi tipi di comunicazione (promemoria, aggiornamenti, ringraziamenti)
- Dominio email produzione configurato su Resend
- Notifiche push per staff (nuova iscrizione, pagamento ricevuto)
- Integrazione Bot Telegram per notifiche staff in tempo reale

### 9.6 Dashboard Direzione — Reportistica

- Statistiche aggregate su tutti gli eventi dell'anno
- Andamento iscrizioni nel tempo (grafico)
- Revenue per evento, per pacchetto, per tipo attività
- Confronto anno su anno
- Occupancy rate per attività (iscritti / capienza)
- Export report PDF per riunioni di board

### 9.7 Amministrazione — Pagamenti avanzati

- Integrazione pagamento online (Stripe o similar)
- Ricevuta digitale automatica a pagamento confermato
- Rimborsi e note credito
- Riconciliazione automatica bonifici (in integrazione con home banking, futuro)
- Fatturazione automatizzata

### 9.8 Gestione volontari

- Anagrafica volontari separata dai partecipanti
- Assegnazione turni e postazioni
- QR code volontario distinto
- Check-in turno volontario
- Comunicazioni dedicate

### 9.9 API esterne e integrazioni

- API REST documentata per integrazioni esterne (sito Art&Tango, app mobile futura)
- Webhook per notifiche a sistemi esterni (es. CRM, mailing list)
- Importazione partecipanti da CSV (migrazione dati storici)
- Integrazione Google Calendar per pubblicazione eventi

---

## 10. Stato attuale del progetto

**Versione**: MVP 0.9.0
**Stato**: funzionante in sviluppo/staging, primo deploy produzione in preparazione

### Già implementato e funzionante

**Area pubblica**
- [x] Home page con branding ABRAZO e roadmap visiva
- [x] Flusso iscrizione completo Epico Tango Fest 2027 (pacchetti, attività, GDPR)
- [x] Selezione pacchetti con calcolo automatico attività coperte
- [x] Selezione attività singole con pricing separato
- [x] Visualizzazione coppie di maestri con highlight attività correlate
- [x] Switch di lingua IT/EN nel form
- [x] Calcolo acconto/saldo (70% default o custom per pacchetto)
- [x] Validazione consensi GDPR (privacy e termini obbligatori)
- [x] Pagina success con QR code, riepilogo finanziario, istruzioni bonifico
- [x] Flusso iscrizione generico `/register/[eventId]` (legacy, funzionante)

**Generazione e storage QR**
- [x] Generazione PNG 512×512 con payload `ABRAZO:EVP:CODE`
- [x] Upload su Supabase Storage bucket `registration-qr`
- [x] Display QR nella pagina success
- [x] Display QR nella scheda partecipante admin
- [x] Pagina test QR per sviluppo

**Email**
- [x] Template HTML bilingue IT/EN dark-themed
- [x] Invio automatico via Resend al completamento iscrizione
- [x] Contenuto: dati iscrizione, pacchetti, attività, riepilogo finanziario, istruzioni bonifico, consensi GDPR
- [x] Preview template nell'admin (`/communications`)

**Area amministrativa**
- [x] Dashboard operativa con statistiche evento attivo
- [x] Lista eventi
- [x] Hub evento con link a tutte le funzioni operative
- [x] Lista partecipanti con stati pagamento e badge ruolo
- [x] Scheda partecipante dettaglio (dati, attività, GDPR, QR, audit trail)
- [x] Check-in evento via QR scanner (html5-qrcode, camera posteriore)
- [x] Input manuale payload per check-in senza camera
- [x] Check-in per singola attività (con verifica prenotazione)
- [x] Prevenzione check-in duplicati con warning visivo
- [x] Lista attività con metriche Iscritti/Presenti/Assenti
- [x] Gestione stati pagamento (pending/deposit/paid) con Server Actions
- [x] Ricerca partecipanti
- [x] Export Excel (3 fogli: Iscrizioni, Attività, Riepilogo)
- [x] Audit trail visibile nella scheda partecipante
- [x] **Modulo Segreteria** (`/admin/events/[id]/segreteria`): inbox operativa pagamenti, Server Actions confirmDeposit/confirmPayment, feedback redirect con banner, template email conferma pagamento, manuale operativo in `docs/manuals/SEGRETERIA.md`

### Non ancora implementato

**Critico per produzione**
- [ ] Autenticazione area admin (nessun layer auth al momento)
- [ ] Dominio email produzione per Resend (oggi `onboarding@resend.dev`)
- [ ] Ricalcolo prezzi server-side (oggi accettati dal client)
- [ ] Operator identity reale nel check-in (oggi `"staff-demo"`)

**Prossime milestone**
- [ ] Generalizzazione flusso iscrizione (slug-based, rimozione hardcoding)
- [ ] CRUD eventi, pacchetti, attività nell'admin
- [ ] Waiting list per attività a capienza limitata
- [ ] Gestione coppie leader/follower
- [ ] Email batch / comunicazioni di massa
- [ ] Dashboard statistiche multi-evento
- [ ] Integrazione pagamento online
- [ ] Procedura cancellazione dati GDPR
- [ ] Export audit log per compliance

---

## 11. Indicazioni per Claude

Questa sezione contiene le regole che Claude deve seguire in ogni sessione di lavoro su ABRAZO.

### Regole fondamentali

**Non eseguire refactoring non richiesti.**
Se durante il lavoro si individua codice migliorabile ma la richiesta non lo riguarda, segnalarlo nel report finale ma non toccarlo. Il refactoring non richiesto introduce rischi di regressione e rallenta il lavoro produttivo.

**Proporre modifiche piccole e incrementali.**
Preferire dieci modifiche da 10 righe a una modifica da 100 righe. Le modifiche piccole sono più facili da revisionare, testare e revertire. Nessuna riscrittura di pagine intere se non esplicitamente richiesta.

**Mantenere coerenza con l'architettura esistente.**
Prima di scrivere qualsiasi codice, leggere i file esistenti che svolgono funzioni simili e seguirne lo stile. Se la pagina `/admin/events/[id]/payments/page.tsx` è un Server Component, la nuova pagina admin sarà un Server Component. Se `CheckinClient.tsx` usa `"use client"` con `useState` e `fetch`, il nuovo client component seguirà lo stesso pattern.

**Preservare la leggibilità del codice.**
Nomi di variabili descrittivi, funzioni brevi con responsabilità singola. Nessun commento per ovvietà. Commentare solo il perché non-ovvio (vincoli nascosti, workaround specifici, invarianti non evidenti).

**Evitare duplicazioni.**
Se una funzione fa già quello che serve, usarla. Se due componenti fanno cose simili, valutare se estrarre un'astrazione — ma solo se il secondo caso d'uso è già presente, non per anticipazione.

**Non aggiungere librerie senza discussione.**
Lo stack è intenzionalmente minimale. Ogni dipendenza aggiunta è un peso di manutenzione. Se si valuta una nuova libreria, proporre prima e aspettare conferma.

### Regole tecniche specifiche

**Leggere sempre AGENTS.md e i docs di Next.js prima di scrivere codice.**
Questa versione di Next.js ha breaking changes rispetto alle versioni precedenti. Leggere `node_modules/next/dist/docs/` per verificare le API corrette.

**Usare `supabaseAdmin` (service role) in tutte le API routes e Server Components che scrivono o leggono dati admin.**
Usare `supabase` (anon key) solo per query pubbliche lato client (form pubblici, pagine di registrazione).

**Ricalcolare sempre i prezzi server-side.**
Non fidarsi dei valori di prezzo inviati dal client. Nelle API routes, recuperare i prezzi da `packages.price`, `event_activities.price_amount` e `packages.deposit_amount` dal database.

**Aggiungere sempre un record audit per ogni operazione significativa.**
Creazione iscrizione, cambio stato pagamento, check-in, modifica dati: ogni operazione deve produrre un record in `event_participant_audit`.

**Eseguire `npm run build` dopo ogni modifica ai file applicativi.**
La build TypeScript identifica errori che lo sviluppo locale non sempre mostra. Non considerare una modifica completa finché la build non è pulita.

**Testare su viewport mobile dopo ogni modifica UI.**
Il design è mobile-first. Verificare che ogni nuovo componente funzioni su schermo ≤390px.

### Regole GDPR

- Non raccogliere dati personali non necessari alla funzione implementata
- Il QR code non deve mai contenere dati personali
- Ogni nuovo consenso deve avere campo boolean + campo timestamp separati
- Le operazioni sui dati personali devono produrre record audit
- Non esporre mai dati personali in URL pubblici

### Regole Git

**Proporre un commit Git significativo in italiano al termine di ogni milestone.**
Il messaggio di commit deve spiegare il perché della modifica, non solo il cosa. Esempi:

```
# Buono
feat: aggiunge autenticazione admin con Supabase Auth
refactor: generalizza flusso iscrizione su slug evento

# Non ottimale
update: modificato file
fix: sistemato bug
```

**Aggiornare questo documento** (`CLAUDE.md`) quando cambia l'architettura in modo significativo: nuove tabelle, nuovi flussi, nuove dipendenze, nuovi principi.

### Ordine di priorità quando si affronta un task

1. Leggere i file esistenti correlati al task
2. Capire il pattern già usato per funzioni simili
3. Proporre l'approccio (se non ovvio) prima di implementare
4. Implementare la modifica minima necessaria
5. Eseguire `npm run build`
6. Verificare su mobile se è una modifica UI
7. Proporre commit Git

---

## 12. Report tecnico

### Punti di forza dell'architettura

**1. Separazione netta tra Server e Client Components**
La distinzione è rispettata ovunque: i loader di dati sono Server Components, l'interattività è Client Components. Questo garantisce performance ottimali (HTML pre-renderizzato lato server) e sicurezza (nessuna logica sensibile nel browser).

**2. Audit trail completo e immutabile**
`event_participant_audit` è presente fin dalle fondamenta. Ogni operazione significativa è tracciata. Questo non è una funzionalità opzionale: è la spina dorsale della compliance GDPR e del debugging operativo.

**3. QR system end-to-end pensato bene**
Il formato `ABRAZO:EVP:CODE` è semantico (namespace), opaco (nessun dato personale), scalabile (si possono aggiungere tipi `ABRAZO:VOL:`, `ABRAZO:STAFF:`) e indipendente dall'ID database. Generazione, storage, display e scanning sono integrati in modo coerente.

**4. Bilingualismo by design**
La lingua è un cittadino di prima classe: stored nel DB, rispettata nei template email, controllata nell'UI. Non è un'aggiunta tardiva. Il toggle IT/EN nel form funziona anche per partecipanti che cambiano idea dopo aver iniziato la compilazione.

**5. Stack minimale e coerente**
Nessuna libreria UI esterna, nessun ORM, Tailwind puro. Questo riduce la superficie di manutenzione e rende il codice leggibile senza dover conoscere l'API di decine di componenti esterni.

**6. Modello dati ben normalizzato**
La separazione `participants` / `event_participants` è la scelta corretta per un sistema multi-evento. Le relazioni molti-a-molti (`package_activities`, `activity_teachers`) sono modellate correttamente. Il modello supporta già più eventi senza modifiche strutturali.

**7. Export Excel professionale e immediatamente utilizzabile**
Tre fogli strutturati con headers in grassetto, colonne auto-sized, dati pronti per uso operativo. Non è un export CSV grezzo: è un documento che lo staff può usare direttamente.

### Criticità individuate

**1. Nessuna autenticazione admin** *(critico)*
Le route `/admin/*` sono pubblicamente accessibili. Chiunque conosca l'URL può vedere tutti i dati dei partecipanti, fare check-in, modificare stati pagamento. È il gap più urgente prima di qualsiasi deploy in produzione con dati reali.

**2. Prezzi non ricalcolati server-side** *(sicurezza)*
La POST di `/api/event-participants` accetta i valori di totale, acconto e saldo calcolati dal client. Un utente malintenzionato potrebbe manipolare questi valori per iscriversi a prezzi alterati. I prezzi devono essere ricalcolati server-side dalla POST API attingendo dal database.

**3. Event ID hardcoded** *(architetturale)*
L'ID dell'evento Epico Tango Fest 2027 appare hardcoded in vari punti del codice. Se si aggiunge un secondo evento, bisogna cercare e modificare manualmente. La generalizzazione slug-based è necessaria per la vision multi-evento.

**4. Operator identity fittizia** *(compliance)*
`checked_in_by: "staff-demo"` nei check-in rende l'audit trail incompleto: non sappiamo chi ha effettivamente eseguito il check-in. L'identità reale dipende dall'implementazione dell'autenticazione.

**5. Email sender non produzione** *(operativo)*
`onboarding@resend.dev` è accettabile per sviluppo ma può essere filtrato come spam in produzione e non ha credibilità come mittente per i partecipanti. Serve un dominio verificato (es. `noreply@abrazo.app` o `iscrizioni@artango.it`).

**6. Due flussi di iscrizione divergenti** *(debito tecnico)*
Esistono due API (`/api/registrations` e `/api/event-participants`) e due form (`RegisterForm.tsx` e `RegisterClient.tsx`) con modelli dati diversi. Il flusso legacy dovrebbe essere deprecato e il sistema unificato attorno a `event_participants`.

**7. URL Storage pubblici permanenti** *(sicurezza GDPR)*
I QR code PNG sono probabilmente accessibili via URL pubblico permanente su Supabase Storage. Valutare l'uso di signed URL con scadenza, per evitare che QR code di partecipanti siano accessibili a chiunque conosca l'URL.

### Suggerimenti di miglioramento

1. **Autenticazione admin** con Supabase Auth — prima priorità assoluta, sblocca il deploy produzione
2. **Ricalcolo prezzi server-side** in `POST /api/event-participants` — elimina una vulnerabilità di sicurezza
3. **Signed URL per i QR PNG** su Supabase Storage con scadenza — rafforza la privacy GDPR
4. **Slug-based routing** per gli eventi — abilita la vision multi-evento e rimuove l'hardcoding
5. **Dominio email produzione** su Resend — migliora deliverability e credibilità
6. **Deprecare il flusso generico legacy** e unificare su `event_participants`
7. **Loggare gli export Excel** in audit — tracciabilità chi ha scaricato dati in massa
8. **Predisporre la procedura di cancellazione dati GDPR** — diritto all'oblio Art. 17
