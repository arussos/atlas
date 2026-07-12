# 01 — Architettura di ABRAZO

**Versione**: 1.0.0 | **Progetto**: ABRAZO MVP 0.9.0 | **Aggiornato**: Giugno 2026

---

## Indice

1. [Visione architetturale](#1-visione-architetturale)
2. [Stack tecnologico](#2-stack-tecnologico)
3. [Struttura Next.js e organizzazione cartelle](#3-struttura-nextjs-e-organizzazione-cartelle)
4. [Separazione pubblico / admin / API](#4-separazione-pubblico--admin--api)
5. [Supabase — database e storage](#5-supabase--database-e-storage)
6. [Resend — email service](#6-resend--email-service)
7. [QR Code system](#7-qr-code-system)
8. [Principio multi-evento](#8-principio-multi-evento)
9. [Mobile-first](#9-mobile-first)
10. [Motivazioni delle scelte tecniche](#10-motivazioni-delle-scelte-tecniche)
11. [Vincoli e debiti tecnici noti](#11-vincoli-e-debiti-tecnici-noti)

---

## 1. Visione architetturale

ABRAZO è progettato come un'applicazione web **full-stack** costruita su Next.js App Router, con Supabase come backend unificato (database, storage, auth futura). L'architettura privilegia la **semplicità operativa** e la **velocità di sviluppo** rispetto alla scalabilità orizzontale: siamo in contesto di associazione sportiva no-profit, non di SaaS multi-tenant ad alto traffico.

### Principi guida

| Principio | Applicazione pratica |
|---|---|
| **Server-first** | Ogni dato è caricato lato server per default. Il client riceve HTML pronto. |
| **Interattività minima** | I Client Components esistono solo dove l'interattività è strettamente necessaria (form, scanner QR). |
| **Business logic server-side** | Nessuna logica critica nel browser. Tutta la mutazione di dati passa per API Routes. |
| **Audit everywhere** | Ogni operazione significativa produce un record tracciabile. |
| **Incrementalità** | Nessuna infrastruttura generica costruita in anticipo. Si generalizza quando il secondo caso d'uso appare. |

---

## 2. Stack tecnologico

### Core

| Tecnologia | Versione | Ruolo |
|---|---|---|
| **Next.js** | 16.2.x | Framework full-stack (App Router, SSR, API Routes, Server Actions) |
| **React** | 19.x | UI runtime (Server + Client Components) |
| **TypeScript** | 5.x | Type safety, manutenibilità a lungo termine |
| **Tailwind CSS** | 4.x | Styling utility-first, nessuna libreria UI esterna |

### Backend & servizi

| Tecnologia | Versione | Ruolo |
|---|---|---|
| **Supabase** | SDK 2.x | Database PostgreSQL, Storage S3, Auth (futura), Realtime (futuro) |
| **Resend** | 6.x | Invio email transazionale |
| **Vercel** | — | Deploy e hosting Next.js |

### Librerie funzionali

| Libreria | Versione | Ruolo |
|---|---|---|
| `qrcode` | 1.5.x | Generazione PNG QR code lato server |
| `html5-qrcode` | 2.3.x | Scanner QR via camera nel browser |
| `exceljs` | 4.4.x | Generazione file `.xlsx` multi-foglio lato server |

### Font

| Font | Tipo | Uso |
|---|---|---|
| Cormorant Garamond | Serif display | Titoli, identità visiva elegante |
| Geist Sans | Sans-serif | Corpo testo, interfacce |
| Geist Mono | Monospace | Codici, dati tecnici |

### Variabili d'ambiente

```bash
# Esposte al browser (sicure: solo lettura pubblica)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Solo server-side (mai esposte al browser)
SUPABASE_SERVICE_ROLE_KEY=
RESEND_API_KEY=
```

---

## 3. Struttura Next.js e organizzazione cartelle

ABRAZO usa il **Next.js App Router** (introdotto in Next.js 13, stabile da 14+). Ogni cartella in `src/app/` è una route. I file speciali sono `page.tsx` (pagina), `layout.tsx` (wrapper), `route.ts` (API).

```
abrazo-prototype/
├── src/
│   ├── app/                            # Next.js App Router
│   │   ├── layout.tsx                  # Root layout: font, metadata globali
│   │   ├── page.tsx                    # Home page pubblica (marketing + roadmap)
│   │   │
│   │   ├── admin/                      # Area operativa staff (futura auth)
│   │   │   ├── page.tsx                # Dashboard: statistiche evento attivo
│   │   │   └── events/
│   │   │       ├── page.tsx            # Catalogo eventi
│   │   │       └── [id]/               # Hub di un evento specifico
│   │   │           ├── page.tsx        # Dashboard evento
│   │   │           ├── participants/
│   │   │           │   ├── page.tsx    # Lista partecipanti + stati pagamento
│   │   │           │   └── [participantId]/page.tsx  # Scheda completa partecipante
│   │   │           ├── checkin/
│   │   │           │   ├── page.tsx
│   │   │           │   └── CheckinClient.tsx  # Scanner QR evento (Client Component)
│   │   │           ├── activities/
│   │   │           │   ├── page.tsx            # Attività con Iscritti/Presenti/Assenti
│   │   │           │   └── [activityId]/
│   │   │           │       ├── page.tsx
│   │   │           │       └── ActivityCheckinClient.tsx  # Scanner QR per attività
│   │   │           ├── payments/page.tsx        # Aggiornamento stati pagamento
│   │   │           ├── search/page.tsx          # Ricerca partecipanti
│   │   │           └── communications/page.tsx  # Preview template email
│   │   │
│   │   ├── register/                   # Area pubblica iscrizioni
│   │   │   ├── [eventId]/              # Flusso generico (legacy, da unificare)
│   │   │   │   ├── page.tsx
│   │   │   │   └── RegisterForm.tsx    # Form base (Client Component)
│   │   │   └── epico-tango-fest-2027/  # Flusso avanzato Epico (principale)
│   │   │       ├── page.tsx            # Server loader: fetch event + packages + activities
│   │   │       ├── RegisterClient.tsx  # Form bilingue con pacchetti e attività
│   │   │       └── success/[id]/
│   │   │           └── page.tsx        # Conferma: QR, finanziario, istruzioni
│   │   │
│   │   ├── api/                        # API Routes (business logic di mutazione)
│   │   │   ├── registrations/route.ts          # POST legacy
│   │   │   ├── event-participants/route.ts      # POST principale (Epico)
│   │   │   ├── checkin/
│   │   │   │   ├── event/route.ts              # POST check-in evento
│   │   │   │   └── activity/route.ts           # POST check-in attività
│   │   │   └── events/[id]/
│   │   │       └── export-xlsx/route.ts        # GET export Excel
│   │   │
│   │   └── test/
│   │       └── qr/page.tsx                     # Test QR (sviluppo)
│   │
│   ├── components/
│   │   └── AbrazoLogo.tsx              # Logo SVG riutilizzabile
│   │
│   └── lib/
│       ├── supabase.ts                 # Client Supabase (anon key, browser-safe)
│       ├── supabaseAdmin.ts            # Client Supabase (service role, server-only)
│       ├── emailService.ts             # Layer astratto invio email via Resend
│       ├── emailTemplates.ts           # Template HTML+testo bilingue IT/EN
│       └── qr.ts                       # Generazione buffer PNG QR code
│
├── public/
│   └── brand/
│       └── abrazo-logo.svg
│
├── docs/                               # Documentazione ufficiale del progetto
├── CLAUDE.md                           # Memoria operativa per Claude
├── AGENTS.md                           # Regole Next.js per agenti AI
└── package.json
```

### Convenzione: Server vs Client Components

```
page.tsx senza "use client"       → Server Component (default)
                                    Esegue sul server. Può fare fetch async.
                                    Non ha useState, useEffect, event handlers.

CheckinClient.tsx con "use client" → Client Component
                                    Esegue nel browser. Ha stato e interattività.
                                    Riceve dati come props dal Server Component padre.
```

---

## 4. Separazione pubblico / admin / API

### Area pubblica (`/register/`, `/`)

- Accessibile senza autenticazione
- Progettata per partecipanti da smartphone
- Server Components per il caricamento dati (SEO, performance)
- Client Components solo per il form interattivo (`RegisterClient.tsx`)
- Usa il client Supabase con anon key per le query di lettura

### Area admin (`/admin/`)

- Destinata allo staff e alla direzione Art&Tango
- **Attualmente priva di autenticazione** (debito tecnico critico)
- Tutte le pagine sono Server Components che usano `supabaseAdmin` (service role)
- I Client Components sono solo per l'interattività (scanner, bottoni azione)
- Le mutazioni di stato usano Server Actions (Next.js) per aggiornamenti semplici

### API Routes (`/api/`)

- Contengono tutta la business logic di mutazione
- Ogni route valida l'input, esegue operazioni su DB, genera artefatti (QR, email)
- Usano esclusivamente `supabaseAdmin` (service role key)
- Restituiscono `Response` con status HTTP appropriati
- Nessuna logica di presentazione: solo dati JSON

### Regola fondamentale

```
supabase.ts (anon)        → solo in Client Components, letture pubbliche
supabaseAdmin.ts (service role) → solo in API Routes e Server Components
```

---

## 5. Supabase — database e storage

Supabase è il backend unificato di ABRAZO: fornisce PostgreSQL, storage S3-compatible, SDK TypeScript, e (in futuro) Auth e Realtime.

### Due client con privilegi distinti

**`src/lib/supabase.ts`** — client pubblico:
- Chiave: `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Soggetto a Row Level Security (RLS)
- Usabile nel browser (bundle client)
- Uso: query pubbliche nel form di iscrizione

**`src/lib/supabaseAdmin.ts`** — client admin:
- Chiave: `SUPABASE_SERVICE_ROLE_KEY`
- Bypass della Row Level Security
- Esclusivamente server-side (API Routes, Server Components)
- Uso: tutto ciò che richiede visibilità completa (dashboard, check-in, export)

### Storage

- **Bucket**: `registration-qr`
- **Path**: `events/{event_id}/event-participants/{participant_id}.png`
- **Formato file**: PNG 512×512 px
- **Accesso**: URL pubblico (da valutare migrazione a signed URL con scadenza)

### Realtime (futuro)

Supabase offre WebSocket-based realtime subscriptions. L'architettura è pronta per aggiungere una dashboard presenze live (check-in in tempo reale su schermo condiviso in sala) senza cambiamenti strutturali.

---

## 6. Resend — email service

### Layer astratto

L'invio email è isolato in `src/lib/emailService.ts`. Questo è un **layer astratto intenzionale**: l'applicazione non chiama Resend direttamente dal codice di business, ma sempre tramite questa funzione:

```typescript
sendRegistrationConfirmationEmail({ to, subject, html, text })
  → Promise<{ ok: boolean, data?, error? }>
```

L'astrazione consente di sostituire Resend con un altro provider (SMTP, Amazon SES, SendGrid, Mailgun) modificando un solo file, senza toccare le API Routes o i template.

### Template bilingue

`src/lib/emailTemplates.ts` contiene la funzione `buildRegistrationConfirmationEmail()` che:
- Accetta un oggetto `RegistrationEmailData` con tutti i dati necessari
- Produce `{ subject, text, html }` in italiano o inglese in base al campo `language`
- Il template HTML è dark-themed, branded ABRAZO, con formattazione valuta `it-IT`

### Sender attuale (sviluppo)

`from: "ABRAZO <onboarding@resend.dev>"`

Da sostituire con dominio verificato prima del deploy in produzione.

---

## 7. QR Code system

### Architettura end-to-end

```
Generazione     →     Storage          →     Display          →     Scanning
(server-side)         (Supabase)              (browser)              (browser)

qr.ts                 registration-qr         success/[id]/          CheckinClient.tsx
qrcode library        bucket                  page.tsx               html5-qrcode
PNG Buffer            PNG file                <Image> component      camera posteriore
```

### Formato del payload

```
ABRAZO:EVP:EVP-XXXXXX
  │       │    │
  │       │    └── Codice univoco (6 char alfanumerici)
  │       └─────── Tipo record (EVP = Event Participant)
  └─────────────── Namespace applicazione
```

Il formato è:
- **Opaco**: nessun dato personale leggibile
- **Semantico**: il prefisso identifica il tipo di record
- **Scalabile**: si possono aggiungere tipi futuri (`ABRAZO:VOL:`, `ABRAZO:STAFF:`)
- **Indipendente dall'UUID database**: il codice è un riferimento human-readable

### Generazione

```typescript
// src/lib/qr.ts
generateQrPngBuffer(payload: string): Promise<Buffer>
// PNG 512×512, margine 2, error correction "M", sfondo bianco
```

### Risoluzione

La risoluzione del QR (payload → dati partecipante) avviene solo server-side, tramite lookup nella tabella `event_participants` per il campo `qr_payload`. Non è possibile ottenere dati personali scansionando il QR senza accesso autenticato al sistema.

### QR come identità operativa, non prova di pagamento

Questa è una decisione architetturale esplicita (vedi `DL-11` nel Decision Log).

Il QR code identifica il partecipante; **non certifica che abbia pagato**. Le conseguenze pratiche:

| Comportamento | Motivazione |
|---|---|
| Il QR è generato all'iscrizione, non al pagamento | Il partecipante ha un codice stabile dal primo giorno |
| Il QR è inviato nella prima email, non nella seconda | La seconda email (pagamento completo) ricorda di usare quello già ricevuto |
| Il QR è valido anche con acconto parziale | La verifica del pagamento è responsabilità dello staff al check-in |
| Il check-in restituisce sempre `payment_status` | Lo staff decide in autonomia come gestire i casi di pagamento incompleto |

**Pattern operativo al check-in**:
1. Staff scansiona il QR → sistema conferma il partecipante con stato pagamento
2. Se `payment_status = "paid"` → ingresso normale
3. Se `payment_status = "deposit"` o `"pending"` → staff indirizza alla Segreteria/cassa prima dell'ingresso

Questo approccio mantiene la semplicità del QR (uno per partecipante, per sempre) senza sacrificare il controllo operativo del pagamento.

---

## 8. Principio multi-evento

ABRAZO non è costruito per Epico Tango Fest. È costruito per **tutti gli eventi di Art&Tango**.

### Come l'architettura lo supporta

- Tutte le tabelle principali hanno `event_id` come foreign key
- Le route admin sono parametriche: `/admin/events/[id]/...`
- I moduli di libreria (`emailService`, `qr`, `emailTemplates`) sono event-agnostic
- Lo schema DB supporta già eventi multipli senza modifiche strutturali

### Cosa rimane da generalizzare

- La route `/register/epico-tango-fest-2027/` è specifica per Epico (hardcoded slug)
- Alcune query in componenti admin referenziano l'event ID di Epico direttamente
- Il flusso generico (`/register/[eventId]/`) esiste ma usa un modello dati legacy

### Evoluzione prevista

Il percorso verso la generalizzazione completa è:
1. Migrare il flusso Epico al modello slug-based (`/register/[slug]/`)
2. Rendere il form di iscrizione completamente parametrico (configurazione da DB)
3. Aggiungere un pannello admin per creare/modificare eventi, pacchetti, attività
4. Deprecare il flusso legacy `/api/registrations`

---

## 9. Mobile-first

### Motivazione operativa

- I partecipanti si iscrivono prevalentemente da smartphone
- Lo staff fa check-in con smartphone in mano in sala
- La dashboard admin è consultata anche in mobilità

### Implementazione

- Breakpoint Tailwind: la maggior parte dei layout è a colonna singola su mobile, poi espanso con `md:` e `lg:`
- Scanner QR (`html5-qrcode`): configurato per usare la camera posteriore (`facingMode: "environment"`)
- Il form di iscrizione (`RegisterClient.tsx`) è ottimizzato per input touch
- Le card nella dashboard admin hanno spaziatura generosa per target touch

### Regola di sviluppo

Ogni nuovo componente UI deve essere verificato su viewport ≤390px prima di essere considerato completato.

---

## 10. Motivazioni delle scelte tecniche

### Perché Next.js App Router e non un SPA separato?

Un'architettura con React SPA + API REST separata avrebbe richiesto due progetti, due deploy, gestione CORS, token auth più complessa. App Router unifica tutto in un progetto con deploy Vercel zero-config e consente il mix Server/Client Components, eliminando fetch ridondanti.

### Perché Tailwind e nessuna libreria UI?

Librerie come shadcn/ui, MUI o Chakra semplificano i componenti comuni ma introducono dipendenze che vincolano le scelte stilistiche. Il design di ABRAZO ha un'identità visiva specifica (palette dark, tipografia serif elegante, colori oro e rosso) che sarebbe più difficile da mantenere sopra strati CSS di terze parti. Tailwind puro offre controllo totale con zero overhead.

### Perché Supabase e non un DB standalone?

Supabase fornisce database, storage, auth e realtime in un unico servizio con SDK TypeScript di prima qualità. Per un'associazione no-profit con risorse limitate, evitare di gestire infrastruttura separata è un vantaggio operativo significativo. Il piano gratuito è sufficiente per il volume attuale.

### Perché Resend e non SMTP diretto?

Resend garantisce deliverability, tracking di aperture, gestione bounce e un'API moderna. Lo SMTP self-hosted richiede configurazione SPF/DKIM/DMARC e gestione reputazione IP. Per MVP, Resend è la scelta pragmatica. Il layer astratto in `emailService.ts` consente la sostituzione futura.

### Perché ExcelJS per l'export?

L'export dati deve essere immediatamente utilizzabile dallo staff senza elaborazione. ExcelJS genera xlsx con più fogli, headers in grassetto, colonne auto-sized: il risultato è un documento professionale, non un CSV grezzo. L'alternativa (CSV) avrebbe richiesto comunque elaborazione manuale da parte dello staff.

---

## 11. Vincoli e debiti tecnici noti

| ID | Debito | Impatto | Priorità |
|---|---|---|---|
| DT-01 | Nessuna autenticazione area admin | Critico per produzione | Alta |
| DT-02 | Event ID Epico hardcoded in alcuni componenti | Blocca generalizzazione multi-evento | Alta |
| DT-03 | Prezzi non ricalcolati server-side (accettati dal client) | Vulnerabilità sicurezza economica | Alta |
| DT-04 | Due flussi iscrizione divergenti (`registrations` vs `event_participants`) | Duplicazione codice e logica | Media |
| DT-05 | Operator identity fittizia (`"staff-demo"`) nei check-in | Audit trail incompleto | Media |
| DT-06 | Email sender non produzione (`onboarding@resend.dev`) | Deliverability / credibilità | Media |
| DT-07 | QR PNG su storage con URL pubblico permanente | Rischio privacy GDPR | Media |
| DT-08 | `teacher_pair_label` come campo testo flat | Normalizzazione incompleta (vedi `02_DATABASE.md`) | Bassa |

Per dettagli sui debiti relativi al database vedere [02_DATABASE.md](02_DATABASE.md).
Per dettagli su sicurezza e GDPR vedere [04_GDPR_AND_SECURITY.md](04_GDPR_AND_SECURITY.md).
Per la roadmap di risoluzione vedere [05_ROADMAP.md](05_ROADMAP.md).
