# ABRAZO — Security Foundation · Piano di Implementazione

# Status

Versione: 1.1
Proprietario: Progetto ABRAZO
Stato: ✅ COMPLETATA — Security Foundation MVP 0.9.8
Ultima revisione: 28 giugno 2026
Prossima revisione: Release Candidate 1.0 (MS-RLS-B e AdminHeader)

---

## Indice

1. [Scopo](#1-scopo)
2. [Decisioni approvate](#2-decisioni-approvate)
3. [Architettura](#3-architettura)
4. [Piano di implementazione](#4-piano-di-implementazione)
5. [SQL](#5-sql)
6. [Gestione dei rischi](#6-gestione-dei-rischi)
7. [Rollback](#7-rollback)
8. [Decision Log collegati](#8-decision-log-collegati)
9. [Checklist di uscita](#9-checklist-di-uscita)

---

## 1. Scopo

Questo documento è il piano operativo ufficiale della Security Foundation di ABRAZO (MVP 0.9.6).

Raccoglie le decisioni architetturali già approvate durante la Design Review e le traduce in un piano di implementazione milestone per milestone. Deve essere consultato attivamente durante lo sviluppo, non solo come riferimento storico.

**Non descrive le motivazioni delle scelte** — quelle sono documentate nella Design Review di MVP 0.9.6. Descrive cosa fare, in quale ordine, e come verificare che sia fatto correttamente.

**Prerequisito per la produzione**: l'assenza di autenticazione è l'unico blocco al deploy in produzione con dati reali. Questa milestone lo risolve.

---

## 2. Decisioni approvate

Tutte le seguenti decisioni sono consolidate. Non richiedono ulteriore validazione.

| Decisione | Valore approvato |
|---|---|
| Provider auth | Supabase Auth (nativo, nessun provider esterno) |
| Pacchetto SSR | `@supabase/ssr` v0.4.0+ |
| Cookie API | `getAll` / `setAll` (non la vecchia `get`/`set`/`remove`) |
| Metodo di verifica sessione server-side | `getClaims()` — validazione JWT locale |
| Metodo per caricare profilo utente | `getUser()` — chiamata di rete |
| Metodo **vietato** server-side | `getSession()` — legge cookie senza rivalidazione |
| Tabella staff | `staff` (non `admin_users`) |
| Ruoli | 4 ruoli: `super_admin`, `segreteria`, `direzione`, `checkin` |
| Ruolo eliminato | `amministratore` (non necessario in MVP) |
| Defense in Depth | Le Server Actions verificano l'autenticazione indipendentemente dal proxy |
| Accesso metodo auth | Email + password (no OAuth, no magic link, no 2FA in questa milestone) |
| Session duration | Defaults Supabase: access token 1h, refresh token indefinito |
| Inactivity timeout | Non implementato (richiede Pro Plan — rinviato) |
| API Routes | Rimangono non protette in MVP 0.9.6 (gap documentato, roadmap 0.9.7) |

---

## 3. Architettura

### 3.1 Visione generale

```
Browser                  Next.js                    Supabase
───────────────────────────────────────────────────────────
GET /admin/*    →   src/proxy.ts  [Next.js 16: proxy, non middleware]
                    getClaims()   →   JWT locale
                    ✓ valid       →   passa alla pagina
                    ✗ missing     →   redirect /login?from=<path>

POST /login     →   LoginForm.tsx (Client)
                    supabase.auth.signInWithPassword()   →   Supabase Auth
                    ✓ ok          →   cookie session + redirect /admin
                    ✗ fail        →   errore visibile

Server Action   →   requireRole("segreteria")
(confirmDeposit)    getUser()     →   Supabase Auth (rete)
                    staff lookup  →   supabaseAdmin
                    ✓ ok          →   esegue azione
                    ✗ fail        →   redirect /login
```

### 3.2 Autenticazione

**Flusso di login**:
1. L'operatore inserisce email e password in `LoginForm.tsx`
2. Il client chiama `supabase.auth.signInWithPassword()` usando il client anon (`supabase.ts`)
3. Supabase Auth valida le credenziali e restituisce una sessione
4. `@supabase/ssr` scrive i cookie di sessione nella risposta tramite `setAll`
5. Il browser viene reindirizzato al percorso originale (parametro `?from=`)

**Flusso di verifica (proxy)**:
1. Ad ogni request su `/admin/*`, il proxy (`src/proxy.ts`) crea un client SSR con `createServerClient`
2. Chiama `getClaims()` — validazione JWT locale, nessuna chiamata di rete
3. Se `claims` è null → redirect a `/login?from=<pathname>`
4. Se `claims` è presente → la request prosegue; i cookie di refresh vengono aggiornati se necessario

> **Nota tecnica**: In Next.js 16, `middleware.ts` è stato rinominato `proxy.ts` e la funzione esportata da `middleware` a `proxy`. Il runtime è Node.js per default (non più Edge). Vedere la guida ufficiale: `node_modules/next/dist/docs/01-app/02-guides/upgrading/version-16.md`.

**Flusso di verifica (Server Actions)**:
1. La Server Action chiama `requireAuth()` o `requireRole('segreteria')`
2. Internamente viene chiamato `getUser()` — chiamata di rete, verifica fresca
3. Il profilo viene caricato da `supabaseAdmin.from('staff').select(*)` con filtro `is_active = true`
4. Se non autenticato o ruolo insufficiente → `redirect('/login')`

### 3.3 Autorizzazione — Ruoli

```
super_admin  ──────────────────────────────  tutto
segreteria   ──────────────────────  pagamenti, partecipanti, comunicazioni
direzione    ──────────────────────  lettura: statistiche, schede, export
checkin      ─────────────  solo scanner QR evento e attività
```

Tutti i ruoli sono registrati nella tabella `staff`. La colonna `role` ha un `CHECK` constraint che accetta solo i quattro valori validi.

`super_admin` bypassa qualsiasi controllo di ruolo. Gli altri tre ruoli sono paralleli — non gerarchici — e vengono verificati per corrispondenza esatta nelle Server Actions.

### 3.4 Sessioni

| Parametro | Valore | Note |
|---|---|---|
| Access token | 1 ora | Default Supabase, trasparente per l'utente |
| Refresh token | Single-use, non scade | Il middleware aggiorna automaticamente |
| Logout | `supabase.auth.signOut()` | Cancella i cookie |
| Dispositivi condivisi | Logout manuale obbligatorio | Da documentare nel manuale staff |

### 3.5 Nuovi file da creare

| File | Tipo | Scopo |
|---|---|---|
| `src/lib/supabaseServer.ts` | Libreria | Client Supabase SSR con `getAll`/`setAll` |
| `src/lib/supabaseBrowser.ts` | Libreria | Client Supabase browser con cookie (non localStorage) |
| `src/lib/auth.ts` | Libreria | `getCurrentStaff`, `requireAuth`, `requireRole` |
| `src/proxy.ts` | Proxy Next.js 16 | Protezione route `/admin/*` (ex-`middleware.ts`) |
| `src/app/login/page.tsx` | Server Component | Container pagina login |
| `src/app/login/LoginForm.tsx` | Client Component | Form email + password |
| `src/app/login/actions.ts` | Server Actions | `logout()` |

### 3.6 File esistenti da modificare

| File | Modifica |
|---|---|
| `src/app/admin/events/[id]/segreteria/actions.ts` | Aggiungere `requireRole('segreteria')` a `confirmDeposit` e `confirmPayment` |
| `src/app/admin/events/[id]/participants/[participantId]/actions.ts` | Aggiungere `requireAuth()` a `addStaffNote` |
| `src/app/admin/page.tsx` | Aggiungere bottone logout |

---

## 4. Piano di implementazione

### MS-A — Prerequisiti Supabase ✓ COMPLETATA

**Obiettivo**: infrastruttura DB e primo utente pronti. Nessun file di codice modificato.

**Dove**: solo Supabase Dashboard.

**Operazioni**:
1. Eseguire lo script SQL della sezione 5.1 nel SQL Editor di Supabase
2. Andare in Authentication → Users → Add User
3. Inserire email e password del primo `super_admin`
4. Copiare l'UUID generato
5. Eseguire lo script SQL della sezione 5.2 con l'UUID corretto

**Prerequisiti**: accesso al Dashboard Supabase del progetto.

**Build**: non applicabile (nessun codice modificato).

**Test**:
- La tabella `staff` esiste con la struttura corretta
- Il record `super_admin` è visibile in `staff` con `is_active = true`
- Il corrispondente utente esiste in Authentication → Users

**Commit previsto**: nessuno (solo operazioni Dashboard).

**Criterio di completamento**: `SELECT * FROM staff;` restituisce almeno un record.

**Stato**: completata il 28 giugno 2026.

---

### MS-B — Foundation SSR ✓ COMPLETATA

**Obiettivo**: il layer Supabase SSR e le funzioni di autenticazione esistono e compilano. Zero comportamento visibile per l'utente.

**File coinvolti** (tutti nuovi):
- `src/lib/supabaseServer.ts`
- `src/lib/auth.ts`

**Prerequisiti**: MS-A completata; `@supabase/ssr` installato (`npm install @supabase/ssr`).

**Struttura `supabaseServer.ts`**:
```typescript
// Crea un client Supabase SSR con getAll/setAll
// Usato da middleware e Server Components per leggere/rinnovare la sessione
// NON usare getSession() — usare getClaims() per verifica, getUser() per profilo
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createSupabaseServerClient() {
  const cookieStore = await cookies()
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

**Struttura `auth.ts`**:
```typescript
// Funzioni di autenticazione per Server Components e Server Actions
// getAdminUser: carica utente + profilo staff
// requireAuth: redirect a /login se non autenticato
// requireRole: redirect a /admin se ruolo insufficiente
```

Funzioni da esportare:
- `getAdminUser(): Promise<{ user, staff } | null>`
- `requireAuth(): Promise<{ user, staff }>` — redirect se non autenticato
- `requireRole(role: StaffRole): Promise<{ user, staff }>` — redirect se ruolo insufficiente

**Build**: `npm run build` deve passare senza errori.

**Test**: nessun comportamento visibile; verificare che la build non abbia errori TypeScript.

**Commit previsto**: `feat(auth): aggiunge foundation SSR Supabase e layer auth (inert)`

**Criterio di completamento**: build pulita; i due file esistono e non hanno errori TypeScript.

**Stato**: completata il 28 giugno 2026. Versione `@supabase/ssr` installata: 0.12.0.

---

### MS-C — Proxy ✓ COMPLETATA

**Obiettivo**: `/admin/*` richiede sessione valida. Area pubblica e API invariate.

> **Nota Next.js 16**: In questa versione il file non si chiama `middleware.ts` ma `src/proxy.ts`, e la funzione esportata è `proxy` (non `middleware`). Il runtime è Node.js per default. Il rollback si ottiene eliminando `src/proxy.ts`.

**File coinvolti** (nuovo):
- `src/proxy.ts`

**Struttura**:
```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function proxy(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // CRITICO: getClaims(), non getSession()
  const { data } = await supabase.auth.getClaims()
  const isAuthenticated = !!data?.claims?.sub

  if (!isAuthenticated && request.nextUrl.pathname.startsWith('/admin')) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('from', request.nextUrl.pathname)
    return NextResponse.redirect(loginUrl)
  }

  return supabaseResponse
}

export const config = {
  matcher: ['/admin', '/admin/:path*'],
}
```

**Prerequisiti**: MS-B completata.

**Build**: `npm run build` deve passare.

**Test manuali**:
- Aprire `/admin` senza sessione attiva → redirect a `/login?from=/admin`
- Aprire `/register/epico-tango-fest-2027` → funziona normalmente (non protetta)
- Aprire `/` → funziona normalmente

**Commit previsto**: `feat(auth): proxy protegge /admin/* con redirect a /login`

**Criterio di completamento**: unauthenticated → redirect; area pubblica invariata.

**Stato**: completata il 28 giugno 2026.

---

### MS-D — Login page ✓ COMPLETATA

**Obiettivo**: lo staff può autenticarsi con email e password.

**File coinvolti** (tutti nuovi):
- `src/app/login/page.tsx` — Server Component, legge `?from=` dai searchParams
- `src/app/login/LoginForm.tsx` — Client Component con `"use client"`

**Comportamento `page.tsx`**:
- Legge il parametro `from` dai searchParams
- Se l'utente è già autenticato (verifica con `getClaims`), redirect a `/admin`
- Altrimenti renderizza `<LoginForm from={from} />`

**Comportamento `LoginForm.tsx`**:
- Campi: email, password
- Submit: chiama `supabase.auth.signInWithPassword()` via client anon (`supabase.ts`)
- Successo: `router.push(from ?? '/admin')`
- Errore credenziali: messaggio visibile ("Email o password non corretti")
- Errore rete: messaggio visibile ("Errore di connessione")
- Stile: dark theme ABRAZO, ABRAZO logo, accent oro

**Prerequisiti**: MS-C completata; utente super_admin creato in MS-A.

**Build**: `npm run build`.

**Test manuali**:
- Login con credenziali errate → errore visibile, nessun redirect
- Login con credenziali corrette → redirect a `/admin`
- Accesso a `/admin` dopo login → pagina visibile senza redirect
- Accesso diretto a `/login` con sessione attiva → redirect a `/admin`
- Accesso a `/admin/events` senza sessione → redirect a `/login?from=/admin/events`; dopo login → redirect a `/admin/events`

**Commit previsto**: `feat(auth): pagina di login con email e password`

**Criterio di completamento**: login funzionante end-to-end; redirect `from` corretto.

> **Nota implementativa**: il piano originale indicava `supabase.ts` (localStorage) per il login. Sostituito con `createBrowserClient` da `@supabase/ssr` via `src/lib/supabaseBrowser.ts` — necessario perché il proxy legge cookie, non localStorage.

**Stato**: completata il 28 giugno 2026.

---

### MS-E — Logout ✓ COMPLETATA

**Obiettivo**: lo staff può disconnettersi. La sessione viene invalidata.

**File coinvolti**:
- `src/app/login/actions.ts` (nuovo) — Server Action `logout()`
- `src/app/admin/page.tsx` (modifica) — aggiunge bottone logout

**Struttura `actions.ts`**:
```typescript
"use server"
import { createSupabaseServerClient } from '@/lib/supabaseServer'
import { redirect } from 'next/navigation'

export async function logout() {
  const supabase = await createSupabaseServerClient()
  await supabase.auth.signOut()
  redirect('/login')
}
```

**Bottone logout** in `src/app/admin/page.tsx`: form con action `logout`, posizionato in modo visibile nella dashboard principale.

**Prerequisiti**: MS-D completata.

**Build**: `npm run build`.

**Test manuali**:
- Login → click logout → redirect a `/login`
- Dopo logout, aprire `/admin` → redirect a `/login`
- Aprire due tab: logout in una → l'altra su refresh mostra `/login`

**Commit previsto**: `feat(auth): logout staff con redirect a login`

**Criterio di completamento**: logout cancella la sessione; `/admin` inaccessibile dopo.

**Stato**: completata il 28 giugno 2026.

---

### MS-F — Server Actions auth guard ✓ COMPLETATA

**Obiettivo**: le operazioni di mutazione non sono eseguibili senza autenticazione, indipendentemente dal middleware.

**File coinvolti** (solo modifiche):
- `src/app/admin/events/[id]/segreteria/actions.ts`
- `src/app/admin/events/[id]/participants/[participantId]/actions.ts`

**Modifiche**:

```typescript
// segreteria/actions.ts
export async function confirmDeposit(formData: FormData) {
  await requireRole("segreteria")  // ← aggiungere come prima riga
  // ... resto invariato
}

export async function confirmPayment(formData: FormData) {
  await requireRole("segreteria")  // ← aggiungere come prima riga
  // ... resto invariato
}

// participants/.../actions.ts
export async function addStaffNote(formData: FormData) {
  await requireAuth()  // ← aggiungere come prima riga
  // ... resto invariato
}
```

**Prerequisiti**: MS-B completata (`auth.ts` con `requireAuth` e `requireRole` disponibili).

**Build**: `npm run build`.

**Test manuali**:
- Con sessione `segreteria` attiva: `confirmDeposit` e `confirmPayment` funzionano
- Con sessione `checkin` attiva: `confirmDeposit` → redirect a `/admin`
- Senza sessione: chiamata diretta all'endpoint della Server Action → redirect a `/login`

**Commit previsto**: `feat(auth): protezione Server Actions con requireRole e requireAuth`

**Criterio di completamento**: nessuna Server Action eseguibile senza autenticazione valida.

**Bonus implementativo**: `operator_name` nelle action `segreteria` ora riporta `admin.staff.email` reale (era assente in `confirmDeposit`/`confirmPayment`, era hardcoded `"segreteria"` in `addStaffNote`). L'audit trail è ora completo e attribuito all'operatore reale.

**Stato**: completata il 28 giugno 2026.

---

### MS-G — Documentazione e chiusura ✓ COMPLETATA

**Obiettivo**: l'architettura di sicurezza è documentata nei file ufficiali del progetto; logout raggiungibile dai hub di navigazione.

**Design Review (28 giugno 2026)**:
Analisi dei 12 file del backoffice ha rilevato che il bottone "Esci" era presente solo su `/admin`. Due opzioni valutate:
- Opzione A: `AdminHeader` condiviso + propagazione a tutte le 12 pagine (rinviato a RC 1.0)
- Opzione B (approvata): aggiungere logout ai due hub di navigazione (`/admin/events` e `/admin/events/[id]`); pagine operative profonde rinviate a RC 1.0

**File modificati**:
- `src/app/admin/events/page.tsx` — aggiunto logout
- `src/app/admin/events/[id]/page.tsx` — aggiunto logout
- `docs/05_ROADMAP.md` — §4 Autenticazione aggiornato; §4b RC 1.0 Backoffice layout aggiunto
- `docs/architecture/SECURITY_IMPLEMENTATION_PLAN.md` — stato aggiornato, MS-G chiusa

**Build**: `npm run build` — ✓ pulita.

**Gap residui documentati**:
- API Routes non protette (gap R5, R6) — roadmap 0.9.7
- `checked_in_by` fisso `"staff-demo"` nelle API check-in — dipende da auth API route
- Logout non presente nelle 8 pagine operative profonde — roadmap RC 1.0 AdminHeader
- RLS Supabase non attivata — roadmap 0.9.7

**Commit previsto**: `feat(auth): chiude Security Foundation MS-G — logout hub, documentazione, roadmap`

**Criterio di completamento**: build pulita; logout raggiungibile da tutti i hub di navigazione; gap residui documentati in roadmap.

**Stato**: completata il 28 giugno 2026.

---

### MS-H — Row Level Security (tabelle service-role) ✓ COMPLETATA

**Obiettivo**: enforcement RLS a livello database come terzo layer di difesa. Tabelle mai toccate da client anon: RLS attivata senza policy.

**Scope**: tutte le tabelle che contengono dati sensibili e sono accessibili esclusivamente tramite `supabaseAdmin` (service role, bypassa RLS).

**SQL eseguito nel Dashboard Supabase**:
```sql
ALTER TABLE public.event_participants           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participants                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_participant_audit      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.checkins                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_participant_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_activities             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.package_activities           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teacher_couples              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.registrations                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.registration_items           ENABLE ROW LEVEL SECURITY;
```

**Motivazione**: il service role bypassa RLS incondizionatamente — abilitare RLS senza policy equivale a bloccare l'accesso via client anon, senza impatto su nessuna funzionalità esistente.

**Stato**: completata il 28 giugno 2026.

---

### MS-RLS-B — Policy pubbliche su events, packages, event_sessions

**Stato**: ⏩ RIMANDATO A RC 1.0

**Motivazione**: MS-RLS-B non è una vulnerabilità attiva. Le tabelle `events`, `packages` ed `event_sessions` sono accessibili via client anon dal flusso pubblico di iscrizione, ma:
- I dati esposti (nome evento, nome pacchetto, sessioni) sono per loro natura pubblici — non dati personali
- Il proxy di Next.js protegge l'intera area `/admin/*`
- Le API sensibili (export, check-in) sono già protette con 401/403

L'aggiunta di RLS + policy selettive su queste tabelle è un **miglioramento architetturale di defense-in-depth**, non la chiusura di un gap di sicurezza. Viene inserito nel piano RC 1.0 insieme al fix `supabase → supabaseAdmin` in `admin/events/page.tsx` e all'implementazione di `AdminHeader`.

**Prerequisiti per RC 1.0**:
1. Fix codice: `src/app/admin/events/page.tsx` — sostituire `supabase` con `supabaseAdmin`
2. SQL RLS su `events`, `packages`, `event_sessions`
3. Policy pubblica `USING (true)` su `events`
4. Policy `USING (is_public = true AND is_active = true)` su `packages`
5. Policy `USING (is_bookable = true)` su `event_sessions`

---

## 5. SQL

### 5.1 — Creazione tabella `staff`

Da eseguire nel SQL Editor di Supabase prima di MS-B.

```sql
-- Tabella staff: operatori autorizzati ad accedere al backoffice ABRAZO
-- Collegata a auth.users tramite FK; ON DELETE CASCADE per coerenza
CREATE TABLE public.staff (
  id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       TEXT        NOT NULL,
  full_name   TEXT        NOT NULL,
  role        TEXT        NOT NULL CHECK (role IN ('super_admin', 'segreteria', 'direzione', 'checkin')),
  is_active   BOOLEAN     NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: abilitata, nessuna policy pubblica — accesso solo via service role (supabaseAdmin)
ALTER TABLE public.staff ENABLE ROW LEVEL SECURITY;

-- Indice per lookup rapido su is_active (usato da requireAuth e requireRole)
CREATE INDEX staff_active_idx ON public.staff(id) WHERE is_active = true;
```

### 5.2 — Inserimento primo operatore `super_admin`

Da eseguire dopo aver creato l'utente in Authentication → Users.
Sostituire `REPLACE-WITH-AUTH-USER-UUID` con l'UUID reale copiato dal Dashboard.

```sql
-- Inserimento super_admin
-- L'UUID deve corrispondere all'utente creato in Authentication → Users
INSERT INTO public.staff (id, email, full_name, role)
VALUES (
  'REPLACE-WITH-AUTH-USER-UUID',
  'andrea.russos@gmail.com',
  'Andrea Russos',
  'super_admin'
);

-- Verifica
SELECT id, email, full_name, role, is_active, created_at
FROM public.staff;
```

### 5.3 — Procedura per operatori aggiuntivi

Per ogni nuovo membro dello staff, eseguire in sequenza:

1. Authentication → Users → Add User (email + password temporanea)
2. Copiare l'UUID generato
3. Eseguire:

```sql
INSERT INTO public.staff (id, email, full_name, role)
VALUES (
  'UUID-DEL-NUOVO-UTENTE',
  'email@artango.it',
  'Nome Cognome',
  'segreteria'  -- oppure: direzione, checkin, super_admin
);
```

### 5.4 — Disattivazione operatore (non eliminazione)

```sql
-- Preferire is_active = false all'eliminazione
-- L'eliminazione dell'utente auth causa ON DELETE CASCADE sulla tabella staff
UPDATE public.staff
SET is_active = false, updated_at = NOW()
WHERE id = 'UUID-DELL-OPERATORE';
```

### 5.5 — Best Practice: script idempotenti

Gli script di bootstrap devono essere idempotenti quando possibile, per permettere la riesecuzione senza errori e semplificare le procedure operative.

Per l'inserimento di operatori, valutare l'utilizzo di `INSERT ... ON CONFLICT DO NOTHING` al posto del semplice `INSERT`:

```sql
-- Inserimento idempotente: nessun errore se il record esiste già
INSERT INTO public.staff (id, email, full_name, role)
VALUES (
  'UUID-UTENTE',
  'email@artango.it',
  'Nome Cognome',
  'segreteria'
)
ON CONFLICT (id) DO NOTHING;
```

Questa forma è preferibile negli script di provisioning e nelle procedure operative ripetibili. Non sostituisce i controlli applicativi, ma riduce il rischio di errori accidentali durante l'esecuzione manuale.

---

## 6. Gestione dei rischi

### R1 — Uso accidentale di `getSession()` al posto di `getClaims()` [ALTO]

**Descrizione**: `getSession()` non genera errori — passa silenziosamente anche con token manomessi. Un bug qui è invisibile durante i test normali.

**Mitigazione**: aggiungere un commento esplicito in `supabaseServer.ts` e `auth.ts` che vieta l'uso di `getSession()` e indica il metodo corretto. Il pattern corretto è documentato in questo piano e nella Design Review.

---

### R2 — Configurazione cookie su Vercel [MEDIO]

**Descrizione**: in produzione su Vercel, il comportamento dei cookie di sessione dipende dalla corretta configurazione di Site URL e Redirect URLs nel Dashboard Supabase.

**Mitigazione**: prima del deploy produzione, testare esplicitamente su staging Vercel. Verificare nel Dashboard Supabase che `Site URL` corrisponda al dominio di deploy e che i redirect URL siano configurati.

---

### R3 — `ON DELETE CASCADE` sulla tabella `staff` [MEDIO]

**Descrizione**: eliminare un utente da Supabase Auth → Authentication → Users cancella anche il record in `staff` senza traccia in audit.

**Mitigazione**: preferire sempre la disattivazione (`is_active = false`) all'eliminazione. Documentare questa procedura nel manuale operativo. Non eliminare mai utenti dal Dashboard senza prima disattivarli in `staff`.

---

### R4 — Creazione utenti manuali — errore UUID [BASSO-MEDIO]

**Descrizione**: un errore nel copiare l'UUID crea un utente autenticato che non riesce ad accedere al backoffice. Il messaggio di errore non è immediato.

**Mitigazione**: usare sempre lo script SQL della sezione 5.2 (non inserire UUID a mano nella console). Dopo l'inserimento, eseguire la query di verifica (`SELECT * FROM staff`).

---

### R5 — Route `export-xlsx` non protetta ✅ RISOLTO in MVP 0.9.7

**Descrizione**: `/api/events/[id]/export-xlsx` restituisce dati personali di tutti i partecipanti.

**Mitigazione applicata**: guard `getCurrentStaff()` + ruolo `direzione` o `super_admin`. Risposta 401 se non autenticato, 403 se ruolo insufficiente.

---

### R6 — Ruolo `checkin` accede a dati personali via API ✅ PARZIALMENTE RISOLTO in MVP 0.9.7

**Descrizione**: `/api/checkin/event` e `/api/checkin/activity` restituiscono nome, cognome, email del partecipante.

**Mitigazione applicata**: entrambe le API ora richiedono autenticazione con ruolo `checkin` o `super_admin`. Il nome rimane visibile ai checker — necessario per la verifica fisica all'ingresso. `operator_name` nell'audit ora riporta l'email reale invece di `"staff-demo"`.

---

### R7 — `supabaseAdmin` importato accidentalmente in bundle client [BASSO]

**Descrizione**: se `supabaseAdmin.ts` venisse importato in un Client Component, la service role key sarebbe esposta nel browser.

**Mitigazione**: il file `supabaseAdmin.ts` non ha il pacchetto `server-only` installato. Valutare l'aggiunta di `import 'server-only'` in cima al file durante MS-B — genera un errore di build se importato in contesto client.

---

## 7. Rollback

### MS-A

Eliminare il record da `staff` e/o eliminare l'utente da Authentication → Users. Nessun codice modificato.

### MS-B

Eliminare `src/lib/supabaseServer.ts` e `src/lib/auth.ts`. Rimuovere `@supabase/ssr` da `package.json` e eseguire `npm install`. Zero impatto sul comportamento dell'applicazione (i file erano inert).

### MS-C

Eliminare `src/proxy.ts`. Il proxy non è più attivo: `/admin/*` torna accessibile senza autenticazione. La build torna allo stato precedente.

### MS-D

Eliminare `src/app/login/page.tsx` e `src/app/login/LoginForm.tsx`. Il proxy di MS-C reindirizza a `/login`, ma la pagina non esiste — questo crea un 404. Il rollback di MS-D richiede contestualmente il rollback di MS-C.

### MS-E

Eliminare `src/app/login/actions.ts` e rimuovere il bottone logout da `src/app/admin/page.tsx`. La sessione rimane attiva fino alla scadenza naturale (1 ora per l'access token).

### MS-F

Rimuovere le chiamate `requireRole`/`requireAuth` dalle Server Actions. Le actions tornano eseguibili senza autenticazione. Rollback chirurgico, zero regressioni su altre funzionalità.

### MS-G

Ripristinare i file documentazione dallo stato precedente via `git revert` o manualmente. Nessun impatto sul codice.

---

## 8. Decision Log collegati

I seguenti Decision Log devono essere creati o aggiornati durante MS-G:

| ID | Titolo | Azione |
|---|---|---|
| DL-12 | Supabase Auth con `@supabase/ssr` per autenticazione SSR | Creare |
| DL-13 | Defense in Depth — Server Actions verificano auth indipendentemente | Creare |
| DL-14 | Tabella `staff` — naming e struttura | Creare |

**Riferimento operativo**:

| Decision Log | Milestone | Stato |
|---|---|---|
| DL-12 | MS-A | Da creare |
| DL-13 | MS-C | Da creare |
| DL-14 | MS-G | Da creare |

**Template per ogni entry**:

```
### DL-XX: <titolo>

**Data**: <data di implementazione>
**Decisione**: <la scelta fatta>
**Motivazione**: <il perché — già documentato nella Design Review>
**Alternative valutate**: <cosa è stato scartato>
**Stato**: confermata ✓
```

---

## 9. Checklist di uscita

```
## Checklist di uscita — MVP 0.9.8 Security Foundation

### Core (completati al 28 giugno 2026)
✅ Tabella staff con 4 ruoli — MS-A
✅ Foundation SSR Supabase (@supabase/ssr 0.12.0) — MS-B
✅ Proxy Next.js 16 su /admin/* — MS-C
✅ Pagina login email + password — MS-D
✅ Logout con signOut() e redirect — MS-E
✅ Server Actions protette (requireRole / requireAuth) — MS-F
✅ operator_name reale nell'audit trail — MS-F bonus
✅ API Routes protette con 401/403 JSON (getCurrentStaff) — MVP 0.9.7
✅ checked_in_by reale nelle API check-in — MVP 0.9.7
✅ RLS attivata su 10 tabelle contenenti dati sensibili — MS-H
✅ Build completata senza errori TypeScript

### Documentazione
✅ docs/05_ROADMAP.md — §2, §4, §4b, §4c aggiornati
✅ docs/architecture/SECURITY_IMPLEMENTATION_PLAN.md — MS-H, MS-RLS-B, status

### Rinviati a RC 1.0 (non blocchi)
☐ MS-RLS-B — policy pubbliche su events, packages, event_sessions
☐ AdminHeader condiviso con logout su tutte le 12 pagine admin
☐ docs/01_ARCHITECTURE.md — sezione autenticazione
☐ docs/04_GDPR_AND_SECURITY.md — sicurezza tecnica aggiornata
☐ docs/06_PROJECT_HISTORY.md — DL-12, DL-13, DL-14
☐ Push al remote

✅ Security Foundation COMPLETATA — MVP 0.9.8 pronto per deploy
```

### Riepilogo architettura di sicurezza attiva

```
Layer 1  src/proxy.ts        getClaims() — blocco a /admin/* senza sessione
Layer 2  src/lib/auth.ts     requireRole/requireAuth — Server Actions protette
Layer 3  getCurrentStaff()   401/403 JSON — API Routes protette
Layer 4  Supabase RLS        tabelle sensibili inaccessibili via client anon
```

Ogni layer è indipendente. Il fallimento di uno non compromette gli altri.

> Questa checklist è il modello standard per tutti i futuri piani di implementazione del progetto ABRAZO.
