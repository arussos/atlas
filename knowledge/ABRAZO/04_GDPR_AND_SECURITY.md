# 04 — GDPR e Sicurezza

**Versione**: 1.0.0 | **Progetto**: ABRAZO MVP 0.9.0 | **Aggiornato**: Giugno 2026

---

## Indice

1. [Premessa: GDPR come requisito progettuale](#1-premessa-gdpr-come-requisito-progettuale)
2. [Principi GDPR applicati](#2-principi-gdpr-applicati)
3. [Minimizzazione dei dati](#3-minimizzazione-dei-dati)
4. [QR Code non parlante](#4-qr-code-non-parlante)
5. [Consensi e tracciamento](#5-consensi-e-tracciamento)
6. [Audit delle operazioni](#6-audit-delle-operazioni)
7. [Cancellazione e diritto all'oblio](#7-cancellazione-e-diritto-alloblio)
8. [Export controllati](#8-export-controllati)
9. [Conservazione dei dati](#9-conservazione-dei-dati)
10. [Sicurezza tecnica](#10-sicurezza-tecnica)
11. [Autenticazione admin — priorità critica](#11-autenticazione-admin--priorità-critica)
12. [Supabase RLS — stato attuale e futuro](#12-supabase-rls--stato-attuale-e-futuro)
13. [Storage QR e valutazione signed URL](#13-storage-qr-e-valutazione-signed-url)
14. [Fornitori e servizi esterni](#14-fornitori-e-servizi-esterni)

---

## 1. Premessa: GDPR come requisito progettuale

La conformità al Regolamento Generale sulla Protezione dei Dati (GDPR — Regolamento UE 2016/679) non è una funzionalità da aggiungere a ABRAZO: è un **requisito progettuale fondamentale**.

Art&Tango raccoglie dati personali di persone fisiche (partecipanti ai propri eventi), il che la qualifica come **titolare del trattamento** ai sensi dell'Art. 4 GDPR. ABRAZO è lo strumento tecnico attraverso il quale avviene questo trattamento.

Ogni nuova funzionalità di ABRAZO deve essere valutata alla luce dei principi descritti in questo documento **prima** dell'implementazione.

### Categorie di dati trattati

| Categoria | Esempi | Base legale |
|---|---|---|
| Dati identificativi | Nome, cognome, email | Esecuzione contratto (iscrizione evento) |
| Dati comportamentali | Attività scelte, ruolo, check-in | Esecuzione contratto |
| Dati di preferenza | Lingua scelta | Legittimo interesse |
| Dati di consenso | Timestamp accettazione privacy/termini/media | Adempimento obblighi legali (GDPR) |

---

## 2. Principi GDPR applicati

### Liceità, correttezza, trasparenza

Il partecipante è informato del trattamento al momento dell'iscrizione tramite la privacy notice. Il consenso è esplicito e separato dagli altri campi.

### Limitazione della finalità

I dati raccolti durante l'iscrizione sono usati esclusivamente per:
- Gestione dell'iscrizione all'evento specifico
- Comunicazioni relative all'evento
- Check-in fisico all'evento
- Adempimenti amministrativi dell'Associazione

Non vengono usati per profilazione commerciale, cessioni a terzi, né finalità diverse da quelle dichiarate.

### Minimizzazione

Raccogliere solo ciò che è necessario (vedi sezione [3](#3-minimizzazione-dei-dati)).

### Esattezza

I dati anagrafici sono inseriti dall'interessato stesso. La modifica post-iscrizione è prevista nella roadmap.

### Limitazione della conservazione

Definire una policy di conservazione (vedi sezione [9](#9-conservazione-dei-dati)).

### Integrità e riservatezza

Protezione tecnica mediante separazione client/admin Supabase, HTTPS, variabili d'ambiente per le credenziali.

### Responsabilizzazione (accountability)

Audit trail completo, consensi con timestamp, documentazione tecnica di questo documento.

---

## 3. Minimizzazione dei dati

### Cosa viene raccolto e perché

| Dato | Finalità | Necessario? |
|---|---|---|
| Nome e cognome | Identificazione, comunicazioni, check-in | Sì |
| Email | Comunicazioni, invio conferma | Sì |
| Ruolo (leader/follower) | Bilanciamento ruoli in sala, statistica | Sì |
| Lingua | Comunicazioni in lingua corretta | Sì |
| Pacchetti e attività scelte | Gestione evento, verifica prenotazione al check-in | Sì |
| Consensi + timestamp | Adempimento GDPR, prova del consenso | Sì |

### Cosa NON viene raccolto (e non deve essere aggiunto senza valutazione)

- Data di nascita
- Numero di telefono
- Indirizzo fisico
- Nazionalità / documento d'identità
- Informazioni di pagamento (carte di credito, IBAN del partecipante)
- Dati biometrici
- Dati di salute
- Preferenze religiose o politiche

> **Regola**: se si intende raccogliere un nuovo dato non presente nell'elenco sopra, documentare la finalità specifica, la base legale e la necessità prima di implementarlo.

---

## 4. QR Code non parlante

Questa è una delle scelte architetturali più importanti dal punto di vista GDPR.

### Il payload è opaco

Il QR code generato da ABRAZO contiene **solo** la stringa `ABRAZO:EVP:EVP-XXXXXX`.

- Non contiene nome, cognome, email, ruolo, né alcun dato personale
- Non contiene importi pagati o stato del pagamento
- Non contiene dati relativi alle attività prenotate

### Perché è importante

Chiunque fotografasse o scansionasse il QR di un partecipante (ad esempio uno sconosciuto in sala con un'app qualsiasi) otterrebbe solo una stringa opaca senza alcun valore informativo.

La risoluzione del codice in dati personali avviene **esclusivamente server-side**, tramite lookup autenticato nel database. Senza accesso alle API di ABRAZO, il QR code è inutile.

### Confronto con approcci alternativi da evitare

| Approccio | Rischio GDPR |
|---|---|
| QR con nome nel payload | Dato personale esposto a chiunque scansioni |
| QR con UUID database nel payload | Guida direttamente alla riga DB — rischio se le API non sono protette |
| QR con email nel payload | Dato personale esposto |
| **ABRAZO: codice opaco** | **Nessun dato personale esposto** ✓ |

### Il QR non contiene stato del pagamento — questo è intenzionale

Il payload non include importi, stato di pagamento o ricevute. Questa separazione ha una doppia motivazione:

**Tecnica**: lo stato del pagamento cambia nel tempo (pending → deposit → paid). Un QR che incorporasse questo dato diventerebbe obsoleto o richiederebbe rigenerazione a ogni transizione.

**GDPR**: lo stato di pagamento è un dato finanziario personale. Incorporarlo nel QR lo esporrebbe a chiunque lo scansionasse — in una sala affollata, un QR "leggibile" con dati finanziari è un rischio.

La verifica del pagamento avviene **esclusivamente server-side** al momento del check-in: l'API restituisce `payment_status` allo staff autenticato, che ha la facoltà di agire di conseguenza (consentire l'ingresso o indirizzare alla Segreteria). Il QR rimane un identificatore puro.

---

## 5. Consensi e tracciamento

### Tre consensi separati

Al momento dell'iscrizione vengono presentati tre consensi distinti, ciascuno con la propria checkbox:

1. **Privacy notice** (`privacy_accepted`): obbligatorio. Informativa sul trattamento dati personali per la gestione dell'iscrizione e dell'evento.

2. **Regolamento evento** (`terms_accepted`): obbligatorio. Accettazione delle regole e condizioni dell'evento specifico.

3. **Media release** (`media_accepted`): facoltativo (raccomandato di verificare con il legale di Art&Tango). Consenso all'utilizzo di foto e video in cui il partecipante potrebbe comparire durante l'evento.

### Tracciamento con timestamp

Ogni consenso ha un campo timestamp corrispondente (`_at`) che registra il momento esatto dell'accettazione. Questo è fondamentale per:

- Dimostrare **quando** il consenso è stato dato
- Dimostrare che il consenso è stato dato **prima** del trattamento dei dati
- Rispondere a eventuali contestazioni

### Visibilità dei consensi

I consensi e i loro timestamp sono visibili:
- Nella scheda partecipante nell'area admin (per consultazione staff)
- Nell'email di conferma inviata al partecipante (riepilogo consensi accettati)
- Nell'export Excel (colonne dedicate)

### Cosa NON fare

- Non raggruppare tutti e tre i consensi in un'unica checkbox generica ("Ho letto e accetto tutto")
- Non pre-selezionare le checkbox
- Non rendere obbligatorio il consenso media se non lo è per legge

---

## 6. Audit delle operazioni

La tabella `event_participant_audit` è il registro delle operazioni sui dati personali. Ogni riga documenta chi ha fatto cosa e quando.

### Operazioni attualmente tracciate

| Operazione | `event_type` |
|---|---|
| Nuova iscrizione | `registration_created` |
| Cambio stato pagamento | `payment_status_changed` |
| Check-in evento | `event_checkin_completed` |
| Check-in attività | `activity_checkin_completed` |

### Operazioni future da tracciare

| Operazione | `event_type` da usare |
|---|---|
| Modifica iscrizione | `registration_updated` |
| Cancellazione iscrizione | `registration_cancelled` |
| Anonimizzazione GDPR | `gdpr_data_erasure` |
| Export dati scaricato | `data_export_executed` |
| Login admin | `admin_login` |

### Regola immutabile

I record di audit **non devono mai essere modificati o eliminati**. In caso di errore, si aggiunge un record correttivo con riferimento al precedente, non si modifica quello sbagliato.

### Limite attuale: operatore fittizio

Il campo `operator_name` è attualmente valorizzato con `"staff-demo"`. Quando sarà implementata l'autenticazione, questo campo dovrà essere popolato con l'identità reale dell'operatore (email o username).

---

## 7. Cancellazione e diritto all'oblio

### Stato attuale

La procedura di cancellazione dati non è ancora implementata in MVP 0.9.0.

### Approccio previsto: anonimizzazione

La **cancellazione fisica** del record è sconsigliata perché:
- Romperebbe l'integrità referenziale (checkins, audit trail)
- Impedirebbe la produzione di statistiche aggregate accurate
- Potrebbe violare obblighi contabili/fiscali se correlata a pagamenti

L'approccio corretto è la **anonimizzazione**:

```sql
-- Esempio (non implementato)
UPDATE participants
SET
  first_name = '[ANONIMIZZATO]',
  last_name = '[ANONIMIZZATO]',
  email = 'anonimizzato-' || id || '@deleted.invalid'
WHERE id = ?;
```

### Cosa conservare dopo l'anonimizzazione

| Dato | Conservare? | Motivazione |
|---|---|---|
| Dati anagrafici | No → anonimizzare | Diritto all'oblio |
| `privacy_accepted_at` | Sì | Prova del trattamento |
| `terms_accepted_at` | Sì | Prova del trattamento |
| `media_accepted_at` | Sì | Prova del trattamento |
| Record `event_participant_audit` | Sì | Registro operazioni |
| Record `checkins` | Sì (senza link a PII) | Statistica presenze |
| Dati aggregati economici | Sì | Obblighi contabili |

### Da implementare

- Funzione di anonimizzazione accessibile all'admin
- Conferma con password (double-check)
- Audit record `gdpr_data_erasure`
- Email di conferma cancellazione all'interessato

---

## 8. Export controllati

### Situazione attuale

L'export Excel è accessibile tramite link nell'area admin senza ulteriori controlli. Contiene dati personali di tutti i partecipanti.

### Principi da applicare

- L'export deve essere accessibile **solo da utenti autenticati** con ruolo appropriato
- Ogni download di dati deve essere **loggato** in audit (`data_export_executed`)
- Il file esportato deve essere trattato con la stessa riservatezza dei dati nel sistema
- Non condividere file export via canali non sicuri (email non cifrata, link pubblici, ecc.)

### Evoluzione prevista

- Autenticazione con ruolo `admin` o `segreteria` per accedere all'export
- Log automatico dell'export nell'audit trail
- Possibile limitazione: export filtrato per periodo o per stato (es. solo confirmed)

---

## 9. Conservazione dei dati

### Situazione attuale

Non è definita una policy formale di conservazione dei dati. I dati dei partecipanti rimangono nel database indefinitamente.

### Principi GDPR

Il GDPR richiede che i dati personali non siano conservati più a lungo del necessario per le finalità del trattamento.

### Policy consigliata (da validare con legale Art&Tango)

| Tipo di dato | Periodo di conservazione suggerito |
|---|---|
| Dati anagrafici (`participants`) | 3 anni dall'ultimo evento partecipato |
| Dati iscrizione (`event_participants`) | 3 anni dall'evento |
| Dati pagamento | 10 anni (obblighi fiscali/contabili) |
| Audit trail | 5 anni |
| Consensi + timestamp | 5 anni (prova del trattamento) |
| QR PNG storage | Eliminare entro 1 anno dall'evento |

> **Da fare**: definire formalmente la policy con il Presidente di Art&Tango e/o un consulente legale, poi implementarla come job schedulato o procedura manuale annuale.

---

## 10. Sicurezza tecnica

### HTTPS

Tutte le comunicazioni avvengono su HTTPS. Vercel fornisce TLS automatico. Non è possibile accedere all'applicazione in HTTP.

### Variabili d'ambiente

Tutte le credenziali (chiavi Supabase, chiave Resend) sono in variabili d'ambiente e non compaiono mai nel codice sorgente. Il file `.env.local` non è committato nel repository (da verificare nel `.gitignore`).

### Service role key

La `SUPABASE_SERVICE_ROLE_KEY` non compare mai nel bundle client-side. È usata esclusivamente in:
- `src/lib/supabaseAdmin.ts` (importato solo in server-side code)
- API Routes
- Server Components

Qualsiasi violazione di questa regola costituisce una vulnerabilità critica.

### Validazione input

Le API Routes validano i campi obbligatori prima di eseguire operazioni sul DB. Non esiste SQL injection risk perché Supabase SDK usa query parametrizzate.

### Nessun dato personale negli URL

- Il codice `EVP-XXXXXX` nell'URL della pagina success non è un dato personale (è un identificatore opaco)
- Non compaiono mai nome, email o altri dati personali in URL o query string

---

## 11. Autenticazione admin — priorità critica

### Situazione attuale

**L'area admin (`/admin/*`) è completamente priva di autenticazione.**

Chiunque conosca l'URL `https://abrazo.app/admin` può:
- Vedere nomi, email e dati di tutti i partecipanti
- Modificare lo stato dei pagamenti
- Fare check-in a nome di qualsiasi partecipante
- Scaricare l'export Excel con tutti i dati personali

Questo è il **rischio di sicurezza e GDPR più critico** del progetto, e il principale blocco al deploy in produzione con dati reali.

### Soluzione prevista: Supabase Auth

L'implementazione prevista usa Supabase Auth (già incluso nel piano attuale di Supabase):

1. **Login email + password** (o magic link) per lo staff
2. **Middleware Next.js** che protegge tutte le route `/admin/*`
3. **Ruoli** gestiti tramite tabella `user_roles` o metadata utente Supabase:
   - `admin`: accesso completo (direzione Art&Tango)
   - `staff`: segreteria, pagamenti, schede partecipanti
   - `checkin`: solo scanner QR, senza accesso ai dati
4. **Row Level Security** su Supabase per enforcement lato database
5. **Identità operatore** nei check-in e nell'audit trail (`checked_in_by = auth.email`)

### Priorità di implementazione

1. Auth basic (login/logout) → protegge tutti i dati
2. Ruolo `checkin` → consente al personale di check-in l'uso del scanner senza accesso ai dati
3. Ruolo `staff` vs `admin` → separazione responsabilità
4. RLS Supabase → enforcement lato DB (defense in depth)

---

## 12. Supabase RLS — stato attuale e futuro

### Stato attuale

La Row Level Security di Supabase **potrebbe non essere configurata** sulle tabelle principali. Il client admin (service role key) bypassa la RLS per definizione, quindi l'applicazione funziona correttamente anche senza RLS configurata.

> **Da verificare**: lo stato delle policy RLS nel progetto Supabase.

### Configurazione prevista con Auth

Quando sarà implementata l'autenticazione, la RLS dovrà essere configurata per:

- Consentire la **lettura di eventi pubblici** (`events.is_public = true`) senza autenticazione
- Consentire la **creazione di iscrizioni** senza autenticazione (flusso pubblico)
- Richiedere autenticazione per **tutte le query admin** (partecipanti, checkin, pagamenti)
- Limitare le operazioni di scrittura ai ruoli appropriati

---

## 13. Storage QR e valutazione signed URL

### Situazione attuale

I PNG dei QR code sono salvati nel bucket Supabase Storage `registration-qr`. L'URL usato per visualizzare il QR è probabilmente un **URL pubblico permanente**.

### Rischio

Un URL pubblico permanente significa che:
- Chiunque conosca (o indovini) l'URL può scaricare il QR di qualsiasi partecipante
- Il QR stesso non contiene dati personali (è opaco), ma la sua accessibilità pubblica potrebbe essere considerata una non conformità GDPR
- Il path prevedibile (`events/{event_id}/event-participants/{participant_id}.png`) riduce l'entropia di sicurezza

### Soluzione consigliata: signed URL con scadenza

Supabase Storage supporta la generazione di URL firmati con scadenza temporale:

```typescript
const { data } = await supabaseAdmin.storage
  .from("registration-qr")
  .createSignedUrl(path, 3600)  // scade in 1 ora
```

Un signed URL è:
- Valido solo per un periodo limitato (es. 1 ora per la visualizzazione nella pagina success)
- Non indovinabile (contiene un token crittografico)
- Revocabile (il bucket può essere reso privato)

### Compromesso

I signed URL richiedono una chiamata server-side per essere generati a ogni visualizzazione. Per i QR nelle email (che devono rimanere accessibili per giorni/settimane), servono URL con scadenza molto lunga o URL pubblici. Questa è una decisione da valutare con attenzione.

---

## 14. Fornitori e servizi esterni

ABRAZO è costruito su servizi esterni. Ogni servizio è un **sub-responsabile del trattamento** ai sensi del GDPR: Art&Tango deve assicurarsi che i DPA (Data Processing Agreement) siano in essere.

### Supabase

| Aspetto | Dettaglio |
|---|---|
| **Ruolo** | Backend principale: database, storage |
| **Dati trattati** | Tutti i dati personali dei partecipanti |
| **Hosting** | AWS (regione da verificare — preferibile EU West) |
| **DPA** | Disponibile e da sottoscrivere tramite dashboard Supabase |
| **Piano attuale** | Free tier (sufficiente per MVP) |
| **Motivazione scelta** | BaaS completo, SDK TypeScript maturo, piano gratuito generoso, integrazione auth/storage/realtime, rapidità di sviluppo |
| **Sostituibilità** | Alta — PostgreSQL standard, storage S3-compatible. Migrazione possibile a Neon, PlanetScale, AWS RDS + S3 se necessario. |

### Vercel

| Aspetto | Dettaglio |
|---|---|
| **Ruolo** | Deploy, hosting, CDN, Edge Functions |
| **Dati trattati** | Log di accesso (IP, user agent), nessun dato applicativo |
| **Hosting** | AWS / Cloudflare Edge (globale) |
| **DPA** | Disponibile tramite Vercel dashboard |
| **Piano attuale** | Hobby/Pro (da verificare) |
| **Motivazione scelta** | Deploy zero-config per Next.js, preview automatiche per ogni branch, SSL gratuito |
| **Sostituibilità** | Alta — Next.js può girare su qualsiasi provider Node.js (Railway, Fly.io, AWS EC2, self-hosted) |

### Resend

| Aspetto | Dettaglio |
|---|---|
| **Ruolo** | Invio email transazionale (conferme iscrizione) |
| **Dati trattati** | Email dei partecipanti, contenuto delle email |
| **Hosting** | AWS SES come infrastruttura sottostante |
| **DPA** | Disponibile |
| **Piano attuale** | Free tier (100 email/giorno) |
| **Motivazione scelta** | API semplice, deliverability affidabile, dashboard tracking aperture/bounce, costo zero per MVP |
| **Sostituibilità** | **Alta e intenzionale** — il layer astratto `emailService.ts` isola l'applicazione dall'SDK Resend. La sostituzione con SMTP, Amazon SES, SendGrid, Mailgun o Postmark richiede la modifica di un solo file (`emailService.ts`), senza toccare le API Routes né i template. |

### Nota sul sender email

Attualmente il sender è `onboarding@resend.dev`. Prima del deploy in produzione è necessario:
1. Configurare un dominio proprio su Resend (es. `noreply@artango.it` o `iscrizioni@abrazo.app`)
2. Aggiungere i record DNS (SPF, DKIM) sul dominio
3. Aggiornare il campo `from` in `emailService.ts`
4. Verificare la deliverability (test con strumenti come mail-tester.com)

Senza questo passaggio, le email di conferma rischiano di finire nello spam dei partecipanti.
