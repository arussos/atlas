# 03 — API e Flussi Applicativi

**Versione**: 1.0.0 | **Progetto**: ABRAZO MVP 0.9.0 | **Aggiornato**: Giugno 2026

---

## Indice

1. [Panoramica delle API](#1-panoramica-delle-api)
2. [Flusso iscrizione pubblica](#2-flusso-iscrizione-pubblica)
3. [Selezione pacchetti e attività (carrello)](#3-selezione-pacchetti-e-attività-carrello)
4. [POST /api/event-participants — iscrizione principale](#4-post-apievent-participants--iscrizione-principale)
5. [Generazione QR e upload storage](#5-generazione-qr-e-upload-storage)
6. [Invio email Resend](#6-invio-email-resend)
7. [Pagina success](#7-pagina-success)
8. [Verifica e gestione pagamenti](#8-verifica-e-gestione-pagamenti)
9. [POST /api/checkin/event — check-in evento](#9-post-apicheckinvent--check-in-evento)
10. [POST /api/checkin/activity — check-in attività](#10-post-apicheckinactivity--check-in-attività)
11. [GET /api/events/[id]/export-xlsx](#11-get-apieventsidexport-xlsx)
12. [POST /api/registrations — flusso legacy](#12-post-apiregistrations--flusso-legacy)
13. [Flussi futuri previsti](#13-flussi-futuri-previsti)

---

## 1. Panoramica delle API

| Route | Metodo | Descrizione | Auth |
|---|---|---|---|
| `/api/event-participants` | POST | Iscrizione principale (Epico) | No (pubblica) |
| `/api/checkin/event` | POST | Check-in evento via QR | No (futura) |
| `/api/checkin/activity` | POST | Check-in singola attività via QR | No (futura) |
| `/api/events/[id]/export-xlsx` | GET | Export Excel partecipanti | No (futura) |
| `/api/registrations` | POST | Iscrizione generica legacy | No (legacy) |

> Tutte le route sono attualmente prive di autenticazione. L'autenticazione admin è la prossima priorità critica (vedi [05_ROADMAP.md](05_ROADMAP.md)).

### Principio comune di tutte le API

Ogni API Route in ABRAZO:
1. Legge il body dalla `Request` (`request.json()`)
2. Valida i campi obbligatori
3. Usa `supabaseAdmin` (service role key) per le operazioni DB
4. Restituisce `Response` con `Content-Type: application/json`
5. In caso di errore: status 4xx/5xx con campo `error` nel body
6. In caso di successo: status 200/201 con payload JSON

---

## 2. Flusso iscrizione pubblica

Il flusso principale si sviluppa su tre step, tutti in una singola pagina:

```
1. Dati personali         2. Pacchetti + Attività        3. Consensi + Invio
   ┌──────────────┐          ┌──────────────────┐           ┌──────────────┐
   │ Nome         │          │ Full Pass         │           │ ☐ Privacy    │
   │ Cognome      │   ───▶   │ Stage Pass        │   ───▶    │ ☐ Termini    │
   │ Email        │          │ [attività...]     │           │ ☐ Foto/Video │
   │ Ruolo        │          │ [coppie maestri]  │           │ [Iscriviti]  │
   │ Lingua       │          │ ──────────────    │           └──────────────┘
   └──────────────┘          │ Totale: €XXX      │
                             │ Acconto: €XXX     │
                             │ Saldo: €XXX       │
                             └──────────────────┘
```

### Server Component loader (`page.tsx`)

Prima che il form venga renderizzato, il Server Component carica dal DB:
- Dati dell'evento (`events`)
- Pacchetti disponibili (`packages` con `is_active=true`)
- Attività pubbliche (`event_activities` con `is_public=true`)
- Coppie di maestri attive (`teacher_couples` con `is_active=true`)
- Mappa pacchetto→attività (`package_activities`)

Questi dati vengono passati come props al Client Component.

### Client Component form (`RegisterClient.tsx`)

Il form è un Client Component (`"use client"`) che gestisce tutto lo stato locale:
- Campi del form (nome, cognome, email, ruolo, lingua)
- Pacchetti selezionati (array)
- Attività selezionate (Set di ID)
- Stato validazione e errori
- Preview finanziaria in tempo reale

Il submit invia una `fetch` POST a `/api/event-participants`.

---

## 3. Selezione pacchetti e attività (carrello)

ABRAZO non ha un "carrello" nel senso tradizionale (nessuna sessione persistente, nessun cookie). La selezione è **stateful nel Client Component** e viene inviata in un'unica transazione all'atto dell'iscrizione.

### Logica di selezione pacchetti

- L'utente può selezionare uno o più pacchetti (radio o checkbox, da verificare)
- Ogni pacchetto include un set di attività (definite in `package_activities`)
- Le attività incluse nel pacchetto vengono automaticamente aggiunte alla selezione
- Le attività coperte dal pacchetto hanno `final_amount = 0`

### Logica di selezione attività singole

- L'utente può selezionare attività non incluse nel pacchetto scelto
- Ogni attività singola ha un prezzo (`event_activities.price_amount`)
- Le attività singole hanno `source_type = "single_selection"` e `final_amount = price_amount`

### Calcolo finanziario lato client (preview)

```
total = somma(pacchetti.price) + somma(attivita_singole.price_amount)

deposit = se_pacchetto_selezionato
            ? pacchetto.deposit_amount       (importo custom del pacchetto)
            : total * 0.70                   (70% default)

balance = total - deposit
```

> **Attenzione**: questo calcolo è solo una preview per l'UX. I valori reali devono essere ricalcolati server-side nella POST API (debito tecnico DT-DB-02, vedi [02_DATABASE.md](02_DATABASE.md)).

### Highlight coppie di maestri

Nel form, le card delle coppie di maestri si evidenziano visivamente quando si selezionano attività correlate a quella coppia. La logica di correlazione usa `teacher_pair_label` come matching temporaneo (debito tecnico DT-DB-01).

---

## 4. POST /api/event-participants — iscrizione principale

**File**: `src/app/api/event-participants/route.ts`

### Request body

```typescript
{
  // Dati anagrafici
  firstName: string
  lastName: string
  email: string
  role: "leader" | "follower" | "entrambi" | "n_a"
  language: "it" | "en"

  // Selezioni
  packageIds: string[]          // UUID dei pacchetti selezionati
  activityIds: string[]         // UUID di tutte le attività (incluse quelle da pacchetto)

  // Finanziario (da client - TODO: ignorare e ricalcolare)
  totalAmount: number
  depositAmount: number
  balanceAmount: number

  // Consensi GDPR (obbligatori: privacy + terms)
  privacyAccepted: boolean
  termsAccepted: boolean
  mediaAccepted: boolean
}
```

### Sequenza di operazioni server-side

```
1. VALIDAZIONE
   └── Verifica privacyAccepted = true
   └── Verifica termsAccepted = true
   └── Se mancano → Response 400

2. UPSERT PARTICIPANT
   └── SELECT participants WHERE email = ?
   └── Se non esiste → INSERT participants
   └── Ottieni participant.id

3. GENERA CODICE
   └── Genera stringa casuale 6 char alfanumerici maiuscoli
   └── event_participant_code = "EVP-" + codice
   └── qr_payload = "ABRAZO:EVP:" + event_participant_code

4. CREA EVENT_PARTICIPANT
   └── INSERT event_participants con tutti i campi
   └── Ottieni event_participant.id

5. CREA ATTIVITÀ PRENOTATE
   └── Per ogni activityId:
        └── Determina se coperta da pacchetto (package_activities lookup)
        └── source_type = "package" | "single_selection"
        └── final_amount = 0 | price_amount
        └── INSERT event_participant_activities

6. GENERA QR PNG
   └── generateQrPngBuffer(qr_payload)
   └── Buffer PNG 512×512

7. UPLOAD STORAGE
   └── supabaseAdmin.storage.from("registration-qr")
       .upload("events/{event_id}/event-participants/{participant_id}.png", buffer)
   └── Ottieni URL pubblico

8. AGGIORNA QR URL
   └── UPDATE event_participants SET qr_png_url = url

9. INSERISCI AUDIT
   └── INSERT event_participant_audit
       event_type = "registration_created"

10. INVIA EMAIL
    └── buildRegistrationConfirmationEmail(data)
    └── sendRegistrationConfirmationEmail({ to, subject, html, text })

11. RESPONSE
    └── { id, code, qr_payload, qr_png_url, totali, email_preview }
```

### Response (200 OK)

```typescript
{
  event_participant_id: string
  event_participant_code: string
  qr_payload: string
  qr_png_url: string
  total_amount: number
  deposit_amount: number
  balance_amount: number
  email_sent: boolean
}
```

---

## 5. Generazione QR e upload storage

**File**: `src/lib/qr.ts`

```typescript
async function generateQrPngBuffer(payload: string): Promise<Buffer>
```

| Parametro QR | Valore |
|---|---|
| Dimensione | 512×512 px |
| Tipo output | PNG Buffer |
| Margine | 2 moduli |
| Error correction | "M" (15% recupero dati) |
| Colore foreground | nero |
| Colore background | bianco |

### Perché error correction "M" e non "H"?

Il livello "H" (30% recupero dati) genera un QR più denso e difficile da scansionare rapidamente. Il livello "M" è il compromesso ottimale per codici che non vengono stampati su superfici usurate o deteriorate, ma mostrati su schermo o stampati con buona qualità.

### Upload Supabase Storage

```typescript
supabaseAdmin.storage
  .from("registration-qr")
  .upload(
    `events/${eventId}/event-participants/${participantId}.png`,
    buffer,
    { contentType: "image/png", upsert: true }
  )
```

L'`upsert: true` consente la rigenerazione del QR in caso di errori senza fallire per file già esistente.

---

## 6. Invio email Resend

### Layer astratto (`src/lib/emailService.ts`)

```typescript
async function sendRegistrationConfirmationEmail({
  to: string,
  subject: string,
  html: string,
  text: string
}): Promise<{ ok: boolean, data?, error? }>
```

Il layer:
- Inizializza il client Resend con `RESEND_API_KEY`
- Imposta `from: "ABRAZO <onboarding@resend.dev>"` (da aggiornare in produzione)
- Se `RESEND_API_KEY` non è configurata: logga su console e restituisce `{ ok: false }`
- In caso di errore Resend: logga e restituisce `{ ok: false, error }`

### Template (`src/lib/emailTemplates.ts`)

```typescript
function buildRegistrationConfirmationEmail(
  data: RegistrationEmailData
): { subject: string, text: string, html: string }
```

Il tipo `RegistrationEmailData` include:
- Dati anagrafici (firstName, lastName, email)
- Codice iscrizione (participantCode)
- Nome evento (eventName)
- Dati finanziari (totalAmount, depositAmount, balanceAmount, balanceDeadline)
- Lingua (language: "it" | "en")
- Lista pacchetti e attività (per il riepilogo)
- Dati bancari (beneficiary, iban, paymentReference)

### Struttura dell'email HTML

- Dark theme: sfondo `#0f0f0f`, testo `#f4efe7`
- Identità visiva ABRAZO con colori oro e rosso
- Sezioni: intestazione → codice iscrizione in evidenza → pacchetti → attività → riepilogo finanziario → istruzioni bonifico → consensi GDPR → footer
- Formattazione valuta: `Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" })`
- Fallback plain text per client email che non supportano HTML

---

## 7. Pagina success

**File**: `src/app/register/epico-tango-fest-2027/success/[id]/page.tsx`

Server Component che carica dal DB:
- Dati `event_participants` per `id`
- Dati `participants` (join)
- Dati `event_participant_activities` con dettaglio attività
- URL del QR PNG da Supabase Storage

### Contenuto della pagina

| Sezione | Contenuto |
|---|---|
| **Intestazione** | Nome partecipante, codice `EVP-XXXXXX` |
| **QR Code** | Immagine PNG dal bucket, 48×48 display |
| **Riepilogo finanziario** | Totale (rosso), Acconto (oro), Saldo (oro) |
| **Istruzioni bonifico** | Beneficiario, IBAN, Causale (codice - cognome), Scadenza saldo |
| **Pagamento in sede** | Alternativa al bonifico (se prevista) |
| **Conferme GDPR** | Privacy ✓, Termini ✓, Foto/Video ✓/— |
| **Nota email** | "Controlla la casella Spam se non ricevi l'email" |

La lingua della pagina è determinata dal query param `?lang=it|en`.

---

## 8. Verifica e gestione pagamenti

**File**: `src/app/admin/events/[id]/payments/page.tsx`

### Visualizzazione

La pagina mostra una tabella con tutti i partecipanti dell'evento, con colonne:
- Codice EVP
- Nome e cognome
- Email
- Totale / Acconto / Saldo
- Stato attuale (badge colorato: verde/ambra/rosso)

### Azioni disponibili

Tre Server Actions per ogni riga:

**"Segna acconto"** → `payment_status = "deposit"`
```
UPDATE event_participants
  SET payment_status = "deposit",
      deposit_received_at = now()
  WHERE id = ?
INSERT event_participant_audit
  event_type = "payment_status_changed",
  event_description = "Acconto ricevuto — stato aggiornato a deposit"
```

**"Segna saldato"** → `payment_status = "paid"`
```
UPDATE event_participants
  SET payment_status = "paid",
      paid_received_at = now()
  WHERE id = ?
INSERT event_participant_audit
  event_type = "payment_status_changed",
  event_description = "Saldo ricevuto — stato aggiornato a paid"
```

**"Rimetti pending"** → `payment_status = "pending"`
```
UPDATE event_participants
  SET payment_status = "pending"
  WHERE id = ?
INSERT event_participant_audit
  event_type = "payment_status_changed",
  event_description = "Stato reimpostato a pending"
```

Dopo ogni azione: `revalidatePath()` per aggiornare la pagina.

---

## 9. POST /api/checkin/event — check-in evento

**File**: `src/app/api/checkin/event/route.ts`

### Request body

```typescript
{
  qr_payload: string   // es. "ABRAZO:EVP:EVP-A3K9P2"
  event_id: string     // UUID evento
}
```

### Sequenza

```
1. SELECT event_participants WHERE qr_payload = ? AND event_id = ?
   └── Se non trovato → Response 404 "Partecipante non trovato"

2. SELECT checkins
   WHERE event_participant_id = ?
     AND event_id = ?
     AND checkin_type = "event"
   └── Se trovato → Response 200 { already_checked_in: true, participant, checkin }

3. INSERT checkins
   { event_participant_id, event_id, checkin_type: "event",
     checked_in_at: now(), checked_in_by: "staff-demo",
     context_type: "event", context_label: "Ingresso evento" }

4. INSERT event_participant_audit
   { event_type: "event_checkin_completed", ... }

5. Response 200
   { already_checked_in: false, participant, checkin }
```

### Response (200 OK)

```typescript
{
  already_checked_in: boolean
  participant: {
    id, event_participant_code, selected_role,
    payment_status, total_amount, deposit_amount, balance_amount,
    participant: { first_name, last_name, email }
  }
  checkin?: {
    id, checked_in_at, checked_in_by
  }
}
```

I campi `total_amount`, `deposit_amount`, `balance_amount` sono inclusi per consentire alla UI di mostrare il saldo residuo senza ulteriori query. Il check-in viene sempre registrato indipendentemente dal `payment_status`.

### Interfaccia staff (CheckinClient.tsx)

- Scanner QR con camera posteriore (html5-qrcode)
- Input manuale payload per casi senza camera
- Flash verde su check-in riuscito
- Warning ambra su check-in duplicato
- `PaymentPanel` con badge, messaggio operativo e importi dopo ogni scan

### Nota: il QR non è una prova di pagamento

Il QR viene generato all'iscrizione e rimane valido indipendentemente dallo stato del pagamento. La response include sempre `payment_status` proprio per questo: è lo staff a decidere se consentire l'ingresso o indirizzare il partecipante alla Segreteria. Un partecipante con `payment_status = "deposit"` o `"pending"` scansionerà con successo, ma la card mostrerà il saldo dovuto.

---

## 10. POST /api/checkin/activity — check-in attività

**File**: `src/app/api/checkin/activity/route.ts`

### Request body

```typescript
{
  qr_payload: string   // es. "ABRAZO:EVP:EVP-A3K9P2"
  event_id: string     // UUID evento
  activity_id: string  // UUID attività specifica
}
```

### Differenze rispetto al check-in evento

1. **Verifica prenotazione**: prima di tutto, controlla che il partecipante sia prenotato per quell'attività specifica (`event_participant_activities`)
2. **checkin_type**: `"session"` invece di `"event"`
3. **context_id**: valorizzato con `activity_id`
4. **context_label**: include codice e titolo dell'attività (es. `"ST01 — Stage Avanzato"`)
5. **Rilevamento duplicato**: verifica per coppia `(event_participant_id, context_id)` con `checkin_type = "session"`

### Response aggiuntiva

La response include anche i dati dell'attività:

```typescript
{
  already_checked_in: boolean
  participant: { ... }
  activity: {
    id, code, title_it, title_en, activity_type, room_name, start_datetime
  }
  checkin?: { ... }
}
```

---

## 11. GET /api/events/[id]/export-xlsx

**File**: `src/app/api/events/[id]/export-xlsx/route.ts`

### Struttura del file generato

Il file `.xlsx` ha tre fogli:

#### Foglio 1: "Iscrizioni"

Un partecipante per riga. Colonne:

| Colonna | Fonte |
|---|---|
| Codice | `event_participant_code` |
| Nome | `participants.first_name` |
| Cognome | `participants.last_name` |
| Email | `participants.email` |
| Ruolo | `event_participants.role` |
| Lingua | `event_participants.language` |
| Totale | `total_amount` |
| Acconto | `deposit_amount` |
| Saldo | `balance_amount` |
| Stato pagamento | `payment_status` |
| Data iscrizione | `created_at` |

#### Foglio 2: "Attività"

Una riga per ogni coppia partecipante/attività prenotata. Colonne:

| Colonna | Fonte |
|---|---|
| Codice partecipante | `event_participant_code` |
| Nome | `participants.first_name` |
| Cognome | `participants.last_name` |
| Codice attività | `event_activities.code` |
| Tipo | `event_activities.activity_type` |
| Titolo | `event_activities.title_it` |
| Sala | `event_activities.room_name` |
| Data/Ora | `event_activities.start_datetime` |
| Maestri | `event_activities.teacher_pair_label` |
| Sorgente | `source_type` (pacchetto / singola) |
| Prezzo | `final_amount` |

#### Foglio 3: "Riepilogo"

Statistiche aggregate:

| Dato | Formula |
|---|---|
| Totale iscritti | COUNT(*) |
| In attesa | COUNT WHERE payment_status = "pending" |
| Acconto versato | COUNT WHERE payment_status = "deposit" |
| Saldati | COUNT WHERE payment_status = "paid" |
| Totale incassato | SUM(deposit_received + paid_received) |
| Totale atteso | SUM(total_amount) |

### Response

```
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="{slug}-iscrizioni.xlsx"
```

---

## 12. POST /api/registrations — flusso legacy

**File**: `src/app/api/registrations/route.ts`

> **Stato**: Legacy. Funzionante ma da non estendere. Da deprecare e unificare con `/api/event-participants`.

Questo endpoint è stato il primo flusso implementato e usa il modello dati `registrations` + `registration_items` invece di `event_participants`. Differenze principali:

- Codice partecipante: `ABR-XXXXXX` invece di `EVP-XXXXXX`
- QR payload: `ABRAZO:REG:ABR-XXXXXX`
- Nessun supporto multilingua
- Nessuna gestione coppie di maestri
- Nessuna email di conferma
- Modello dati separato (`registrations`, `registration_items`)

---

## 13. Flussi futuri previsti

### Flusso: modifica iscrizione post-registrazione

```
Staff admin:
1. Apre scheda partecipante
2. Seleziona "Modifica iscrizione"
3. Aggiunge/rimuove attività
4. Ricalcolo automatico importi
5. Email notifica al partecipante
6. Audit: "registration_updated"
```

### Flusso: cancellazione iscrizione

```
Staff admin:
1. Apre scheda partecipante
2. Seleziona "Annulla iscrizione"
3. Conferma motivazione
4. UPDATE registration_status = "cancelled"
5. Email notifica al partecipante
6. Audit: "registration_cancelled"
```

### Flusso: comunicazione batch

```
Staff admin → /admin/events/[id]/communications:
1. Seleziona template (promemoria acconto, aggiornamento orari, ecc.)
2. Filtra destinatari (tutti / solo pending / solo confirmed)
3. Anteprima email
4. Conferma invio
5. Job di invio via Resend batch API
6. Report: inviati / errori
```

### Flusso: iscrizione multi-evento

```
Partecipante su /events:
1. Vede lista eventi pubblici
2. Seleziona un evento
3. Viene reindirizzato a /register/[slug]
4. Flusso iscrizione parametrico (stesso per tutti gli eventi)
```

### Flusso: cancellazione dati GDPR (Art. 17)

```
Staff admin (su richiesta partecipante):
1. Apre scheda partecipante
2. Seleziona "Cancella dati personali"
3. Conferma con password admin
4. UPDATE participants:
   first_name = "[ANONIMIZZATO]",
   last_name = "[ANONIMIZZATO]",
   email = "anonimizzato-{id}@deleted.invalid"
5. Mantiene: event_participant_audit, checkins, dati aggregati
6. Mantiene: privacy_accepted_at, terms_accepted_at (prova del trattamento)
7. Audit: "gdpr_data_erasure"
```
