# 02 — Modello Dati

**Versione**: 1.0.0 | **Progetto**: ABRAZO MVP 0.9.0 | **Aggiornato**: Giugno 2026

---

## Indice

1. [Principi di modellazione](#1-principi-di-modellazione)
2. [Schema ER semplificato](#2-schema-er-semplificato)
3. [Tabelle principali](#3-tabelle-principali)
4. [Tabelle di relazione e supporto](#4-tabelle-di-relazione-e-supporto)
5. [State machine: pagamento](#5-state-machine-pagamento)
6. [State machine: iscrizione](#6-state-machine-iscrizione)
7. [QR payload — formato e semantica](#7-qr-payload--formato-e-semantica)
8. [Audit trail](#8-audit-trail)
9. [Check-in](#9-check-in)
10. [Dati GDPR nel database](#10-dati-gdpr-nel-database)
11. [Storage: bucket e percorsi](#11-storage-bucket-e-percorsi)
12. [Note sulla normalizzazione](#12-note-sulla-normalizzazione)
13. [Debiti tecnici noti](#13-debiti-tecnici-noti)

---

## 1. Principi di modellazione

### Separazione anagrafica / evento

La scelta più importante del modello dati è la **separazione tra `participants` e `event_participants`**:

- `participants` contiene solo i dati anagrafici (nome, cognome, email). È l'identità stabile nel tempo di chi partecipa agli eventi Art&Tango.
- `event_participants` contiene tutto ciò che riguarda la partecipazione a un evento specifico: pacchetti scelti, ruolo, lingua, stato pagamento, consensi GDPR.

Questo consente di:
- riconoscere un partecipante che torna a eventi successivi
- evitare duplicazione di dati personali
- costruire nel tempo una base associativa (storico iscrizioni per persona)
- rispettare la minimizzazione GDPR (i dati anagrafici sono scritti una volta)

### Multi-evento fin dal primo giorno

Tutte le tabelle principali hanno `event_id` come foreign key verso `events`. Il modello supporta già più eventi in parallelo senza modifiche strutturali.

### Audit come requisito, non come opzione

La tabella `event_participant_audit` è parte integrante del modello, non un'aggiunta successiva. Ogni operazione significativa produce un record audit. I record non vengono mai modificati.

---

## 2. Schema ER semplificato

```
events (1) ──────────────────────────────────────────────────────────────────┐
  │                                                                           │
  ├── packages (N)                                                            │
  │     └── package_activities (N) ──── event_activities (1) ──────────────┐ │
  │                                           │                             │ │
  ├── event_activities (N) ──────────── activity_teachers (N)              │ │
  │     │                                     └── teachers (1)             │ │
  │     └── (referenced by event_participant_activities)                   │ │
  │                                                                         │ │
  ├── teacher_couples (N)                                                   │ │
  │                                                                         │ │
  └── event_participants (N) ──── participants (1)                          │ │
        │                                                                   │ │
        ├── event_participant_activities (N) ──────────────────────────────┘ │
        │     └── packages (1, opzionale) ──────────────────────────────────┘
        │
        ├── checkins (N)
        └── event_participant_audit (N)
```

---

## 3. Tabelle principali

### `events`

Il catalogo degli eventi dell'Associazione. Ogni riga è un festival, una milonga, un workshop, un corso.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | Identificativo univoco |
| `name` | text | Nome dell'evento (es. "Epico Tango Fest 2027") |
| `slug` | text | URL-friendly (es. `epico-tango-fest-2027`) |
| `description` | text | Descrizione pubblica |
| `start_date` | date | Data inizio |
| `end_date` | date | Data fine |
| `venue_name` | text | Nome della sede |
| `city` | text | Città |
| `iban` | text | IBAN per bonifici dei partecipanti |
| `beneficiary` | text | Intestatario del conto |
| `payment_notes` | text | Note aggiuntive per il pagamento (causale, scadenze) |
| `early_booking_*` | vari | Campi per sconti early booking (struttura da verificare) |

---

### `participants`

Anagrafica permanente. Una riga per persona, indipendente dagli eventi.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `first_name` | text | Nome |
| `last_name` | text | Cognome |
| `email` | text | Email — identificatore di fatto per upsert |

> **Nota**: al momento dell'iscrizione, il codice esegue un upsert per email: se il partecipante esiste già, viene riutilizzato il record esistente.

---

### `event_participants`

Il cuore del sistema. Una riga per ogni iscrizione a un evento specifico.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `participant_id` | UUID FK | → `participants.id` |
| `event_participant_code` | text | Codice leggibile (es. `EVP-A3K9P2`) |
| `qr_payload` | text | Stringa nel QR code (es. `ABRAZO:EVP:EVP-A3K9P2`) |
| `qr_png_url` | text | URL del PNG su Supabase Storage |
| `role` | text | `leader` / `follower` / `entrambi` / `n_a` |
| `language` | text | `it` / `en` — lingua preferita dell'iscritto |
| `registration_status` | text | Stato iscrizione (vedi state machine) |
| `payment_status` | text | `pending` / `deposit` / `paid` |
| `total_amount` | numeric | Importo totale iscrizione |
| `deposit_amount` | numeric | Acconto dovuto |
| `balance_amount` | numeric | Saldo residuo |
| `payment_method` | text | `bank_transfer` (unico metodo attuale) |
| `payment_deadline` | date | Scadenza pagamento saldo |
| `deposit_received_at` | timestamptz | Quando è stato registrato l'acconto |
| `paid_received_at` | timestamptz | Quando è stato registrato il saldo |
| `privacy_accepted` | boolean | Consenso privacy (obbligatorio) |
| `privacy_accepted_at` | timestamptz | Timestamp consenso privacy |
| `terms_accepted` | boolean | Accettazione regolamento evento (obbligatorio) |
| `terms_accepted_at` | timestamptz | Timestamp accettazione termini |
| `media_accepted` | boolean | Consenso foto/video |
| `media_accepted_at` | timestamptz | Timestamp consenso media |
| `created_at` | timestamptz | Data e ora iscrizione |

---

### `packages`

I pacchetti acquistabili per un evento (Full Pass, Stage Pass, Milonga Pass, ecc.).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `name` | text | Nome commerciale del pacchetto |
| `price` | numeric | Prezzo intero |
| `deposit_amount` | numeric | Acconto specifico del pacchetto (override del default 70%) |
| `slug` | text | Identifier programmatico (es. `full-pass`) |
| `is_active` | boolean | Il pacchetto è acquistabile |
| `is_public` | boolean | Il pacchetto è visibile nella pagina pubblica |
| `sort_order` | integer | Ordine di visualizzazione |

---

### `event_activities`

Le singole attività di un evento: stage, milonga, show, workshop, apertura.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `code` | text | Codice breve (es. `ST01`, `ML03`, `SH01`) |
| `activity_type` | text | `stage` / `milonga` / `show` / `workshop` / `lezione` |
| `title_it` | text | Titolo in italiano |
| `title_en` | text | Titolo in inglese |
| `room_name` | text | Sala o venue specifica |
| `start_datetime` | timestamptz | Inizio attività |
| `end_datetime` | timestamptz | Fine attività |
| `price_amount` | numeric | Prezzo singola attività (se acquistata separatamente) |
| `capacity_total` | integer | Capienza massima |
| `teacher_pair_label` | text | **Campo temporaneo** — vedi sezione [Debiti tecnici](#13-debiti-tecnici-noti) |
| `performance_label_it` | text | Etichetta per show/performance (italiano) |
| `is_public` | boolean | Visibile nella pagina pubblica di iscrizione |

---

### `event_participant_activities`

Le attività prenotate da ogni iscritto, con dettaglio del pricing.

| Colonna | Tipo | Note |
|---|---|---|
| `event_participant_id` | UUID FK | → `event_participants.id` |
| `activity_id` | UUID FK | → `event_activities.id` |
| `price_amount` | numeric | Prezzo di listino dell'attività |
| `discount_amount` | numeric | Eventuale sconto applicato |
| `final_amount` | numeric | Importo effettivo (0 se coperta da pacchetto) |
| `source_type` | text | `package` / `single_selection` |
| `package_id` | UUID FK | → `packages.id` — valorizzato se `source_type = "package"` |
| `status` | text | Stato della prenotazione |
| `created_at` | timestamptz | |

> **Logica di pricing**: se un'attività è inclusa nel pacchetto acquistato (`source_type = "package"`), `final_amount = 0`. Se è acquistata singolarmente (`source_type = "single_selection"`), `final_amount = price_amount - discount_amount`.

---

## 4. Tabelle di relazione e supporto

### `package_activities`

Molti-a-molti tra pacchetti e attività: definisce quali attività sono incluse in ciascun pacchetto.

| Colonna | Tipo |
|---|---|
| `package_id` | UUID FK → `packages.id` |
| `activity_id` | UUID FK → `event_activities.id` |

### `teacher_couples`

Le coppie di maestri ospitate a un evento, visualizzate nel form di iscrizione.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `event_id` | UUID FK | → `events.id` |
| `display_name` | text | Nome visualizzato (es. "Juan & María") |
| `website_url` | text | Sito web della coppia (opzionale) |
| `photo_url` | text | Foto della coppia (futuro) |
| `sort_order` | integer | Ordine di visualizzazione |
| `is_active` | boolean | Visibile nel form |

### `teachers`

Anagrafica dei singoli insegnanti.

| Colonna | Tipo |
|---|---|
| `id` | UUID PK |
| `first_name` | text |
| `last_name` | text |

### `activity_teachers`

Molti-a-molti tra attività e insegnanti singoli.

| Colonna | Tipo |
|---|---|
| `activity_id` | UUID FK → `event_activities.id` |
| `teacher_id` | UUID FK → `teachers.id` |

> **Nota**: la relazione `activity_teachers` / `teachers` è presente nel DB ma non ancora pienamente utilizzata dal codice. Il codice legge spesso `teacher_pair_label` direttamente. Vedi [Debiti tecnici](#13-debiti-tecnici-noti).

---

## 5. State machine: pagamento

Il campo `payment_status` di `event_participants` segue questa state machine:

```
                ┌──────────────────────────┐
                │                          │
     ┌──────────▼──────────┐   ┌───────────▼──────────┐   ┌────────────────────┐
     │       pending        │──▶│       deposit         │──▶│        paid         │
     │  (in attesa acconto) │   │  (acconto ricevuto)   │   │  (saldo ricevuto)   │
     └──────────────────────┘   └───────────────────────┘   └────────────────────┘
             ▲                            │                           │
             └────────────────────────────┘                           │
             └───────────────────────────────────────────────────────┘
```

Ogni transizione:
- È eseguita tramite Server Action o API Route (mai dal client direttamente)
- Aggiorna il campo `payment_status`
- Aggiorna il timestamp corrispondente (`deposit_received_at` o `paid_received_at`)
- Genera un record in `event_participant_audit`

---

## 6. State machine: iscrizione

Il campo `registration_status` di `event_participants` (struttura da verificare nel DB):

| Valore | Significato |
|---|---|
| `pending` | Iscrizione inviata, in attesa di conferma |
| `confirmed` | Iscrizione confermata (es. dopo acconto) |
| `cancelled` | Iscrizione annullata |

> **Da verificare**: i valori esatti di `registration_status` usati dal codice. Il campo è presente ma la state machine completa non è ancora documentata nel codice.

---

## 7. QR payload — formato e semantica

Il campo `qr_payload` in `event_participants` e la corrispondente stringa codificata nel PNG seguono questo formato:

```
ABRAZO:EVP:EVP-A3K9P2
  │      │    │
  │      │    └── event_participant_code (6 char alfanumerici maiuscoli)
  │      └─────── tipo record: EVP = Event Participant
  └────────────── namespace applicazione ABRAZO
```

### Proprietà del payload

- **Opaco**: non contiene nome, email, ruolo né alcun dato personale
- **Non parlante**: senza accesso al database, il payload non rivela nulla
- **Namespace-safe**: il prefisso `ABRAZO:EVP:` distingue questo tipo di QR da altri futuri
- **Human-readable**: il codice `EVP-XXXXXX` può essere digitato manualmente dallo staff

### Tipi di payload futuri previsti

```
ABRAZO:EVP:CODE    → Event Participant (attuale)
ABRAZO:VOL:CODE    → Volontario (futuro)
ABRAZO:STAFF:CODE  → Staff/operatore (futuro)
ABRAZO:GUEST:CODE  → Ospite / accredito (futuro)
```

---

## 8. Audit trail

La tabella `event_participant_audit` è il log immutabile di tutte le operazioni su ogni iscrizione.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `event_participant_id` | UUID FK | → `event_participants.id` |
| `event_id` | UUID FK | → `events.id` |
| `event_type` | text | Tipo di evento (vedi lista sotto) |
| `event_description` | text | Descrizione leggibile in linguaggio naturale |
| `operator_name` | text | Chi ha eseguito l'operazione (attualmente `"staff-demo"`) |
| `context_type` | text | Tipo di contesto aggiuntivo (es. `"activity"`) |
| `context_id` | UUID | ID della risorsa coinvolta (es. ID attività per check-in) |
| `context_label` | text | Etichetta leggibile del contesto |
| `created_at` | timestamptz | **Immutabile** — mai modificare questo valore |

### Tipi di evento audit utilizzati

| `event_type` | Quando viene generato |
|---|---|
| `registration_created` | Al completamento dell'iscrizione (POST `/api/event-participants`) |
| `payment_status_changed` | Ad ogni cambio di `payment_status` (admin payments) |
| `event_checkin_completed` | Al check-in evento (POST `/api/checkin/event`) |
| `activity_checkin_completed` | Al check-in attività (POST `/api/checkin/activity`) |

### Regola immutabile

I record di audit **non devono mai essere modificati o eliminati**. Sono la prova documentale delle operazioni effettuate. Qualsiasi bug che richieda la modifica di un record audit deve essere risolto aggiungendo un record correttivo, non modificando quello esistente.

---

## 9. Check-in

La tabella `checkins` registra ogni presenza fisica verificata tramite QR scanner.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | UUID PK | |
| `event_participant_id` | UUID FK | → `event_participants.id` |
| `event_id` | UUID FK | → `events.id` |
| `checkin_type` | text | `event` / `session` |
| `checked_in_at` | timestamptz | Momento esatto del check-in |
| `checked_in_by` | text | Operatore (futuro: da auth) |
| `context_type` | text | Tipo di contesto (per check-in attività: `"activity"`) |
| `context_label` | text | Etichetta leggibile (es. "ST01 — Stage Avanzato") |
| `context_id` | UUID | ID dell'attività (per `checkin_type = "session"`) |
| `created_at` | timestamptz | |

### Check-in tipo `event`

Un singolo record per partecipante per evento. Registra l'ingresso all'evento nella sua globalità. Viene controllata la presenza di un record esistente (duplicato) prima di crearne uno nuovo.

### Check-in tipo `session`

Un record per partecipante per singola attività (`context_id = activity.id`). Prima della creazione, il sistema:
1. Verifica che il partecipante sia prenotato per quell'attività (`event_participant_activities`)
2. Verifica che non esista già un check-in per quella coppia partecipante/attività

---

## 10. Dati GDPR nel database

I consensi GDPR sono memorizzati direttamente su `event_participants` per immediatezza e semplicità.

| Campo | Tipo | Obbligatorio | Descrizione |
|---|---|---|---|
| `privacy_accepted` | boolean | Sì | Trattamento dati per gestione evento |
| `privacy_accepted_at` | timestamptz | Sì | Momento esatto dell'accettazione |
| `terms_accepted` | boolean | Sì | Regolamento dell'evento |
| `terms_accepted_at` | timestamptz | Sì | Momento esatto dell'accettazione |
| `media_accepted` | boolean | No | Utilizzo foto e video durante l'evento |
| `media_accepted_at` | timestamptz | No | Momento esatto dell'accettazione |

### Principi applicati

- I consensi `privacy` e `terms` sono **obbligatori**: la POST API rifiuta l'iscrizione se non presenti
- I timestamp sono salvati con timezone (PostgreSQL `timestamptz`)
- I consensi e i loro timestamp sono esposti nella scheda partecipante admin e nell'email di conferma
- In caso di futura richiesta di cancellazione GDPR, i timestamp di consenso devono essere **conservati** anche dopo l'anonimizzazione degli altri dati personali (prova del trattamento)

---

## 11. Storage: bucket e percorsi

### Bucket `registration-qr`

Contiene i PNG dei QR code dei partecipanti.

**Path pattern**:
```
events/{event_id}/event-participants/{participant_id}.png
```

**Caratteristiche del file**:
- Formato: PNG
- Dimensioni: 512×512 px
- Margine: 2 moduli
- Error correction: livello "M" (15% di recupero dati)
- Sfondo: bianco
- Foreground: nero

**Accesso attuale**: URL pubblico permanente (da valutare migrazione a signed URL).

**Motivazione dello storage separato**: i BLOB binari nel database degradano le performance delle query. Lo storage S3-compatible consente URL diretti, CDN, e signed URL con scadenza.

---

## 12. Note sulla normalizzazione

Il modello è generalmente ben normalizzato. Le poche eccezioni sono debiti tecnici intenzionali accettati durante lo sviluppo rapido del MVP.

### Normalizzazione corretta

- Separazione `participants` / `event_participants`: ogni entità nel posto giusto
- `package_activities`: molti-a-molti corretto tra pacchetti e attività
- `activity_teachers`: molti-a-molti corretto tra attività e insegnanti
- `teacher_couples`: entità separata per le coppie di maestri ospitate
- `event_participant_activities`: tabella ponte con attributi (pricing, source_type)

### Aspetti parzialmente normalizzati

Il rapporto tra `event_activities`, `teachers`, `activity_teachers` e `teacher_couples` è corretto nella struttura ma non ancora pienamente sfruttato dal codice (vedi debiti tecnici).

---

## 13. Debiti tecnici noti

### DT-DB-01: `teacher_pair_label` — campo testo flat temporaneo

**Colonna**: `event_activities.teacher_pair_label`

**Problema**: questa colonna contiene il nome della coppia di insegnanti come stringa di testo libero (es. `"Juan & María"`). È un campo denormalizzato che duplica informazioni già presenti (o da strutturare) in `teachers` e `teacher_couples`.

**Motivazione dell'esistenza attuale**: durante lo sviluppo del MVP è stato necessario visualizzare rapidamente il nome dei maestri per ogni attività nel form di iscrizione e nelle card dell'admin. Costruire la join completa `event_activities → activity_teachers → teachers` + la visualizzazione della coppia avrebbe richiesto più tempo e logica di join complessa.

**Stato**: il campo va considerato un **fallback temporaneo**. Deve essere mantenuto finché non sarà completata e testata la relazione normalizzata:

```
event_activities (1)
  └── activity_teachers (N)
        └── teachers (1) → first_name + last_name
```

**Percorso di risoluzione**:
1. Assicurarsi che tutte le attività abbiano i record corrispondenti in `activity_teachers`
2. Aggiornare le query che leggono `teacher_pair_label` per usare la join normalizzata
3. Deprecare la colonna (mantenerla come nullable per retrocompatibilità)
4. Non eliminare la colonna finché tutte le query non sono migrate

**Rischio**: se si elimina `teacher_pair_label` prima di completare la migrazione, le attività che non hanno record in `activity_teachers` mostreranno il campo insegnanti vuoto.

---

### DT-DB-02: `event_participants.total_amount` calcolato lato client

**Problema**: i campi `total_amount`, `deposit_amount`, `balance_amount` sono calcolati nel form client-side e inviati alla POST API, che li accetta senza ricalcolo.

**Rischio**: un utente potrebbe manipolare il payload HTTP per iscriversi con importi alterati.

**Soluzione prevista**: la POST `/api/event-participants` deve ricalcolare autonomamente questi valori dal database (`packages.price`, `event_activities.price_amount`, `packages.deposit_amount`), ignorando i valori ricevuti dal client.

---

### DT-DB-03: Flusso legacy `registrations`

**Problema**: esiste una tabella `registrations` (e la relativa tabella `registration_items`) usata dal flusso legacy `/api/registrations`. Questo è un secondo modello dati parallelo a `event_participants`.

**Stato**: da deprecare e unificare. La tabella `registrations` non deve essere estesa con nuove funzionalità.
