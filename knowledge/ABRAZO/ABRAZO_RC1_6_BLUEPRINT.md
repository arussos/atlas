# ABRAZO RC1.6 — Blueprint Architetturale

**Versione**: 1.0.0  
**Stato**: Normativo — approvato prima dell'implementazione  
**Data**: Luglio 2026  
**Maintainer**: Art&Tango / ABRAZO  

> Questo documento è la fonte autorevole di tutte le decisioni architetturali della RC1.6.  
> Nessuna decisione di progettazione deve essere presa durante l'implementazione senza prima aggiornare questo Blueprint.  
> Ogni milestone implementativa deve citare le sezioni di questo documento che sta realizzando.

---

## Indice

1. [Executive Summary](#1-executive-summary)
2. [Stato reale di RC1.5](#2-stato-reale-di-rc15)
3. [Obiettivi RC1.6](#3-obiettivi-rc16)
4. [Non-obiettivi](#4-non-obiettivi)
5. [Principi architetturali](#5-principi-architetturali)
6. [Classificazione Core / Configurabile / Art&Tango](#6-classificazione-core--configurabile--arttango)
7. [Organization Model](#7-organization-model)
8. [Multi-Event Model](#8-multi-event-model)
9. [Activity-First Commerce](#9-activity-first-commerce)
10. [Commercial Engine — Panoramica](#10-commercial-engine--panoramica)
11. [Catalog / Activity Selection](#11-catalog--activity-selection)
12. [Validation Engine](#12-validation-engine)
13. [Pricing Engine](#13-pricing-engine)
14. [Opportunity Engine](#14-opportunity-engine)
15. [Campaign Engine](#15-campaign-engine)
16. [Commercial Simulator](#16-commercial-simulator)
17. [Price Snapshot e audit economico](#17-price-snapshot-e-audit-economico)
18. [Participant Form Configuration](#18-participant-form-configuration)
19. [Registration Change Requests](#19-registration-change-requests)
20. [Event Builder](#20-event-builder)
21. [Organization Console](#21-organization-console)
22. [Event Duplication](#22-event-duplication)
23. [Public Registration UX](#23-public-registration-ux)
24. [Modello dati proposto](#24-modello-dati-proposto)
25. [Compatibilità con RC1.5](#25-compatibilità-con-rc15)
26. [Strategia di migrazione](#26-strategia-di-migrazione)
27. [Sicurezza, RLS e autorizzazioni](#27-sicurezza-rls-e-autorizzazioni)
28. [Test strategy](#28-test-strategy)
29. [Osservabilità e audit](#29-osservabilità-e-audit)
30. [Ambiguità da chiarire con Art&Tango](#30-ambiguità-da-chiarire-con-arttango)
31. [Roadmap tecnica e milestone](#31-roadmap-tecnica-e-milestone)
32. [Percorso critico per early booking](#32-percorso-critico-per-early-booking)
33. [Definition of Done RC1.6](#33-definition-of-done-rc16)
34. [Evoluzione futura del dominio ABRAZO](#34-evoluzione-futura-del-dominio-abrazo)
35. [Principi che il Core ABRAZO non dovrà mai violare](#35-principi-che-il-core-abrazo-non-dovrà-mai-violare)
36. [Exit Criteria & Acceptance RC1.6](#36-exit-criteria--acceptance-rc16)

---

## 1. Executive Summary

ABRAZO RC1.6 è la prima versione production-ready per più eventi. Introduce il **Commercial Engine** activity-first, sostituisce il modello a pacchetti cliccabili con il riconoscimento automatico delle formule commerciali, e generalizza l'architettura per supportare Epico Tango Fest 2027 e Amare Tango 2027 senza modifiche al codice.

**Il vincolo temporale assoluto**: la funzionalità di early booking per Epico Tango Fest deve essere operativa entro il **30 settembre 2026** (81 giorni dalla data del Blueprint).

**Decisioni architetturali chiave**:

| Decisione | Scelta RC1.6 |
|---|---|
| Organization model | Single-org. Nessuna tabella `organizations`. Config in `organization_config`. |
| Multi-event | Slug-based routing. Admin event picker. Nessun UUID hardcoded. |
| Pacchetti | Rimossi dall'interfaccia pubblica. Evolvono in `pricing_bundles` interni al Pricing Engine. |
| Offerte commerciali | Risultato del motore, non entità persistenti. |
| Regole commerciali | Tabelle `pricing_stage_tiers` + `pricing_bundles` + `pricing_campaigns`. |
| Campi partecipante | Colonne strutturate + `extra_data jsonb` come escape hatch. Nessun EAV. |
| Pricing | Esclusivamente server-side. Frontend riceve solo il risultato strutturato. |

---

## 2. Stato reale di RC1.5

### 2.1 Funzionalità operative

RC1.5 (MVP 0.9.8) è un sistema funzionante in produzione con:
- Iscrizione Epico Tango Fest con selezione pacchetti
- Check-in evento e attività con QR scanner
- Segreteria con inbox pagamenti e conferma acconto/saldo
- Autenticazione staff a 4 ruoli con Supabase Auth
- RLS su tabelle sensibili
- Export Excel a 3 fogli
- Audit trail immutabile
- Email bilingue IT/EN

### 2.2 Gap critico: doppio schema

Il gap più grave di RC1.5 è la **divergenza tra le migration SQL e lo schema di produzione**. Le migration 001–005 descrivono un database legacy che non corrisponde all'applicazione reale.

| Tabella in migration 001 | Stato | Tabella reale usata dall'app |
|---|---|---|
| `event_sessions` | Legacy, non usata | `event_activities` |
| `session_teachers` | Legacy, non usata | `activity_teachers` |
| `package_items` | Legacy, non usata | `package_activities` |
| `registrations` | Legacy, non usata | `event_participants` |
| `registration_items` | Legacy, non usata | `event_participant_activities` |
| `couples` | Legacy, non usata | — |
| — | Assente dalla migration | `event_participant_audit` |
| — | Assente dalla migration | `teacher_couples` |
| — | Assente dalla migration | `staff` |
| — | Assente dalla migration | `registration_payments` (ADR-001) |

**La migration 005 abilita RLS su tabelle legacy non usate dall'applicazione.** Le tabelle reali non hanno migration.

### 2.3 Debiti tecnici documentati

| Debito | File | Gravità |
|---|---|---|
| UUID evento hardcoded | `admin/page.tsx` riga 6 | ALTO |
| Slug evento hardcoded | `register/epico-tango-fest-2027/page.tsx` riga 8 | ALTO |
| `TEACHER_CONFIG` con dati specifici Epico | `RegisterClient.tsx` riga 275 | ALTO |
| `packageCopy` con slug Epico-specifici | `RegisterClient.tsx` riga 216 | MEDIO |
| `teacher_pair_label` usato in 7 file | Vari | MEDIO |
| Calcolo prezzi duplicato client+server | `RegisterClient.tsx` + `AmountCalculator.ts` | MEDIO |
| Route pubblica hardcoded `/register/epico-tango-fest-2027` | Struttura cartelle | ALTO |

### 2.4 `registration_payments` (ADR-001)

L'ADR-001 ha documentato e approvato la tabella `registration_payments` come sostituzione del modello timestamp. **Lo stato di deploy in produzione deve essere verificato prima di iniziare RC1.6.** Se non è presente, è prerequisito della migration baseline.

### 2.5 Modello commerciale attuale

Il sistema RC1.5 usa pacchetti cliccabili con prezzo fisso. Il calcolo è:
```
deposit = sum(package.deposit_amount) + sum(direct_activity.price_amount) * 0.70
total   = sum(package.price) + sum(direct_activity.price_amount)
balance = total - deposit
```
Non esiste pricing progressivo, riconoscimento automatico di formule, campagne temporali, o suggerimenti commerciali.

---

## 3. Obiettivi RC1.6

### Obiettivi bloccanti (percorso critico — early booking)

- **OB-1**: Form iscrizione Activity-First per Epico (nessun pacchetto cliccabile, selezione attività)
- **OB-2**: Pricing Engine server-side con stage tiers progressivi e bundle giornalieri
- **OB-3**: Campaign Engine con sconto early booking 20% attivo fino al 30/09/2026
- **OB-4**: Routing slug-based generalizzato (`/register/[slug]`)
- **OB-5**: Rimozione UUID hardcoded dalla dashboard admin

### Obiettivi RC1.6 non bloccanti

- **OR-1**: Event Builder — CRUD eventi, attività, pricing rules dall'admin
- **OR-2**: Opportunity Engine — suggerimenti contestuali nel form
- **OR-3**: Registration Change Requests — flusso modifiche post-iscrizione
- **OR-4**: Commercial Simulator — test engine senza creare iscrizioni
- **OR-5**: Event Duplication
- **OR-6**: Configurazione form partecipante (nuovi campi: telefono, CF, tessera, ecc.)
- **OR-7**: Amare Tango 2027 — configurazione completo secondo evento
- **OR-8**: Baseline migration allineata allo schema reale

---

## 4. Non-obiettivi

Queste aree sono esplicitamente fuori scope per RC1.6:

| Area | Motivazione |
|---|---|
| Multi-tenancy / multi-organizzazione | Single-org per RC1.6. Punti di estensione predisposti. |
| Pagamenti online (Stripe/PayPal) | Flusso bonifico confermato per RC1.6 |
| Dominio Attività Accademiche (corsi, lezioni) | Futura RC2.x |
| Bot Telegram | Futura RC |
| Dashboard statistiche avanzate | Futura RC |
| PDF badge / stampa | Futura RC |
| Gestione volontari | Futura RC |
| RLS policy pubbliche su `events`/`packages` | Rimandato (non gap sicurezza attivo) |
| Refactoring `teacher_pair_label` | Affrontato solo se blocca nuove feature |

---

## 5. Principi architetturali

I principi che seguono integrano e specializzano i Design Principles esistenti (P01–P11) per il contesto RC1.6.

### P-RC1: Il Pricing Engine è l'unica fonte di verità per i prezzi

Nessun prezzo viene calcolato nel frontend. Nessun prezzo viene accettato dal client. La UI riceve solo il risultato strutturato dell'engine e lo mostra. Questo vale sia per il form pubblico sia per il simulatore admin sia per le modifiche post-iscrizione.

### P-RC2: Le offerte commerciali sono risultati, non entità

"Epico Venerdì", "Epico Sabato", "Pacchetto 3 Milonghe" non sono prodotti acquistabili né tabelle del database. Sono **label** associate al risultato del Pricing Engine quando le regole configurate si applicano alla selezione corrente. Questo evita la duplicazione tra regole e offerte e mantiene la configurazione atomica.

### P-RC3: Ogni regola commerciale è configurabile senza modifiche al codice

Prezzi, soglie, bundle, campagne temporali devono essere modificabili tramite la futura UI admin senza deploy. Le tabelle `pricing_stage_tiers`, `pricing_bundles`, `pricing_campaigns` sono la configurazione; il codice del Pricing Engine è il motore.

### P-RC4: Single Organization, Multi-Event

RC1.6 serve una singola organizzazione (Art&Tango) che gestisce più eventi. Non viene costruita infrastruttura multi-tenant. I punti di estensione per il futuro (campo `organization_id` come nullable FK) vengono predisposti ma non attivati.

### P-RC5: Nessun hardcoding di contenuto specifico Art&Tango nel Core

Testi commerciali, nomi di formule, descrizioni di maestri, URL, foto: ogni contenuto specifico di un evento o organizzazione deve risiedere nel database o in file di asset, non nel codice TypeScript del Core.

### P-RC6: La migration baseline precede qualsiasi nuova migration

Prima di aggiungere tabelle RC1.6, la migration `006` deve documentare lo schema reale corrente. Ogni nuovo collaboratore che esegue le migration ottiene un DB identico alla produzione.

### P-RC7: Il sistema deve rimanere deployabile dopo ogni milestone

Ogni milestone lascia il sistema in uno stato funzionante, testabile e retrocompatibile. Nessuna milestone "rompe tutto prima di ricostruirlo". Il percorso critico early booking è diviso in milestone indipendenti.

---

## 6. Classificazione Core / Configurabile / Art&Tango

### CORE ABRAZO
Funzionalità generiche disponibili per qualsiasi organizzatore.

- Modello partecipante / evento / iscrizione
- Generazione QR code con payload opaco
- Audit trail immutabile
- Check-in evento e attività
- Email di conferma (template configurabile)
- Export dati
- Autenticazione staff con ruoli
- Pricing Engine (motore puro)
- Validation Engine (overlap, prerequisiti)
- Opportunity Engine (struttura del risultato)
- Campaign Engine (sconti temporali configurabili)
- Commercial Simulator
- Registration Change Requests (flusso)
- Event Builder (CRUD admin)
- Event Duplication

### CORE CONFIGURABILE
Funzionalità Core il cui comportamento dipende dalla configurazione evento/organizzazione.

- Regole pricing (`pricing_stage_tiers`, `pricing_bundles`, `pricing_campaigns`) — configurate per evento
- Campi del form partecipante (quali campi mostrare e rendere obbligatori)
- Template email (override per evento)
- Lingue supportate
- Metodi di pagamento disponibili
- Policy acconto/saldo (percentuale acconto)
- Stato evento (draft/published/archived)
- Finestra di apertura iscrizioni

### PERSONALIZZAZIONE ART&TANGO
Contenuto specifico che non deve contaminare il Core.

- Foto e descrizioni dei maestri (da spostare nel DB)
- Testi hero e branding Epico/Amare Tango
- URL esterni (Google Maps, siti maestri)
- Nomi specifici delle formule ("Epico Venerdì", "Epico Sabato")
- Impostazioni IBAN e beneficiario (già in `events`)

**Regola operativa**: quando una richiesta Art&Tango può diventare un miglioramento Core Configurabile, si implementa la soluzione Core e si configura per Art&Tango. Non si aggiungono condizioni `if (event.slug === 'epico-...')` nel codice.

---

## 7. Organization Model

### Decisione

RC1.6 opera in modalità **Single Organization**. Non viene introdotta una tabella `organizations` come entità gestita. Art&Tango è l'organizzazione implicita del sistema.

La configurazione organizzativa è gestita da una tabella `organization_config` con struttura chiave-valore:

```sql
organization_config:
  key   text PRIMARY KEY
  value text NOT NULL
  updated_at timestamptz
```

Esempi di chiavi:
```
org_name        → "Art&Tango"
org_logo_url    → "/brand/artetango-logo.svg"
org_email_from  → "noreply@artango.it"
org_city        → "Mirandola"
default_language → "it"
default_currency → "EUR"
gdpr_contact_email → "privacy@artango.it"
```

### Punto di estensione per il futuro multi-tenant

Quando ABRAZO evolverà verso multi-tenant, il percorso è:
1. Creare tabella `organizations` (id, name, slug, config jsonb)
2. Aggiungere colonna `organization_id uuid REFERENCES organizations(id)` su `events` (nullable inizialmente)
3. Aggiornare RLS policies per isolare per organizzazione
4. Migrare Art&Tango come primo record

La struttura delle tabelle `events`, `event_participants`, ecc. non richiede modifiche strutturali: `organization_id` è aggiunto come FK senza cambiare le relazioni esistenti.

### Classificazione
**CORE CONFIGURABILE** — ogni organizzazione futura avrà la propria `organization_config`.

---

## 8. Multi-Event Model

### Decisione

RC1.6 generalizza il routing e la dashboard per supportare qualsiasi numero di eventi senza modifiche al codice.

### Routing pubblico

**Attuale (da eliminare)**: `/register/epico-tango-fest-2027/`  
**RC1.6**: `/register/[slug]/` — il loader legge l'evento per slug, carica configurazione e attività, passa tutto come props a un unico `RegisterClient` parametrico.

La cartella `src/app/register/epico-tango-fest-2027/` viene sostituita da `src/app/register/[slug]/`.

### Dashboard admin

**Attuale**: `ACTIVE_EVENT_ID` hardcoded con UUID.  
**RC1.6**: La dashboard admin mostra tutti gli eventi attivi. L'operatore seleziona l'evento da gestire. La selezione può essere mantenuta in session storage per continuità operativa ma non è hardcoded.

### Estensioni alla tabella `events`

```sql
-- Nuove colonne da aggiungere in migration 006/007
ALTER TABLE events ADD COLUMN IF NOT EXISTS
  status text NOT NULL DEFAULT 'draft'
  CHECK (status IN ('draft', 'test', 'published', 'archived'));

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  registration_open_at timestamptz;

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  registration_close_at timestamptz;

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  timezone text NOT NULL DEFAULT 'Europe/Rome';

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  currency text NOT NULL DEFAULT 'EUR';

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  supported_languages text[] NOT NULL DEFAULT ARRAY['it'];

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  deposit_rate numeric NOT NULL DEFAULT 0.70
  CHECK (deposit_rate > 0 AND deposit_rate <= 1.00);

ALTER TABLE events ADD COLUMN IF NOT EXISTS
  organization_id uuid;  -- nullable: punto di estensione multi-tenant
```

### Logica di visibilità

Un evento è accessibile pubblicamente solo se:
- `status = 'published'`
- `registration_open_at IS NULL OR registration_open_at <= now()`
- `registration_close_at IS NULL OR registration_close_at > now()`

Questa logica è applicata dal server loader di `/register/[slug]` — il client non decide mai se un evento è aperto.

---

## 9. Activity-First Commerce

### Decisione fondamentale

L'utente **non seleziona pacchetti**. L'utente seleziona **attività individuali**. Il sistema riconosce automaticamente le formule commerciali e applica il prezzo ottimale.

Questa è una rottura del modello RC1.5, gestita con compatibilità backward (§25).

### Cosa cambia nel frontend

**RC1.5**: Sezione "Pacchetti" (cliccabili) + sezione "Attività singole"  
**RC1.6**: Solo attività, raggruppate per categoria/giornata. Nessun blocco "pacchetto" selezionabile.

I nomi delle formule ("Epico Venerdì", "Pacchetto 3 Milonghe") appaiono **solo come risultato del calcolo** nella sezione riepilogo, non come prodotti nel form.

### Cosa rimane invariato nel backend

- La tabella `event_participant_activities` continua a tracciare ogni attività prenotata
- Il campo `source_type` evolve: da `'package' | 'single_selection'` a `'recognized_bundle' | 'single_selection'`
- La tabella `packages` viene preservata ma non esposta nel form pubblico (§25)

### Flusso Activity-First

```
[Browser] RegisterClient (slug-parametrico)
  │
  ├─ Utente seleziona attività
  ├─ POST /api/events/[id]/calculate-price
  │    └─ Pricing Engine → PricingResult (totale, breakdown, formule)
  ├─ UI mostra: totale, acconto, saldo, formule riconosciute, suggerimenti
  │
  └─ POST /api/event-participants (submit definitivo)
        ├─ Riesegue Pricing Engine server-side
        ├─ Ignora qualsiasi importo inviato dal client
        ├─ Salva pricing_snapshot su event_participants
        └─ Procede con QR, email, audit
```

Il frontend esegue **due** chiamate server-side: una per il preview live del prezzo (senza effetti permanenti) e una per la creazione definitiva. La seconda ricalcola sempre, non riusa il risultato della prima.

---

## 10. Commercial Engine — Panoramica

Il Commercial Engine è composto da quattro sottosistemi indipendenti con responsabilità distinte:

```
Catalog          → quali attività sono selezionabili (visibilità, capienza, orari)
Validation       → la selezione è valida? (overlap, prerequisiti, capienza)
Pricing          → quanto costa la selezione? (tier, bundle, campagne)
Opportunity      → cosa conviene aggiungere? (suggerimenti contestuali)
```

### Principio di indipendenza

Ogni sottosistema è una funzione pura (no side effects, no DB writes). L'API layer è l'unico punto che orchestra le chiamate e gestisce la persistenza.

### Interfaccia comune

```typescript
// Input comune a tutti i sottosistemi
type CommercialInput = {
  event_id: string;
  activity_ids: string[];
  role?: 'leader' | 'follower' | 'both' | 'not_applicable';
  simulation_date?: Date;  // default: now()
};

// Output del Pricing Engine (usato anche da Opportunity e Simulator)
type PricingResult = {
  total_amount: number;
  deposit_amount: number;
  balance_amount: number;
  breakdown: PricingLineItem[];
  recognized_formulas: RecognizedFormula[];
  campaign_applied: CampaignInfo | null;
  suggestions: OpportunitySuggestion[];  // dall'Opportunity Engine
  pricing_version: string;              // per snapshot reproducibility
  calculated_at: string;                // ISO timestamp
};

type PricingLineItem = {
  label_it: string;
  label_en: string;
  activity_ids: string[];    // attività coperte da questa riga
  unit_price: number;
  quantity: number;
  subtotal: number;
  source: 'tier' | 'bundle' | 'single' | 'discount';
};

type RecognizedFormula = {
  label_it: string;
  label_en: string;
  activity_ids: string[];
  total_price: number;
};

type OpportunitySuggestion = {
  type: 'complete_bundle' | 'next_tier' | 'complete_milonghe';
  label_it: string;
  label_en: string;
  missing_activity_ids: string[];
  current_total: number;
  simulated_total: number;
  incremental_cost: number;
  saving: number;
  priority: number;
};
```

---

## 11. Catalog / Activity Selection

### Responsabilità

Il Catalog determina quali attività sono visibili e prenotabili per un dato evento, ruolo e momento.

### Struttura `event_activities` (invariata + estensioni)

La tabella `event_activities` esiste già in produzione. Le estensioni RC1.6:

```sql
ALTER TABLE event_activities ADD COLUMN IF NOT EXISTS
  category text;  -- es. 'stage_venerdi', 'stage_sabato', 'milonga', 'show', 'orchestra'
  -- Usato per raggruppamento nel form e per regole pricing tipo-based

ALTER TABLE event_activities ADD COLUMN IF NOT EXISTS
  display_day text;  -- es. 'venerdi', 'sabato', 'domenica', null (multi-day o non rilevante)
  -- Permette raggruppamento per giornata nel form

ALTER TABLE event_activities ADD COLUMN IF NOT EXISTS
  is_exclusive boolean NOT NULL DEFAULT false;
  -- Se true, non può essere combinata con altre attività dello stesso slot
```

### Regole di visibilità

Un'attività è selezionabile se:
- `is_public = true`
- `is_bookable = true` (da `event_sessions.is_bookable` nel legacy; campo equivalente in `event_activities`)
- Capienza disponibile (se `capacity_total IS NOT NULL`)
- Non è già prenotata dal partecipante (verifica session-level)

### Classificazione
**CORE CONFIGURABILE** — la struttura è generica; il contenuto (quali attività, quali categorie) è configurato per evento.

---

## 12. Validation Engine

### Responsabilità

Il Validation Engine verifica che la selezione di attività sia legalmente coerente prima che il prezzo venga calcolato.

### Regole implementate in RC1.6

**V1 — Overlap temporale**: due attività con orari sovrapposti non possono coesistere nella stessa selezione. La sovrapposizione è verificata sulle colonne `start_datetime`, `end_datetime` di `event_activities`.

```typescript
type ValidationResult = {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
};

type ValidationError = {
  type: 'time_overlap' | 'capacity_exceeded' | 'prerequisite_missing';
  activity_ids: string[];
  message_it: string;
  message_en: string;
};
```

**V2 — Capienza**: se `capacity_total IS NOT NULL`, verifica che la somma di `event_participant_activities` per quell'attività non superi la capienza. La verifica è ottimistica (race condition possibile) — l'INSERT finale usa un trigger o check per il caso estremo.

**V3 — Prerequisiti** (struttura predisposta, nessun prerequisito definito in RC1.6): tabella `activity_prerequisites (activity_id, required_activity_id)` aggiunta ma vuota per RC1.6.

### Quando viene chiamato

- A ogni modifica della selezione nel form (debounced, per feedback immediato)
- All'atto del submit (definitivo, prima del pricing)
- La validation definitiva al submit è server-side; quella interattiva può essere client-side se la configurazione è già disponibile

### Classificazione
**CORE ABRAZO** — la logica di validazione è generica. Le regole specifiche (prerequisiti) sono configurabili.

---

## 13. Pricing Engine

### Principio

Il Pricing Engine è una **funzione pura** con firma:

```typescript
function computePrice(
  activities: ActivityRow[],
  stageTiers: PricingStageTier[],
  bundles: PricingBundle[],
  bundleActivities: PricingBundleActivity[],
  campaigns: PricingCampaign[],
  referenceDate: Date
): PricingResult
```

Non fa query al DB. Riceve tutti i dati necessari come parametri. L'orchestratore nel layer API si occupa di caricare i dati e chiamare la funzione.

### Algoritmo di calcolo (per Epico 2027)

Il motore applica le regole in questo ordine di priorità (configurabile via `priority` nelle tabelle):

**Step 1 — Controlla All Inclusive**  
Se la selezione copre tutte le attività incluse nella formula all-inclusive → prezzo = `pricing_bundles.total_price` dove `bundle_type = 'all_inclusive'`.

**Step 2 — Controlla bundle giornalieri**  
Per ogni `pricing_bundle` con `bundle_type = 'daily'`, verifica se tutte le attività required sono nella selezione. Se sì, raggruppa le attività in bundle. Ordina i bundle per priorità (più bundle si applicano? scegli la combinazione più vantaggiosa).

**Step 3 — Controlla bundle categorie**  
Per `bundle_type = 'category_pack'` (es. 3 milonghe), verifica il match. La logica di match è `contains`: tutte le attività del bundle devono essere nella selezione.

**Step 4 — Stage tier pricing**  
Conta gli stage non coperti da bundle (step 2-3). Cerca in `pricing_stage_tiers` il tier corrispondente alla quantità. Se lo stage count supera la soglia all-inclusive (`full_lezioni_threshold`), applica il cap.

**Step 5 — Attività singole residue**  
Le attività non coperte da bundle né da tier (es. show) vengono prezzate singolarmente a `event_activities.price_amount`.

**Step 6 — Applica campagna**  
Se esiste una `pricing_campaign` valida per `referenceDate`, applica lo sconto percentuale secondo il perimetro configurato (`applies_to`). Lo sconto viene applicato DOPO il riconoscimento di bundle e tier, non prima. Le ambiguità sulla cumulabilità sono elencate in §30.

**Step 7 — Calcola acconto**  
`deposit = total * event.deposit_rate` (default 0.70), arrotondato a 2 decimali. I bundle con `deposit_rate` specifico sovrascrivono il default.

### Tabelle di configurazione

```sql
-- Tier progressivi per categoria di attività (tipicamente stage)
CREATE TABLE pricing_stage_tiers (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id          uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  activity_category text NOT NULL,   -- 'stage' o altro tipo
  quantity          integer NOT NULL CHECK (quantity > 0),
  total_price       numeric(10,2) NOT NULL CHECK (total_price >= 0),
  label_it          text,
  label_en          text,
  is_active         boolean NOT NULL DEFAULT true,
  sort_order        integer NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (event_id, activity_category, quantity)
);

-- Bundle (giornalieri, categoria, all-inclusive)
CREATE TABLE pricing_bundles (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id      uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  slug          text NOT NULL,
  bundle_type   text NOT NULL CHECK (bundle_type IN ('daily', 'category_pack', 'all_inclusive')),
  label_it      text NOT NULL,
  label_en      text,
  total_price   numeric(10,2) NOT NULL CHECK (total_price >= 0),
  deposit_rate  numeric(4,3),   -- NULL = usa default evento
  match_mode    text NOT NULL DEFAULT 'exact'
                CHECK (match_mode IN ('exact', 'contains')),
  priority      integer NOT NULL DEFAULT 0,
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (event_id, slug)
);

-- Attività richieste per un bundle
CREATE TABLE pricing_bundle_activities (
  bundle_id     uuid NOT NULL REFERENCES pricing_bundles(id) ON DELETE CASCADE,
  activity_id   uuid REFERENCES event_activities(id) ON DELETE CASCADE,
  activity_type text,  -- 'stage' | 'milonga' | ecc. (usato per regole tipo-based)
  min_count     integer DEFAULT 1,
  -- VINCOLO: esattamente uno tra activity_id e activity_type deve essere non-null
  CHECK (
    (activity_id IS NOT NULL AND activity_type IS NULL) OR
    (activity_id IS NULL AND activity_type IS NOT NULL)
  ),
  PRIMARY KEY (bundle_id, COALESCE(activity_id::text, activity_type))
);
```

### Tabella `packages` in RC1.6

La tabella `packages` esistente è **preserved** senza modifiche strutturali. Non viene esposta nel form pubblico RC1.6 (`is_public` dei record esistenti può rimanere `true` ma la UI non la renderizza più). Le iscrizioni RC1.5 che referenziano `packages` rimangono valide. Le nuove tabelle `pricing_bundles` / `pricing_stage_tiers` sono il sistema di configurazione RC1.6. In futuro, se `packages` diventa ridondante, si documenta una migration di cleanup.

### Classificazione
**CORE CONFIGURABILE** — il motore è Core; la configurazione (tier, bundle, prezzi) è per evento.

---

## 14. Opportunity Engine

### Responsabilità

Genera suggerimenti commerciali contestuali basati sulla selezione corrente. È chiamato internamente dal Pricing Engine e restituisce `suggestions[]` nel `PricingResult`.

### Regole di suggerimento (RC1.6)

**OPP-1 — Next tier**: se con N stage la prossima soglia di tier è raggiungibile con 1 stage aggiuntivo e il delta di costo è favorevole.  
Esempio: con 3 stage (75€), aggiungere il 4° costa solo +10€ (totale 85€ invece di 100€ = 4×25€).

**OPP-2 — Complete daily bundle**: se mancano ≤ 2 attività per completare un bundle giornaliero, mostrare le attività mancanti, il costo incrementale e il risparmio.

**OPP-3 — Complete milonga pack**: se 2 milonghe sono selezionate, suggerire la terza con il risparmio rispetto al prezzo singolo.

**OPP-4 — Reach Full Lezioni**: se si è a 1–2 stage dal cap (200€), mostrare la distanza e il costo incrementale per stage aggiuntivi.

### Formato del risultato

Ogni suggerimento include:
- `type`: identificativo del tipo di suggerimento
- `label_it` / `label_en`: testo per la UI (configurabile nel bundle/tier)
- `missing_activity_ids[]`: attività da aggiungere per attivare il vantaggio
- `current_total`: prezzo attuale
- `simulated_total`: prezzo se il suggerimento fosse seguito
- `incremental_cost`: quanto costa aggiungere
- `saving`: risparmio rispetto al prezzo altrimenti pagato (0 se non c'è risparmio, solo convenienza)
- `priority`: ordine di visualizzazione

### Principio etico

L'Opportunity Engine non comunica mai false urgenze o informazioni ingannevoli. Mostra solo vantaggi verificabili. Non esiste un "sconto esclusivo" che non sia una regola reale. Non esiste "quasi esaurito" senza una capienza reale nel DB.

### Classificazione
**CORE ABRAZO** — la struttura dei suggerimenti è generica. I testi specifici ("Epico Venerdì") sono configurati nei bundle.

---

## 15. Campaign Engine

### Responsabilità

Gestisce le campagne temporali (sconti early booking, offerte speciali) in modo configurabile.

### Tabella `pricing_campaigns`

```sql
CREATE TABLE pricing_campaigns (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id         uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  label            text NOT NULL,   -- es. "Early Booking Settembre 2026"
  discount_percent numeric(5,2) NOT NULL
                   CHECK (discount_percent > 0 AND discount_percent <= 100),
  valid_from       date,            -- NULL = da sempre
  valid_until      date NOT NULL,   -- data inclusiva di fine validità
  applies_to       text NOT NULL DEFAULT 'all'
                   CHECK (applies_to IN ('all', 'stages', 'milonghe', 'bundles', 'single_activities')),
  is_stackable     boolean NOT NULL DEFAULT false,
  rounding_mode    text NOT NULL DEFAULT 'nearest'
                   CHECK (rounding_mode IN ('nearest', 'floor', 'ceil')),
  priority         integer NOT NULL DEFAULT 0,
  is_active        boolean NOT NULL DEFAULT true,
  created_at       timestamptz NOT NULL DEFAULT now()
);
```

### Logica di applicazione

1. Caricare tutte le campagne `is_active = true` per l'evento
2. Filtrare quelle valide per `reference_date` (tra `valid_from` e `valid_until`)
3. Ordinare per `priority` DESC
4. Se non sono stackable, applicare solo la prima valida per perimetro
5. Se sono stackable, sommare gli sconti (con limite 100%)

### Snapshot della campagna applicata

Quando una campagna è applicata, il `PricingResult` include `campaign_applied`:
```typescript
type CampaignInfo = {
  campaign_id: string;
  label: string;
  discount_percent: number;
  valid_until: string;
  base_amount: number;    // importo prima dello sconto
  discount_amount: number;
  final_amount: number;
};
```

Questo snapshot è salvato in `event_participants.pricing_snapshot` per garantire la riproducibilità del calcolo storico.

### Campagne per Epico 2027

| Campagna | Sconto | Valida fino |
|---|---|---|
| Early Booking settembre | 20% | 30/09/2026 |
| Early Booking dicembre | 10% | 31/12/2026 |
| Listino standard | — | — |

La campagna 20% ha `priority = 20`, la 10% ha `priority = 10`. Non sono stackable. Se una prenotazione avviene quando entrambe sono attive (impossibile con queste date), vince quella con priorità più alta.

---

## 16. Commercial Simulator

### Obiettivo

Consentire alla segreteria di verificare la configurazione del Pricing Engine senza creare iscrizioni reali. Fondamentale per validare la configurazione prima di pubblicare l'evento.

### Posizionamento

Pagina admin: `/admin/events/[id]/pricing-simulator`  
Autenticazione richiesta: `direzione` o `super_admin`.  
Percorso critico: **NO** (non blocca early booking, deve essere disponibile prima della pubblicazione dell'Event Builder).

### Funzionalità

1. **Selezione attività**: interfaccia uguale al form pubblico ma con tutti gli stage, milonghe, show visibili (inclusi quelli `is_public = false`)
2. **Data di simulazione**: default oggi, modificabile per testare campagne future/passate
3. **Risultato in tempo reale**: `PricingResult` completo con breakdown, formule riconosciute, suggerimenti
4. **Confronto campagne**: pulsante per vedere il prezzo senza campagna e con ogni campagna disponibile
5. **Export simulazione**: possibilità di esportare il risultato in JSON o tabella per documentazione

### Architettura

L'endpoint API `/api/events/[id]/calculate-price` (già necessario per il form pubblico) serve anche il simulatore. La differenza è il parametro `simulation_date` passato esplicitamente. Il simulatore è un thin client sopra lo stesso endpoint.

**Nessuna scrittura nel DB.** Il simulatore non crea `event_participants`, non genera QR, non invia email, non scrive audit.

### Classificazione
**CORE ABRAZO** — è uno strumento operativo generico per qualsiasi evento.

---

## 17. Price Snapshot e audit economico

### Problema

Quando le regole commerciali cambiano dopo che le iscrizioni sono già state create, le iscrizioni esistenti devono mantenere il prezzo calcolato al momento della prenotazione.

### Soluzione

**`pricing_snapshot jsonb`** su `event_participants`: salva il `PricingResult` completo al momento della creazione. Questo include:
- Regole applicate (tier IDs, bundle IDs)
- Campagna attiva al momento
- Breakdown analitico
- `pricing_version` per identificare la versione del motore

**`pricing_version text`** su `event_participants`: stringa semantica della versione del motore (es. `"rc1.6.0"`). Permette di sapere quale versione dell'algoritmo ha calcolato il prezzo.

### Campi aggiuntivi su `event_participants`

```sql
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  pricing_snapshot jsonb;

ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  pricing_version text;
```

### Immutabilità economica

Una volta che un'iscrizione è confermata (`registration_status = 'confirmed'`), il `total_amount`, `deposit_amount` e `balance_amount` non vengono più modificati automaticamente anche se le regole cambiano. Qualsiasi modifica economica post-conferma passa attraverso il flusso `Registration Change Requests` (§19) e produce un record in `registration_payments` (ADR-001).

### `registration_payments` (ADR-001)

Se non ancora in produzione, la migration baseline (§26) deve includere:

```sql
CREATE TABLE IF NOT EXISTS registration_payments (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_participant_id    uuid NOT NULL REFERENCES event_participants(id) ON DELETE RESTRICT,
  event_id                uuid NOT NULL REFERENCES events(id),
  amount                  numeric(10,2) NOT NULL CHECK (amount > 0),
  currency                text NOT NULL DEFAULT 'EUR',
  payment_type            text NOT NULL
                          CHECK (payment_type IN ('deposit','balance','supplement','adjustment')),
  payment_method          text NOT NULL
                          CHECK (payment_method IN ('bank_transfer','cash','external')),
  provider_name           text,
  provider_transaction_id text,
  description             text NOT NULL,
  recorded_by             uuid NOT NULL REFERENCES auth.users(id),
  recorded_at             timestamptz NOT NULL DEFAULT now(),
  created_at              timestamptz NOT NULL DEFAULT now()
);
```

---

## 18. Participant Form Configuration

### Decisione

Per RC1.6 si adotta un modello a **colonne strutturate** con un campo `extra_data jsonb` come escape hatch. Non viene introdotto un sistema EAV (Entity-Attribute-Value) dinamico.

**Motivazione**: i campi richiesti per RC1.6 sono identificati e stabili. Un sistema EAV completo (tabelle `form_fields`, `form_answers`) aggiungerebbe complessità progettuale e implementativa non proporzionata al vantaggio. La configurabilità "quali campi mostrare" è separata dalla struttura del dato: i campi esistono come colonne anche se non mostrati nel form.

### Nuovi campi su `participants`

```sql
ALTER TABLE participants ADD COLUMN IF NOT EXISTS
  fiscal_code text;         -- codice fiscale, stabile a vita del partecipante
```

### Nuovi campi su `event_participants`

```sql
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  phone text;               -- contatto per l'evento (può variare tra eventi)

ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  experience_years integer
  CHECK (experience_years IS NULL OR experience_years >= 0);

ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  is_couple boolean NOT NULL DEFAULT false;

ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  partner_name text;        -- nome partner indicato (testo libero, non FK)

ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  membership_card_type text;   -- es. 'ACSI', 'UISP', null
ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  membership_card_number text; -- numero tessera

ALTER TABLE event_participants ADD COLUMN IF NOT EXISTS
  extra_data jsonb;         -- escape hatch per futuri campi non strutturati
```

### Configurazione per evento

Quali campi appaiono nel form pubblico è determinato da `events.form_config jsonb`:

```sql
ALTER TABLE events ADD COLUMN IF NOT EXISTS
  form_config jsonb NOT NULL DEFAULT '{}'::jsonb;
```

Struttura di `form_config`:
```json
{
  "show_phone": true,
  "phone_required": false,
  "show_fiscal_code": false,
  "show_experience_years": true,
  "show_is_couple": true,
  "show_partner_name": true,
  "show_membership_card": true,
  "membership_card_types": ["ACSI"]
}
```

Il server loader di `/register/[slug]` carica `form_config` e lo passa al RegisterClient. Il client mostra/nasconde i campi in base alla configurazione. La validazione server-side usa la stessa `form_config` per verificare i required.

### Note GDPR

- `fiscal_code` su `participants` è dato personale strutturato. Raccolta solo se `show_fiscal_code = true`.
- `phone` su `event_participants` permette di avere numeri diversi per eventi diversi (un partecipante può cambiare numero).
- `membership_card_number` è dato personale — raccogliere solo se strettamente necessario per l'evento.
- Ogni nuovo campo deve avere motivazione documentata in `form_config`.

### Classificazione
- **CORE** i campi
- **CORE CONFIGURABILE** la presenza nel form (via `form_config`)

---

## 19. Registration Change Requests

### Obiettivo

Consentire a partecipanti e segreteria di richiedere modifiche post-iscrizione mantenendo l'integrità dello snapshot economico originale.

### Tabella `registration_change_requests`

```sql
CREATE TABLE registration_change_requests (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_participant_id    uuid NOT NULL REFERENCES event_participants(id),
  event_id                uuid NOT NULL REFERENCES events(id),
  source                  text NOT NULL DEFAULT 'staff'
                          CHECK (source IN ('participant', 'staff')),
  activities_to_add       uuid[] NOT NULL DEFAULT '{}',
  activities_to_remove    uuid[] NOT NULL DEFAULT '{}',
  free_text               text,
  status                  text NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','in_review','approved','rejected','applied')),
  original_total_amount   numeric(10,2) NOT NULL,
  proposed_total_amount   numeric(10,2),   -- calcolato quando approvata
  price_delta             numeric(10,2),   -- positivo = deve pagare di più
  assigned_to             uuid REFERENCES auth.users(id),
  response_text           text,
  resolved_at             timestamptz,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);
```

### Flusso operativo

1. **Richiesta**: staff o (futuro) partecipante crea `registration_change_request` con le modifiche desiderate
2. **Revisione**: segreteria o `direzione` valuta la richiesta nella Pratica Partecipante
3. **Calcolo**: il sistema ricalcola il prezzo con le modifiche usando il Pricing Engine
4. **Approvazione**: segreteria approva → il sistema:
   - Aggiorna `event_participant_activities`
   - Ricalcola `total_amount` / `balance_amount`
   - Se `price_delta > 0`: crea un record `registration_payments` con `payment_type = 'supplement'`
   - Aggiorna `pricing_snapshot`
   - Scrive audit `registration_change_applied`
5. **Rifiuto**: segreteria rifiuta → `status = 'rejected'`, `response_text` spiega il motivo

### Principio di immutabilità economica

Lo snapshot originale (`original_total_amount`, `pricing_snapshot`) non viene mai cancellato. Ogni modifica produce un delta documentato. La storia è ricostruibile.

### Classificazione
**CORE ABRAZO** — il flusso è generico; i prezzi usano lo stesso Pricing Engine.

---

## 20. Event Builder

### Obiettivo

Consentire la creazione e configurazione completa di un evento dall'interfaccia admin senza SQL né modifiche al codice.

### Struttura delle pagine admin

```
/admin/events/new                      → Crea nuovo evento
/admin/events/[id]/settings            → Impostazioni evento (nome, date, IBAN, status)
/admin/events/[id]/activities/manage   → CRUD attività
/admin/events/[id]/pricing/tiers       → Configura tier progressivi
/admin/events/[id]/pricing/bundles     → Configura bundle giornalieri
/admin/events/[id]/pricing/campaigns   → Configura campagne sconto
/admin/events/[id]/teachers            → Maestri e coppie
/admin/events/[id]/form-config         → Configurazione form partecipante
/admin/events/[id]/email-settings      → Override template email
/admin/events/[id]/pricing-simulator   → Commercial Simulator (§16)
/admin/events/[id]/publish             → Anteprima e pubblicazione
```

### Flusso di pubblicazione

```
draft → (valida configurazione) → test → (preview pubblica OK) → published
```

La validazione controlla:
- Almeno una attività `is_public = true`
- Almeno un tier o bundle configurato
- `iban` e `beneficiary` presenti
- Date evento coerenti
- Finestra iscrizioni configurata

### Percorso critico

**Non blocca early booking**: la pubblicazione di Epico può avvenire tramite configurazione diretta del DB (come RC1.5). L'Event Builder è un obiettivo RC1.6 non bloccante.

### Classificazione
**CORE ABRAZO** — strumento generico di configurazione eventi.

---

## 21. Organization Console

### Obiettivo

Configurazione dell'organizzazione (Art&Tango) accessibile a `super_admin`.

### Pagina admin

```
/admin/organization → Impostazioni organizzazione
```

### Configurazioni gestibili

- Nome organizzazione
- Logo e branding (URL file in Supabase Storage)
- Email mittente (aggiorna `organization_config.org_email_from`)
- Testo note legali / privacy per il form
- Operatori staff (CRUD su tabella `staff`)

### Classificazione
**CORE CONFIGURABILE** — la struttura è generica; il contenuto è Art&Tango.

---

## 22. Event Duplication

### Cosa si copia

| Elemento | Copiato |
|---|---|
| Dati evento (nome, date, venue) | Sì — come bozza, titolo "(Copia di...)" |
| Attività | Sì — come bozza |
| Pricing tiers | Sì |
| Pricing bundles | Sì |
| Pricing campaigns | No — le date cambiano |
| Teacher couples | Sì |
| Form config | Sì |
| Email template overrides | Sì |
| Iscrizioni | No |
| Pagamenti | No |
| Check-in | No |
| QR code | No |
| Audit log | No |

### Implementazione

Server Action `duplicateEvent(sourceEventId)` → crea tutte le righe in transazione (Supabase RPC) → restituisce il nuovo `event.id` → redirect a `/admin/events/[newId]/settings`.

### Classificazione
**CORE ABRAZO** — funzionalità generica.

---

## 23. Public Registration UX

### Layout del form `/register/[slug]`

```
HERO (branding evento — contenuto dal DB)
  └─ nome evento, date, venue, badge early booking
  
FORM PARTECIPANTE
  └─ nome, cognome, email, ruolo + campi configurati in form_config
  
CALENDARIO ATTIVITÀ
  └─ Raggruppamento per giornata (display_day) o categoria
  └─ Ogni attività: titolo, ora, sala, maestri, prezzo singolo
  └─ Selezione con toggle
  
RIEPILOGO (sticky su desktop, collassabile su mobile)
  └─ Attività selezionate
  └─ Formule riconosciute (label del bundle/tier applicato)
  └─ Totale, acconto, saldo
  └─ Campagna applicata (se presente)
  └─ Suggerimenti Opportunity Engine
  
MAESTRI (se teacher_couples configurate per l'evento)
  └─ Card con foto, descrizione, link profilo — dati dal DB
  └─ Highlight quando le loro attività sono nella selezione
  
PRIVACY E CONSENSI
  └─ Privacy (obbligatorio), Termini (obbligatorio), Media (facoltativo)
  
SUBMIT
```

### Flusso di prezzi

Il form invia a `/api/events/[id]/calculate-price` ad ogni modifica della selezione (debounced 300ms). Il risultato aggiorna il riepilogo. Al submit, il server ricalcola indipendentemente.

### Generalizzazione `TEACHER_CONFIG`

Il `TEACHER_CONFIG` hardcoded in `RegisterClient.tsx` viene eliminato. I dati maestri (foto, descrizione IT/EN, URL profilo) vengono spostati nella tabella `teacher_couples`:

```sql
ALTER TABLE teacher_couples ADD COLUMN IF NOT EXISTS
  description_it text;
ALTER TABLE teacher_couples ADD COLUMN IF NOT EXISTS
  description_en text;
ALTER TABLE teacher_couples ADD COLUMN IF NOT EXISTS
  profile_url text;
ALTER TABLE teacher_couples ADD COLUMN IF NOT EXISTS
  photo_storage_path text;  -- path in Supabase Storage
ALTER TABLE teacher_couples ADD COLUMN IF NOT EXISTS
  is_special_guest boolean NOT NULL DEFAULT false;
```

Il componente `RegisterClient` legge questi dati come props dal server loader.

### Compatibilità con il branding evento

Il branding specifico dell'evento (colori hero, sfondi, testi di presentazione) viene gestito tramite `events.branding_config jsonb`. Per RC1.6 può essere un campo semplice con background color e headline text. Il componente React lo applica via style inline.

---

## 24. Modello dati proposto

### Tabelle esistenti (invariate strutturalmente)

- `events` — estesa con colonne RC1.6 (status, registration windows, deposit_rate, form_config, timezone, currency, supported_languages, organization_id)
- `participants` — estesa con `fiscal_code`
- `event_participants` — estesa con phone, experience_years, is_couple, partner_name, membership_card_*, pricing_snapshot, pricing_version, extra_data
- `event_activities` — estesa con category, display_day, is_exclusive
- `event_participant_activities` — source_type evolve a include `'recognized_bundle'`
- `event_participant_audit` — invariata
- `teacher_couples` — estesa con description_it/en, profile_url, photo_storage_path, is_special_guest
- `teachers` — invariata
- `activity_teachers` — invariata
- `staff` — invariata
- `checkins` — invariata
- `packages` — preserved, non usata nel form pubblico RC1.6

### Tabelle da aggiungere (RC1.6)

| Tabella | Scopo |
|---|---|
| `pricing_stage_tiers` | Tier progressivi per categoria attività |
| `pricing_bundles` | Bundle giornalieri, category pack, all-inclusive |
| `pricing_bundle_activities` | Attività richieste per ogni bundle |
| `pricing_campaigns` | Sconti temporali configurabili |
| `registration_change_requests` | Richieste modifica post-iscrizione |
| `registration_payments` | Ledger pagamenti (ADR-001, se non già presente) |
| `organization_config` | Configurazione organizzazione single-tenant |
| `activity_prerequisites` | Prerequisiti tra attività (struttura predisposta, vuota) |

### Relazioni chiave RC1.6

```
events (1)
  ├── event_activities (N)
  │     └── pricing_bundle_activities (N) ← pricing_bundles (N)
  │                                             └── events (1)
  ├── pricing_stage_tiers (N)
  ├── pricing_bundles (N)
  ├── pricing_campaigns (N)
  ├── event_participants (N)
  │     ├── participants (1)
  │     ├── event_participant_activities (N)
  │     ├── registration_payments (N)       ← ADR-001
  │     ├── registration_change_requests (N)
  │     ├── checkins (N)
  │     └── event_participant_audit (N)
  └── teacher_couples (N)
        └── activity_teachers → teachers
```

---

## 25. Compatibilità con RC1.5

### Iscrizioni esistenti

Le iscrizioni create con RC1.5 (con pacchetti cliccabili) rimangono valide. I record in `event_participant_activities` con `source_type = 'package'` e `package_id` referencing `packages` sono preservati intatti. Non viene eseguita nessuna migration dei dati esistenti.

### Flusso legacy `/register/[eventId]`

Il flusso generico legacy (`src/app/register/[eventId]/`) e l'API `/api/registrations` sono stati documentati come deprecati. RC1.6 non li rimuove ma li lascia invariati. La rimozione è programmata per RC2.0 dopo che tutti gli eventi attivi usano il nuovo flusso.

### Tabella `packages`

Preservata con tutti i dati. I vecchi record mantengono `is_public = true` (ma la nuova UI non li renderizza). I nuovi bundle sono in `pricing_bundles`. Non esiste migrazione dati tra le due tabelle.

### `AmountCalculator.ts`

La versione attuale (`calculateAmounts`) rimane per compatibilità con il flusso legacy. Il nuovo Pricing Engine è in `src/lib/commerce/PricingEngine.ts`. I due coesistono durante la transizione.

### API `/api/event-participants`

L'endpoint esistente viene esteso per supportare il flusso activity-first. Il campo `package_ids` diventa opzionale (array vuoto = nessun pacchetto, comportamento RC1.6). Il campo `activity_ids` rimane obbligatorio. Il calcolo prezzi viene sostituito con il Pricing Engine mantenendo la stessa interfaccia di risposta.

---

## 26. Strategia di migrazione

### Principio

Le migration devono essere idempotenti (`IF NOT EXISTS`, `IF NOT EXISTS`). L'ordine è fondamentale: ogni migration dipende dalle precedenti.

### Migration 006 — Schema baseline attuale

**File**: `supabase/migrations/006_schema_baseline_rc15.sql`  
**Scopo**: documentare lo schema reale di produzione per allineare le migration alla realtà.

Contiene `CREATE TABLE IF NOT EXISTS` per tutte le tabelle che esistono in produzione ma non nelle migration (001–005):
- `event_activities`, `activity_teachers`
- `event_participants`, `event_participant_activities`
- `event_participant_audit`
- `teacher_couples`
- `staff`
- `package_activities`
- `registration_payments` (se non ancora in produzione)
- Tabelle viste (ricreate come `SECURITY INVOKER`)

### Migration 007 — Organization config e estensioni events

**File**: `supabase/migrations/007_organization_and_events_rc16.sql`

- `CREATE TABLE organization_config`
- `ALTER TABLE events ADD COLUMN` per status, registration windows, deposit_rate, timezone, currency, supported_languages, form_config, organization_id, branding_config

### Migration 008 — Participant form fields

**File**: `supabase/migrations/008_participant_form_fields_rc16.sql`

- `ALTER TABLE participants ADD COLUMN fiscal_code`
- `ALTER TABLE event_participants ADD COLUMN` per phone, experience_years, is_couple, partner_name, membership_card_*, pricing_snapshot, pricing_version, extra_data

### Migration 009 — Pricing Engine tables

**File**: `supabase/migrations/009_pricing_engine_rc16.sql`

- `CREATE TABLE pricing_stage_tiers`
- `CREATE TABLE pricing_bundles`
- `CREATE TABLE pricing_bundle_activities`
- `CREATE TABLE pricing_campaigns`

### Migration 010 — Activity catalog extensions

**File**: `supabase/migrations/010_activity_catalog_rc16.sql`

- `ALTER TABLE event_activities ADD COLUMN` per category, display_day, is_exclusive
- `ALTER TABLE teacher_couples ADD COLUMN` per description_it/en, profile_url, photo_storage_path, is_special_guest
- `CREATE TABLE activity_prerequisites` (vuota)

### Migration 011 — Registration Change Requests

**File**: `supabase/migrations/011_registration_change_requests_rc16.sql`

- `CREATE TABLE registration_change_requests`

### Seed data

Le migration di seed (dati iniziali per Epico e Amare Tango) sono separate dalle migration strutturali:
- `seed_epico_2027_pricing.sql` — tier stage, bundle giornalieri, campagne per Epico
- `seed_amare_tango_2027.sql` — evento Amare Tango con configurazione

---

## 27. Sicurezza, RLS e autorizzazioni

### Layer di sicurezza (invariati da RC1.5)

```
Layer 1: src/proxy.ts         → blocca /admin/* senza sessione
Layer 2: src/lib/auth.ts      → requireRole su Server Actions
Layer 3: getCurrentStaff()    → 401/403 su API Routes
Layer 4: Supabase RLS          → accesso via service_role per admin
```

### Nuove API Routes e autorizzazioni RC1.6

| Endpoint | Metodo | Auth richiesta |
|---|---|---|
| `/api/events/[id]/calculate-price` | POST | Pubblica (no auth) |
| `/api/events/[id]/simulate-pricing` | POST | `direzione` o `super_admin` |
| `/api/events/[id]/pricing/tiers` | GET/POST/PATCH | `super_admin` |
| `/api/events/[id]/pricing/bundles` | GET/POST/PATCH | `super_admin` |
| `/api/events/[id]/pricing/campaigns` | GET/POST/PATCH | `super_admin` |
| `/api/events/[id]/duplicate` | POST | `super_admin` |
| `/api/change-requests/[id]/approve` | POST | `segreteria` |

### RLS per le nuove tabelle

Le nuove tabelle di configurazione (`pricing_stage_tiers`, `pricing_bundles`, ecc.) sono lette dall'applicazione esclusivamente via `supabaseAdmin` (service_role). RLS abilitata con default deny — nessuna policy pubblica.

`registration_change_requests` contiene dati personali: RLS abilitata, service_role only.

### API pubblica `/api/events/[id]/calculate-price`

Questa API è pubblica (chiamata dal form durante la selezione). Non espone dati personali — riceve e restituisce solo importi e label. Rate limiting via middleware (da configurare in Vercel o Next.js).

---

## 28. Test strategy

### Unità (Pricing Engine)

Il Pricing Engine è una funzione pura → test unitari diretti senza mock DB.

```typescript
// Esempio test
describe('PricingEngine', () => {
  it('applica tier corretto per 4 stage', () => {
    const result = computePrice(
      [stage1, stage2, stage3, stage4], tiers, [], [], [], today
    );
    expect(result.total_amount).toBe(85);
  });
  
  it('riconosce Epico Venerdì quando selezionati 2 stage + milonga + show', () => {
    const result = computePrice(
      [stageV1, stageV2, milongaV, showV], tiers, bundles, bundleActs, [], today
    );
    expect(result.recognized_formulas[0].label_it).toBe('Epico Venerdì');
    expect(result.total_amount).toBe(60);
  });
  
  it('applica sconto 20% early booking per date entro settembre', () => {
    const result = computePrice(
      [stageV1], tiers, [], [], [earlyBookingCampaign], new Date('2026-09-15')
    );
    expect(result.total_amount).toBe(20); // 25 * 0.80
  });
});
```

### Integrazione (API Routes)

- `POST /api/events/[id]/calculate-price` → verifica risultato con dati reali evento
- `POST /api/event-participants` → verifica che il prezzo calcolato dal client venga ignorato
- `POST /api/change-requests/[id]/approve` → verifica atomicità (payment + update + audit)

### E2E (form pubblico)

- Selezionare 4 stage → prezzo 85€ mostrato nel form
- Selezionare Epico Venerdì → formula riconosciuta nel riepilogo
- Aggiungere terza milonga → suggerimento completamento mostrato
- Submit con early booking attivo → prezzo scontato nel DB
- Submit con data post-scadenza → prezzo listino nel DB

### Regression test per RC1.5

- Iscrizioni esistenti non modificate dalla migration baseline
- Export Excel funzionante su iscrizioni RC1.5
- Check-in su QR generati con RC1.5

---

## 29. Osservabilità e audit

### Nuovi eventi audit RC1.6

| `event_type` | Quando |
|---|---|
| `pricing_calculated` | Ogni submit definitivo (con snapshot) |
| `change_request_created` | Creazione richiesta modifica |
| `change_request_approved` | Approvazione con delta |
| `change_request_rejected` | Rifiuto con motivazione |
| `price_simulation_run` | Ogni simulazione admin (solo in ambiente di staging) |

### Logging del Pricing Engine

Per ogni iscrizione il `pricing_snapshot` contiene tutto il necessario per riprodurre il calcolo. Se il motore produce risultati anomali, il log è nel dato stesso.

### Export audit

La funzionalità di export audit log (chi ha scaricato cosa) è pianificata come RC1.6 non-bloccante. Ogni accesso all'export Excel produce un record audit `export_downloaded`.

---

## 30. Ambiguità da chiarire con Art&Tango

> **ATTENZIONE**: queste ambiguità devono essere risolte prima di implementare il Pricing Engine. Non assumere interpretazioni senza conferma diretta da Art&Tango. Bloccare l'implementazione delle regole in attesa delle risposte.

### Struttura delle formule

| # | Domanda | Impatto |
|---|---|---|
| A1 | "All Inclusive" (240€) e "Full Lezioni" (200€) sono la stessa formula o due diverse? Se diverse, cosa comprende esattamente ciascuna? | Struttura fondamentale dei bundle |
| A2 | Lo spettacolo teatrale da 15€ è incluso nelle formule Epico Venerdì/Sabato/Domenica? O è un biglietto separato sempre a pagamento? | Composizione bundle giornalieri |
| A3 | "Orchestra" negli stage del sabato (Epico Sabato: 6 stage + milonga + orchestra + show): cos'è esattamente "orchestra"? È un'attività separata nel catalogo? | Composizione bundle Sabato |
| A4 | Epico Domenica include "show": è lo stesso show teatrale da 15€ o uno show differente? | Composizione bundle |

### Sconti e campagne

| # | Domanda | Impatto |
|---|---|---|
| B1 | Gli sconti early booking (20% e 10%) si applicano a TUTTE le formule (tier, bundle, singole attività) o ci sono esclusioni? | `applies_to` in `pricing_campaigns` |
| B2 | Lo sconto si applica al totale DOPO il riconoscimento di bundle/tier, o PRIMA? (Es. con Epico Venerdì a 60€: lo sconto del 20% dà 48€, o si scontano le singole attività prima e poi si verifica se è ancora conveniente il bundle?) | Algoritmo del Campaign Engine |
| B3 | Gli sconti early booking si cumulano tra loro? (Es. qualcuno prenota quando entrambe le campagne sono attive — impossibile con le date indicate, ma meglio chiarire) | `is_stackable` |
| B4 | C'è uno sconto per i soci Art&Tango o per i possessori di tessera ACSI? Se sì, percentuale e perimetro | Nuova campagna da modellare |

### Regole stage

| # | Domanda | Impatto |
|---|---|---|
| C1 | "Full Lezioni" a 200€: corrisponde esattamente a 10 o più stage? O è una formula indipendente con un set specifico di attività incluse? | Se è tier: max_quantity = unlimited; se è bundle: elenco specifico |
| C2 | Con 11 stage: il prezzo è ancora 200€ o sale (200€ + 20€ per l'undicesimo)? | Configurazione tier per N > 10 |
| C3 | La regola "suggerimento commerciale sul quarto stage" (§ Business): il sistema deve suggerire di aggiungere il quarto stage PROATTIVAMENTE quando ne sono selezionati 3? | Configurazione Opportunity Engine |
| C4 | Le formule giornaliere (Epico Venerdì, Sabato, Domenica) si basano su stage specifici (quelli del venerdì/sabato/domenica) o su qualsiasi N stage indipendentemente dal giorno? | Composizione bundle: `activity_id` specifici vs `activity_type + display_day` |
| C5 | Se un partecipante seleziona Epico Sabato (6 stage) + 2 stage aggiuntivi: il prezzo è 130€ (bundle) + 2 stage singoli a 20€ ciascuno? O i 2 aggiuntivi entrano in un tier globale? | Interazione bundle + tier residuo |

### Logistica e operatività

| # | Domanda | Impatto |
|---|---|---|
| D1 | I pernottamenti: solo informazione (link esterno) o servizio gestito da ABRAZO (prenotazione, capienza, prezzo)? | Architettura catalogo attività |
| D2 | La tessera ACSI: è obbligatoria per partecipare? Viene verificata dalla segreteria? ABRAZO deve validarla o solo raccoglierla? | Validazione form partecipante |
| D3 | Politica cancellazione: il partecipante può cancellare autonomamente? Entro quando? Con rimborso? | Registration Change Requests + Refund flow |
| D4 | Modifiche post-iscrizione con campagna scaduta: si ricalcola al prezzo di listino o si mantiene lo sconto originale? | Pricing Engine nella modifica |

---

## 31. Roadmap tecnica e milestone

### Milestone M-RC16-01 — Schema Baseline

**Prerequisiti**: verifica stato production DB  
**Obiettivo**: allineare le migration alla realtà  
**File**: `supabase/migrations/006_schema_baseline_rc15.sql`  
**Contenuto**: CREATE TABLE IF NOT EXISTS per tutte le tabelle reali  
**Test**: `supabase db reset` + `npm run build` produce un sistema identico alla produzione  
**Compatibilità**: idempotente, nessun impatto  
**Non blocca**: Tutto. Prerequisito di tutto il resto.

---

### Milestone M-RC16-02 — Multi-Event Routing

**Prerequisiti**: M-RC16-01  
**Obiettivo**: eliminare UUID hardcoded e slug hardcoded; routing parametrico  
**Migration**: 007 (colonne events)  
**File modificati**:
- `src/app/register/[slug]/page.tsx` (nuova cartella)
- `src/app/register/[slug]/RegisterClient.tsx` (parametrico)
- `src/app/admin/page.tsx` (event picker)
- Redirect da `/register/epico-tango-fest-2027` a `/register/epico-tango-fest-2027` (alias temporaneo, stessa route)

**Criteri di accettazione**:
- `/register/epico-tango-fest-2027` continua a funzionare (same slug, new routing)
- `/register/amare-tango-2027` funziona se l'evento esiste nel DB
- Dashboard admin mostra lista eventi senza UUID hardcoded

---

### Milestone M-RC16-03 — Pricing Engine Core

**Prerequisiti**: M-RC16-01, risposte ad almeno A1-A4, C1-C5 di §30  
**Obiettivo**: implementare il Pricing Engine con stage tiers e bundle giornalieri  
**Migration**: 009 (pricing tables), seed Epico pricing  
**File nuovi**:
- `src/lib/commerce/PricingEngine.ts`
- `src/lib/commerce/ValidationEngine.ts`
- `src/lib/commerce/OpportunityEngine.ts`
- `src/app/api/events/[id]/calculate-price/route.ts`

**Test richiesti**:
- Unit test completo del Pricing Engine (tutti i tier, tutti i bundle)
- Test campagna early booking 20%
- Test Epico: simulare tutte le combinazioni principali

**Criteri di accettazione**:
- `computePrice([stageV1, stageV2, milongaV, showV], ...) → { total: 60, recognized: ['Epico Venerdì'] }`
- Il prezzo calcolato lato server è indipendente dal client

---

### Milestone M-RC16-04 — Campaign Engine

**Prerequisiti**: M-RC16-03, risposte a B1-B4 di §30  
**Obiettivo**: implementare sconti early booking configurabili  
**Migration**: seed campagne Epico in `pricing_campaigns`  
**File modificati**: `PricingEngine.ts` (aggiunta step 6)  
**Test**: prenotazione con data 15/09/2026 → sconto 20%; data 01/01/2027 → prezzo listino

---

### Milestone M-RC16-05 — Activity-First Form

**Prerequisiti**: M-RC16-02, M-RC16-03, M-RC16-04  
**Obiettivo**: form pubblico senza pacchetti cliccabili, con prezzi live e Opportunity Engine  
**Migration**: 010 (activity catalog extensions), seed teacher_couples Epico  
**File modificati**:
- `src/app/register/[slug]/RegisterClient.tsx` (riscrittura form)
- Rimozione `TEACHER_CONFIG` hardcoded
- Rimozione `packageCopy` hardcoded

**Criteri di accettazione**:
- TEACHER_CONFIG rimosso dal codice TypeScript
- Prezzo calcolato lato server, non accettato dal client
- Formule riconosciute mostrate nel riepilogo
- Suggerimenti Opportunity Engine visibili
- Build TypeScript pulita (`npm run build`)
- Test su viewport mobile ≤390px

---

### Milestone M-RC16-06 — Participant Form Extended

**Prerequisiti**: M-RC16-05, risposte a D2 di §30 per tessera ACSI  
**Obiettivo**: nuovi campi partecipante configurabili  
**Migration**: 008 (participant form fields)  
**Criteri di accettazione**:
- form_config su events governa quali campi appaiono
- Campi opzionali / obbligatori rispettati lato server

---

### Milestone M-RC16-07 — Commercial Simulator

**Prerequisiti**: M-RC16-03  
**Obiettivo**: strumento admin per testare configurazione pricing  
**File nuovi**: `src/app/admin/events/[id]/pricing-simulator/page.tsx`  
**Autorizzazione**: `direzione` / `super_admin`

---

### Milestone M-RC16-08 — Registration Change Requests

**Prerequisiti**: M-RC16-05  
**Obiettivo**: flusso modifiche post-iscrizione  
**Migration**: 011 (registration_change_requests)

---

### Milestone M-RC16-09 — Event Builder

**Prerequisiti**: M-RC16-05  
**Obiettivo**: CRUD eventi, attività, pricing dall'admin  
**Non blocca early booking**

---

### Milestone M-RC16-10 — Amare Tango 2027

**Prerequisiti**: M-RC16-05 (routing slug-based)  
**Obiettivo**: configurare Amare Tango come secondo evento  
**Contenuto**: seed SQL per Amare Tango + pricing rules + teacher_couples

---

## 32. Percorso critico per early booking

**Scadenza**: 30 settembre 2026 (sistema deve accettare iscrizioni con sconto 20%)

```
M-RC16-01  Schema baseline        [SETTIMANA 1]
     ↓
M-RC16-02  Multi-event routing    [SETTIMANA 2]
     ↓
     ↓ ← ATTESA RISPOSTE ART&TANGO (§30: A1–A4, B1–B3, C1–C5)
     ↓
M-RC16-03  Pricing Engine         [SETTIMANA 3–4]
     ↓
M-RC16-04  Campaign Engine        [SETTIMANA 4]
     ↓
M-RC16-05  Activity-First Form    [SETTIMANA 5–6]
     ↓
     DEPLOY EPICO EARLY BOOKING   [ENTRO SETTIMANA 6 = ~22 agosto 2026]
     (con buffer di 5+ settimane prima della scadenza 30/09)
```

**Milestone non bloccanti per early booking** (da schedulare dopo):
- M-RC16-06 (form fields estesi)
- M-RC16-07 (Commercial Simulator)
- M-RC16-08 (Change Requests)
- M-RC16-09 (Event Builder)
- M-RC16-10 (Amare Tango)

---

## 33. Definition of Done RC1.6

RC1.6 è completa quando:

### Early booking (obbligatorio entro 30/09/2026)
- [ ] Form iscrizione Epico su routing slug-based funzionante
- [ ] Selezione attività senza pacchetti cliccabili
- [ ] Pricing Engine con stage tiers, bundle giornalieri, milonga bundle
- [ ] Campaign Engine con sconto 20% early booking attivo
- [ ] Prezzo calcolato server-side, mai accettato dal client
- [ ] Email di conferma con breakdown prezzi e formule riconosciute
- [ ] TEACHER_CONFIG rimosso dal codice — dati nel DB
- [ ] UUID evento hardcoded rimosso da admin/page.tsx
- [ ] `npm run build` pulita
- [ ] Test unitari Pricing Engine

### Completamento RC1.6
- [ ] Migration baseline 006 allineata alla produzione
- [ ] Routing `/register/[slug]` generalizzato
- [ ] Commercial Simulator disponibile per segreteria
- [ ] Campi partecipante estesi (phone, CF, tessera, ecc.)
- [ ] Registration Change Requests funzionante
- [ ] Amare Tango 2027 configurato e testato
- [ ] Event Builder CRUD base funzionante
- [ ] Ambiguità §30 risolte e documentate
- [ ] ADR aggiornati per decisioni RC1.6

---

## 34. Evoluzione futura del dominio ABRAZO

### Dominio eventi — implementato in RC1.6

| Entità | Stato |
|---|---|
| Organization (single) | RC1.6 — `organization_config` |
| Events | RC1.6 — generalizzati, slug-based |
| Activities | RC1.6 — catalog con categoria e giornata |
| Pricing Engine | RC1.6 — tier + bundle + campagne |
| Registrations | RC1.6 — activity-first, payment ledger |
| Check-in | RC1.5 — funzionante, non modificato in RC1.6 |
| Staff roles | RC1.5 — 4 ruoli, funzionante |

### Futuro dominio Attività Accademiche (RC2.x)

Il dominio comprenderà: corsi annuali, iscrizioni stagionali, presenze lezione, abbonamenti ricorrenti, ruoli leader/follower per coppia, gestione lista allievi.

**Punti di estensione predisposti in RC1.6**:

1. **`activity_prerequisites`** (vuota in RC1.6): consentirà prerequisiti tra corsi e stage
2. **`organization_id` nullable** su events: l'anagrafica organizzazione è già separata
3. **`participants` come entità stabile**: l'anagrafica è già separata dalle iscrizioni; gli allievi di corsi saranno `participants` con relazioni diverse
4. **`event_participant_audit` generico**: il nome "event" è un po' specifico, ma il pattern audit è riusabile; il dominio corsi userà una tabella analoga
5. **`form_config` su events**: il form configurabile vale anche per l'iscrizione a corsi

**Cosa non deve cambiare per introdurre il dominio corsi**:
- La struttura `participants` → immutabile
- Il pattern audit trail → immutabile
- Il sistema QR → riusabile (`ABRAZO:CRS:CODE`)
- Il sistema email → layer astratto già presente

**Cosa dovrà essere aggiunto**:
- Tabella `courses` (diversa da `events` per recurring logic)
- Tabella `course_lessons` (singole lezioni ricorrenti)
- Tabella `course_enrollments` (iscrizione al corso, non al singolo evento)
- Tabella `lesson_attendances` (presenza a singola lezione — analogo a `checkins`)
- Pricing model per abbonamenti (diverso dal pricing activity-first)

**Decisione architetturale**: il dominio Corsi NON condivide le tabelle `events`/`event_participants` anche se ci sono somiglianze superficiali. I due domini hanno semantiche diverse (evento puntuale vs. attività ricorrente) e mixing table sarebbe un anti-pattern. Avranno le proprie tabelle con punti di integrazione sul `participants` e sull'organization.

---

## 35. Principi che il Core ABRAZO non dovrà mai violare

Questa sezione è la **Costituzione del Core ABRAZO**. Ogni proposta di modifica al sistema deve essere valutata contro questi principi. Una modifica che viola un principio richiede prima una revisione esplicita della Costituzione.

---

### C01 — Nessuna logica dipendente dal nome di un'organizzazione

Il codice del Core non contiene mai condizioni del tipo `if (event.slug.startsWith('epico'))` o `if (org === 'art-tango')`. Ogni comportamento specifico di un'organizzazione è ottenuto tramite configurazione (tabelle, `organization_config`, `events.form_config`).

---

### C02 — Nessuna regola commerciale hardcoded nel codice

I prezzi, le soglie, i bundle, le campagne temporali risiedono nel database. Il codice del Pricing Engine è il motore; le tabelle `pricing_stage_tiers`, `pricing_bundles`, `pricing_campaigns` sono il carburante. Modificare una regola commerciale non richiede mai un deploy.

---

### C03 — Nessun calcolo economico nel frontend

Il frontend mostra prezzi e riepilogo. Non li calcola. Non li propone. Non li valida. L'unica fonte di verità è il Pricing Engine server-side. Il client può chiamare `/api/events/[id]/calculate-price` per aggiornare il riepilogo, ma non può mai substituirsi al server nel determinare un importo.

---

### C04 — Nessuna personalizzazione cliente quando esiste una soluzione Core configurabile

Se un requisito di Art&Tango può essere soddisfatto con una configurazione generica, si implementa la soluzione Core e si configura. Non si aggiunge codice specifico per Art&Tango al Core. Questo principio vale anche quando la soluzione Core richiede più tempo — il risparmio futuro supera il costo attuale.

---

### C05 — Ogni differenza tra eventi è ottenibile tramite configurazione

Due eventi possono avere prezzi diversi, attività diverse, form diversi, lingue diverse, branding diverso. Nessuna di queste differenze richiede modifiche al codice. Se una differenza richiede modifiche al codice, significa che la configurabilità non è stata progettata a sufficienza.

---

### C06 — Ogni nuova funzionalità è classificata prima di essere implementata

Prima di iniziare l'implementazione, ogni funzionalità viene classificata come:
- **CORE ABRAZO**: logica generica per qualsiasi organizzatore
- **CORE CONFIGURABILE**: comportamento dipendente dalla configurazione
- **PERSONALIZZAZIONE**: contenuto specifico di un evento/organizzazione

La classificazione guida dove risiede il codice e dove risiedono i dati.

---

### C07 — Il sistema è realmente multi-evento

"Multi-evento" non è un'aspirazione. È una regola verificabile: aggiungere un secondo evento non richiede modifiche al codice. Se aggiungere Amare Tango richiedesse modifiche al codice applicativo, RC1.6 non ha raggiunto il suo obiettivo.

---

### C08 — Il futuro dominio Attività Accademiche non rompe il Core

Ogni decisione architetturale presa in RC1.6 è valutata anche rispetto alla futura introduzione dei corsi. Le fondamenta (participants, audit, QR, email, organization) devono reggere senza refactoring strutturale. I due domini avranno le proprie tabelle e convergeranno solo al livello dell'anagrafica partecipanti e dell'organizzazione.

---

### C09 — Ogni milestone lascia il sistema deployabile, testabile e retrocompatibile

Nessuna milestone lascia il sistema in uno stato inconsistente. Le migration sono idempotenti. I test esistenti continuano a passare. Le iscrizioni RC1.5 rimangono valide dopo ogni migration RC1.6.

---

### C10 — Il Blueprint è la fonte autorevole delle decisioni architetturali

Qualsiasi modifica a una decisione documentata in questo Blueprint richiede prima un aggiornamento del Blueprint, con motivazione esplicita. Non esistono "eccezioni temporanee" non documentate. Il codice implementa ciò che il Blueprint prescrive; se il codice devia, o il Blueprint è sbagliato (va aggiornato) o il codice è sbagliato (va corretto).

---

### C11 — La privacy è progettata dentro al sistema, non aggiunta sopra

Il QR code non contiene mai dati personali. I campi del form raccolgono solo ciò che è strettamente necessario per la funzione specifica (minimizzazione GDPR). Ogni nuovo campo ha una motivazione documentata. Il consenso ha sempre boolean + timestamp separati. L'audit trail è immutabile per design.

---

### C12 — Il bilingualismo è un requisito di primo ordine

Ogni contenuto rivolto ai partecipanti nasce bilingue (IT/EN). La lingua è un dato dell'iscrizione (`registration_language`), non un'opzione di visualizzazione. Ogni nuovo template email, ogni nuovo messaggio operativo, ogni nuovo testo nel form è progettato bilingue dall'inizio.

---

## 36. Exit Criteria & Acceptance RC1.6

Questa sezione definisce i criteri oggettivi che permettono di dichiarare conclusa la RC1.6 e autorizzarne l'utilizzo in produzione.

L'obiettivo non è soltanto completare le milestone tecniche, ma dimostrare che il sistema è realmente utilizzabile dalla segreteria e dalla direzione senza interventi degli sviluppatori.

### 36.1 Technical Exit Criteria

Prima del rilascio devono essere soddisfatti tutti i seguenti requisiti:

- tutte le migration RC1.6 eseguibili da zero senza errori;
- build (`npm run build`) completata senza warning bloccanti;
- test unitari del Pricing Engine superati;
- test di regressione RC1.5 superati;
- nessun UUID o slug hardcoded residuo;
- nessun contenuto Art&Tango hardcoded nel Core;
- tutte le API documentate e funzionanti;
- documentazione tecnica aggiornata.

---

### 36.2 Business Exit Criteria

La direzione Art&Tango dovrà validare:

- correttezza dei prezzi;
- correttezza degli sconti;
- correttezza dei suggerimenti commerciali;
- correttezza del calcolo degli acconti;
- correttezza delle formule commerciali riconosciute;
- correttezza delle email inviate;
- correttezza del flusso di segreteria.

La validazione avverrà utilizzando esclusivamente il sistema, senza modifiche manuali al database.

---

### 36.3 User Acceptance Test (UAT)

Prima del rilascio definitivo dovrà essere svolto un periodo di simulazione operativa utilizzando dati realistici.

Le prove comprenderanno almeno:

- iscrizioni singole;
- iscrizioni in coppia;
- acquisto di stage;
- acquisto di milonghe;
- formule giornaliere;
- early booking;
- modifiche post-iscrizione;
- conferma pagamenti;
- check-in;
- esportazioni;
- QR Code.

Ogni anomalia verrà classificata come:

- Bloccante
- Maggiore
- Minore
- Miglioramento

Solo le anomalie bloccanti impediscono il rilascio.

---

### 36.4 Production Readiness

ABRAZO RC1.6 è considerata Production Ready quando:

- tutti gli Exit Criteria sono soddisfatti;
- la direzione Art&Tango approva il sistema;
- il periodo di simulazione viene completato con esito positivo;
- il sistema è pronto per l'apertura dell'Early Booking.

Da questo momento RC1.6 diventa la baseline ufficiale per tutti gli sviluppi successivi.

Le evoluzioni future dovranno essere implementate tramite nuove Release Candidate senza modificare retroattivamente le decisioni architetturali approvate in questo Blueprint.

---

*Fine Blueprint ABRAZO RC1.6 — Versione 1.0.0*

*Questo documento è normativo. Ogni decisione di implementazione che non trova riscontro in questo Blueprint deve essere proposta come aggiornamento del Blueprint prima di essere implementata nel codice.*
