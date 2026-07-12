# SEC-001 — Supabase Security Hardening Plan

**Versione**: 1.0  
**Data**: Luglio 2026  
**Autore**: Responsabile tecnico ABRAZO  
**Stato**: Piano approvato — esecuzione incrementale

> **Regola operativa**: non applicare modifiche massive al database prima di una demo o di un deploy in produzione. Ogni step è indipendente e reversibile. Applicare uno step alla volta, verificare, procedere.

---

## 1. Alert ricevuti dal Supabase Security Advisor

Il Security Advisor di Supabase ha segnalato tre categorie di alert sul database di ABRAZO.

### 1.1 `security_definer_view` (13 viste)

Viste coinvolte:
- `vw_event_registrations`
- `vw_event_roles`
- `vw_confirmed_couples`
- `vw_unpaired_participants`
- `vw_payment_status`
- `vw_outstanding_balances`
- `vw_session_registrations`
- `vw_session_capacity`
- `vw_package_catalog`
- `vw_teacher_sessions`
- `vw_event_checkins`
- `vw_session_checkins`
- `vw_event_dashboard`

Tutte definite in `supabase/migrations/001_init_abrazo_schema.sql`.

### 1.2 `rls_disabled_in_public` (6 tabelle)

Tabelle coinvolte:
- `events`
- `event_sessions`
- `session_teachers`
- `package_items`
- `couples`
- `packages`

### 1.3 `sensitive_columns_exposed` (3 colonne)

- `events.iban`
- `package_items.session_id`
- `session_teachers.session_id`

---

## 2. Rischio: SECURITY DEFINER sulle viste

**Cosa significa**: in PostgreSQL, una vista con `SECURITY DEFINER` (il default) viene eseguita con i privilegi dell'utente che l'ha creata (tipicamente `postgres`), non con quelli del chiamante. Questo bypassa completamente Row Level Security (RLS).

**Impatto pratico**: se un client con la chiave anonima chiama `GET /rest/v1/vw_event_registrations`, la vista restituisce TUTTI i record, perché esegue come `postgres` che ignora RLS. Anche se avessimo policy RLS restrittive sulle tabelle sottostanti, le viste con SECURITY DEFINER le aggirano.

**Contesto ABRAZO**: le 13 viste non vengono mai chiamate dal codice Next.js (confermato con grep: zero occorrenze di `from("vw_`). Esistono per uso diretto via Supabase Studio o API REST. Il rischio è quindi su accesso diretto all'API Supabase con la chiave anonima, non sull'applicazione.

**Fix**: ricreare le viste con `WITH (security_invoker = true)` — eseguono con i privilegi del chiamante, rispettano RLS.

---

## 3. Rischio: RLS disabilitata sulle 6 tabelle

**Cosa significa**: senza Row Level Security, qualsiasi richiesta con la chiave anonima su `GET /rest/v1/events` (o qualsiasi altra tabella) restituisce tutti i record. Non esiste filtro di accesso a livello di database.

**Impatto pratico per tabella**:

| Tabella | Dato esposto senza RLS | Livello rischio |
|---|---|---|
| `events` | Nome, date, IBAN, IBAN beneficiario, coordinate bancarie | **Alto** |
| `packages` | Prezzi, sconti, struttura commerciale | Medio |
| `event_sessions` | Programma, capacità, prezzi | Basso |
| `session_teachers` | Associazione session↔maestro | Basso |
| `package_items` | Struttura interna pacchetti | Basso |
| `couples` | Coppie leader/follower confermate | Medio |

**Contesto ABRAZO**: il codice Next.js usa il client anon in due soli file:
1. `src/app/register/[eventId]/page.tsx` — forma pubblica legacy, legge `events`, `event_sessions`, `packages`
2. `src/app/admin/events/page.tsx` — lista eventi admin, legge `events` (**da correggere**)

Tutti gli altri file usano `supabaseAdmin` (service_role), che bypassa RLS per design.

---

## 4. Rischio specifico: `events.iban`

**Perché è un alert separato**: anche con RLS abilitata e una policy SELECT per anon, se la policy è `USING (true)` o `USING (is_active = true)`, il client anon legge TUTTE le colonne della tabella — incluse le colonne finanziarie come `iban`, `beneficiary`, `payment_notes`.

**Scenario di abuso**: un chiunque con la chiave anonima (che è pubblica, inclusa nel JavaScript del browser) può chiamare:
```
GET /rest/v1/events?select=iban,beneficiary
```
e ottenere le coordinate bancarie dell'Associazione.

**Contesto ABRAZO**: `events.iban` è letto solo da:
- `src/app/register/epico-tango-fest-2027/page.tsx` → usa `supabaseAdmin` (server-side, sicuro)
- `src/app/admin/events/[id]/page.tsx` → usa `supabaseAdmin` (sicuro)

Il client anon **non ha mai bisogno di leggere l'IBAN**.

**Fix**: dopo aver abilitato RLS su `events` e aggiunto una policy SELECT per anon (necessaria per il form legacy), revocare il privilegio colonna-livello: `REVOKE SELECT (iban, beneficiary, payment_notes) ON events FROM anon`.

---

## 5. Distinzione dati pubblici / dati amministrativi

### Dati che il client anon DEVE poter leggere

Necessari per il funzionamento del form di registrazione legacy (`/register/[eventId]/`):

| Tabella | Colonne necessarie | Condizione |
|---|---|---|
| `events` | `id`, `name` | `is_active = true` |
| `event_sessions` | `id`, `title`, `session_type`, `description`, `location`, `starts_at`, `ends_at`, `price` | `is_bookable = true` |
| `packages` | `id`, `name`, `description`, `price`, `deposit_amount` | `is_public = true AND is_active = true` |

Il form Epico Tango Fest 2027 usa già `supabaseAdmin` — non dipende dal client anon.

### Dati che devono essere INACCESSIBILI al client anon

| Tabella | Motivo |
|---|---|
| `events.iban`, `.beneficiary`, `.payment_notes` | Coordinate bancarie dell'Associazione |
| `session_teachers` | Struttura interna evento — nessun form pubblico la usa |
| `package_items` | Struttura interna pacchetti — nessun form pubblico la usa |
| `couples` | Coppie leader/follower — dato personale, solo admin |
| `vw_event_registrations` e tutte le viste | Dati partecipanti, pagamenti, check-in |

---

## 6. Strategia di hardening incrementale

La migration `003_DRAFT_rls_security_hardening.sql` esiste come bozza completa ma **non va applicata in blocco**. Il rischio di un'applicazione massiva prima di test completi è troppo alto: una policy sbagliata può bloccare il form pubblico di iscrizione.

### Step A — Fix applicativo (nessun SQL, nessun rischio)

**Cosa**: sostituire `supabase` con `supabaseAdmin` in `src/app/admin/events/page.tsx`.  
**Perché ora**: è una correzione di codice senza dipendenze da Supabase. Elimina subito l'unico uso non intenzionale del client anon in area admin.  
**Rischio**: zero. `supabaseAdmin` è già usato in tutte le altre pagine admin.  
**Stato**: **completato** in questa iterazione (SEC-001 v1.0).

### Step B — Security Invoker sulle viste (basso rischio)

**Cosa**: ricreare le 13 viste con `WITH (security_invoker = true)`.  
**Perché**: le viste non sono usate dall'app Next.js → nessun rischio di regressione applicativa.  
**Rischio**: basso. L'unico impatto è su query dirette a Supabase Studio o API REST eseguita da un client anon. Il service_role (usato dal codice) non è mai impattato.  
**Test richiesto**: verificare che le viste esistano ancora e restituiscano dati corretti via Supabase Studio con un client admin.  
**File da creare**: `supabase/migrations/003_step_b_security_invoker_views.sql`

### Step C — Abilitazione RLS sulle 3 tabelle admin-only (basso rischio)

**Cosa**: `ALTER TABLE session_teachers ENABLE ROW LEVEL SECURITY`, idem per `package_items` e `couples`. Nessuna policy anon.  
**Perché**: queste tabelle non sono mai lette dal client anon → abilitare RLS senza policy blocca solo l'accesso diretto non autenticato, senza toccare il codice.  
**Rischio**: basso. Il service_role bypassa RLS → codice admin invariato.  
**Test richiesto**: verificare che le dashboard admin continuino a caricare dati.  
**File da creare**: `supabase/migrations/003_step_c_rls_admin_tables.sql`

### Step D — Policy SELECT pubbliche per events, event_sessions, packages (rischio medio)

**Cosa**: abilitare RLS su `events`, `event_sessions`, `packages` e aggiungere policy anon minime.  
**Perché**: necessario per proteggere i dati ma mantenere il form legacy funzionante.  
**Rischio**: **medio**. Una policy sbagliata rompe `/register/[eventId]/`. Va testato su staging prima di applicare in produzione.  
**Test richiesto**: aprire il form legacy, verificare che eventi, sessioni e pacchetti si carichino.  
**File da creare**: `supabase/migrations/003_step_d_rls_public_tables.sql`

### Step E — Protezione colonne sensibili events.iban (rischio basso, dipende da Step D)

**Cosa**: `REVOKE SELECT (iban, beneficiary, payment_notes) ON events FROM anon`.  
**Perché**: rimuove l'esposizione delle coordinate bancarie tramite API pubblica.  
**Dipendenza**: deve essere applicato dopo Step D (RLS già attiva su events).  
**Rischio**: basso. Solo il client anon perde accesso a queste colonne. Il service_role è immune.  
**Test richiesto**: `curl` con chiave anon su `/rest/v1/events?select=iban` deve restituire errore o campo vuoto.  
**File da creare**: `supabase/migrations/003_step_e_revoke_sensitive_columns.sql`

---

## 7. Test manuali dopo ogni step

### Dopo Step A (fix applicativo)
- [ ] `npm run build` passa senza errori TypeScript
- [ ] `grep -r "from \"@/lib/supabase\"" src/app/admin/` → zero risultati (o solo file non-admin)
- [ ] La pagina `/admin/events` si carica e mostra la lista eventi

### Dopo Step B (security invoker views)
- [ ] Le 13 viste esistono ancora in Supabase Studio (Table Editor → Views)
- [ ] Query diretta in SQL Editor con role `postgres`: ogni vista restituisce dati corretti
- [ ] `GET /rest/v1/vw_event_registrations` con chiave anon → array vuoto (0 righe, nessun dato esposto)

### Dopo Step C (RLS admin tables)
- [ ] Dashboard admin evento si carica normalmente (pacchetti, attività, coppie maestri)
- [ ] `GET /rest/v1/session_teachers` con chiave anon → array vuoto
- [ ] `GET /rest/v1/package_items` con chiave anon → array vuoto
- [ ] `GET /rest/v1/couples` con chiave anon → array vuoto

### Dopo Step D (RLS public tables)
- [ ] `/register/[uuid-evento]` carica evento, sessioni e pacchetti
- [ ] `/register/epico-tango-fest-2027` carica normalmente (usa supabaseAdmin, non dipende da RLS)
- [ ] Dashboard admin evento si carica (supabaseAdmin bypassa RLS)
- [ ] `GET /rest/v1/events` con chiave anon → solo eventi `is_active=true`
- [ ] `GET /rest/v1/event_sessions` con chiave anon → solo sessioni `is_bookable=true`
- [ ] `GET /rest/v1/packages` con chiave anon → solo pacchetti `is_public=true AND is_active=true`

### Dopo Step E (colonne sensibili)
- [ ] `GET /rest/v1/events?select=iban` con chiave anon → errore 403 o campo assente
- [ ] `GET /rest/v1/events?select=id,name` con chiave anon → funziona (solo campi non sensibili)
- [ ] Pagina Epico si carica ancora (legge iban via supabaseAdmin — non impattato)
- [ ] Email conferma iscrizione include ancora IBAN corretto (server-side, non impattato)

### Verifica finale — Supabase Security Advisor
- [ ] Rieseguire Security Advisor dopo tutti gli step
- [ ] Zero alert `security_definer_view`
- [ ] Zero alert `rls_disabled_in_public` per le 6 tabelle
- [ ] Zero alert `sensitive_columns_exposed` per `events.iban`

---

## 8. Raccomandazione: non applicare prima della demo

**Regola**: gli Step B–E modificano il comportamento del database Supabase in produzione. Qualsiasi errore in una policy RLS può bloccare il form pubblico di iscrizione durante una demo o un evento reale.

**Sequenza raccomandata**:

1. **Ora** → Solo Step A (fix codice, zero SQL)
2. **Prima del deploy di staging** → Step B + Step C (basso rischio, nessun impatto sull'app)
3. **Su staging verificato** → Step D (testa il form legacy con policy RLS)
4. **Dopo test completi su staging** → Step E
5. **In produzione** → applicare in sequenza A→B→C→D→E, con verifica tra ogni step

**Non fare**: applicare la bozza `003_DRAFT_rls_security_hardening.sql` direttamente in produzione. È un documento di riferimento, non uno script pronto all'uso.

---

## 9. File di riferimento

| File | Ruolo |
|---|---|
| `supabase/migrations/001_init_abrazo_schema.sql` | Schema originale con le 13 viste e le 6 tabelle flaggate |
| `supabase/migrations/002_email_template_overrides.sql` | Tabella `email_templates` — anch'essa senza RLS (non nell'alert, ma a rischio) |
| `supabase/migrations/003_DRAFT_rls_security_hardening.sql` | Bozza completa dell'hardening — **non applicare in blocco** |
| `src/app/register/[eventId]/page.tsx` | Unico form pubblico che usa client anon su tabelle flaggate |
| `src/app/admin/events/page.tsx` | **Corretto in Step A** — migrato a supabaseAdmin |
| `docs/04_GDPR_AND_SECURITY.md` | Documento GDPR di riferimento del progetto |

---

*ABRAZO Security Operations — SEC-001 v1.0 — Luglio 2026*
