# 05 — Roadmap

**Versione**: 1.1.0 | **Progetto**: ABRAZO MVP 0.9.8 | **Aggiornato**: Giugno 2026

---

## Indice

1. [Stato attuale — MVP 0.9.0](#1-stato-attuale--mvp-090)
2. [Milestone immediate — verso 1.0](#2-milestone-immediate--verso-10)
3. [Modulo Segreteria](#3-modulo-segreteria)
4. [Autenticazione e ruoli](#4-autenticazione-e-ruoli)
5. [Generalizzazione multi-evento](#5-generalizzazione-multi-evento)
6. [Gestione eventi, pacchetti e attività da backoffice](#6-gestione-eventi-pacchetti-e-attività-da-backoffice)
7. [Comunicazioni e notifiche](#7-comunicazioni-e-notifiche)
8. [Check-in avanzato](#8-check-in-avanzato)
9. [Statistiche e dashboard direzione](#9-statistiche-e-dashboard-direzione)
10. [Pagamenti online](#10-pagamenti-online)
11. [Bot Telegram](#11-bot-telegram)
12. [Gestione volontari](#12-gestione-volontari)
13. [Visione annuale Art&Tango](#13-visione-annuale-arttango)
14. [Criteri di priorità](#14-criteri-di-priorità)

---

## 1. Stato attuale — MVP 0.9.8

### Funzionalità implementate e operative

#### Area pubblica
- [x] Home page con branding ABRAZO e roadmap visiva
- [x] Form iscrizione avanzato per Epico Tango Fest 2027 (bilingue IT/EN)
- [x] Selezione pacchetti con calcolo attività incluse
- [x] Selezione attività singole con pricing separato
- [x] Visualizzazione coppie di maestri con highlight attività correlate
- [x] Calcolo acconto/saldo (70% default o custom per pacchetto)
- [x] Raccolta consensi GDPR con timestamp
- [x] Pagina success con QR, riepilogo finanziario, istruzioni bonifico
- [x] Form iscrizione generico `/register/[eventId]` (legacy)

#### QR Code
- [x] Generazione PNG 512×512 (payload `ABRAZO:EVP:CODE`)
- [x] Upload su Supabase Storage
- [x] Display nella pagina success
- [x] Display nella scheda partecipante admin
- [x] Pagina test QR per sviluppo e demo

#### Email
- [x] Template HTML bilingue IT/EN dark-themed
- [x] Invio automatico via Resend al completamento iscrizione
- [x] Riepilogo completo: dati, pacchetti, attività, finanziario, bonifico, consensi
- [x] Preview template nell'admin (`/communications`)

#### Area amministrativa
- [x] Dashboard con statistiche evento attivo
- [x] Lista eventi
- [x] Hub evento con link a tutte le funzioni operative
- [x] Lista partecipanti con stati pagamento e badge ruolo
- [x] Scheda partecipante completa (dati, attività, GDPR, QR, audit trail)
- [x] Check-in evento via QR scanner (html5-qrcode)
- [x] Input manuale payload per check-in senza camera
- [x] Check-in per singola attività con verifica prenotazione
- [x] Prevenzione check-in duplicati
- [x] Lista attività con metriche Iscritti/Presenti/Assenti
- [x] Gestione stati pagamento (pending/deposit/paid) con Server Actions
- [x] Ricerca partecipanti
- [x] Export Excel (3 fogli: Iscrizioni, Attività, Riepilogo)
- [x] Audit trail visibile nella scheda partecipante

#### Sicurezza e autenticazione (MVP 0.9.6 → 0.9.8)
- [x] Tabella `staff` con 4 ruoli (`super_admin`, `segreteria`, `direzione`, `checkin`)
- [x] Login email + password con Supabase Auth e sessioni cookie-based
- [x] Logout con `signOut()` e redirect a `/login`
- [x] Proxy Next.js 16 — `/admin/*` protetta con redirect a `/login`
- [x] Server Actions `confirmDeposit`, `confirmPayment`, `addStaffNote` protette con `requireRole`/`requireAuth`
- [x] API Routes sensibili protette con 401/403 JSON (export Excel, check-in evento, check-in attività)
- [x] `operator_name` e `checked_in_by` nell'audit trail riportano l'email reale dell'operatore
- [x] Row Level Security attivata su 10 tabelle contenenti dati sensibili

---

## 2. Milestone immediate — verso 1.0

Queste sono le funzionalità necessarie per il **primo deploy in produzione reale** con dati reali di Epico Tango Fest 2027.

### M1 — Autenticazione admin ✅ completata (MVP 0.9.6)

Completata nella Security Foundation MVP 0.9.6. Dettagli in `docs/architecture/SECURITY_IMPLEMENTATION_PLAN.md`.

### M1b — API Hardening ✅ completata (MVP 0.9.7)

**Completato**:
- `/api/events/[id]/export-xlsx` → `requireRole direzione` — 401/403 JSON
- `/api/checkin/event` e `/api/checkin/activity` → `requireRole checkin` — 401/403 JSON
- `operator_name` e `checked_in_by` reali nell'audit trail
- API pubbliche (`/api/event-participants`, `/api/registrations`) invariate

### M1c — Row Level Security ✅ completata (MVP 0.9.8)

**Completato**: RLS attivata su 10 tabelle contenenti dati personali o operativi sensibili. Nessuna policy pubblica necessaria: queste tabelle sono accessibili esclusivamente tramite service role, che bypassa RLS.

**Rimandato a RC 1.0** (non è un gap di sicurezza): policy pubbliche su `events`, `packages`, `event_sessions` — tabelle accessibili dal flusso pubblico di iscrizione con dati per natura non sensibili.

---

### M2 — Ricalcolo prezzi server-side

**Obiettivo**: eliminare la fiducia nei valori finanziari inviati dal client.

**Scope**:
- La POST `/api/event-participants` recupera `packages.price`, `event_activities.price_amount` e `packages.deposit_amount` dal DB
- Ignora `totalAmount`, `depositAmount`, `balanceAmount` ricevuti dal client
- Ricalcola autonomamente e salva i valori corretti

**Stima**: 1 sessione di sviluppo.

---

### M3 — Dominio email produzione

**Obiettivo**: garantire la deliverability delle email di conferma.

**Scope**:
- Configurare dominio su Resend (es. `noreply@artango.it`)
- Aggiungere record DNS (SPF, DKIM, DMARC)
- Aggiornare `from` in `emailService.ts`
- Test deliverability

**Stima**: configurazione DNS (non dipende da sviluppo).

---

### M4 — Operator identity nel check-in ✅ completata (MVP 0.9.7)

`checked_in_by` nelle API di check-in ora riporta l'email reale dell'operatore autenticato, estratta dal token di sessione. Completata contestualmente ad API Hardening.

---

## 2bis. Prioritizzazione post-Security-Foundation

> **Decisione di progetto — 28 giugno 2026**

Con il completamento di MVP 0.9.8, le fondamenta di sicurezza di ABRAZO sono **adeguate per il rilascio MVP**. I quattro layer di difesa (proxy, Server Actions, API Routes, RLS) coprono tutti i vettori di rischio critici identificati nella Security Foundation.

**Da questo momento la priorità si sposta dalla sicurezza alle funzionalità utente e operative.**

Le attività di hardening finale (MS-RLS-B, AdminHeader, migration alignment) sono programmate per Release Candidate 1.0, dopo che il sistema avrà ricevuto validazione operativa reale.

### Priorità immediate — funzionalità utente

Le seguenti aree rappresentano il valore operativo che manca per un utilizzo reale del sistema su Epico Tango Fest 2027.

#### A — Flusso completo iscrizione

Il cuore del prodotto. Deve funzionare in modo affidabile end-to-end per ogni iscritto.

- Registrazione completa con selezione pacchetti e attività
- Generazione QR code univoco per ogni iscrizione
- Salvataggio PNG su Supabase Storage con path strutturato
- Invio email automatico di conferma (template bilingue IT/EN con QR allegato)
- Pagina success con riepilogo finanziario e istruzioni bonifico

#### B — Carrello dinamico

L'esperienza utente durante la compilazione del form deve essere immediata e coerente.

- Riepilogo costi aggiornato live al variare delle selezioni
- Calcolo dinamico di totale, acconto e saldo residuo
- Indicazione chiara di cosa è incluso nel pacchetto vs. selezionato singolarmente
- Feedback visivo immediato su ogni modifica

#### C — Iscrizioni multiple

Art&Tango ha partecipanti che viaggiano in coppia o in piccoli gruppi. Il sistema deve permetterlo.

- Iscrizione di più persone in un'unica sessione
- Gestione anagrafica individuale per ogni membro del gruppo
- Generazione QR code individuali per ciascuno
- Riepilogo aggregato con importi per ogni iscritto

#### D — Dashboard operativa

Le funzioni di back-office devono essere affidabili e rapide per il personale Art&Tango.

- Segreteria: inbox pagamenti, conferma acconto/saldo, email automatiche
- Check-in: scanner QR con feedback immediato, gestione duplicati, segnalazione pagamento incompleto
- Pagamenti: lista iscritti per stato, aggiornamento rapido da smartphone
- Ricerca: ricerca per nome/codice/email con accesso diretto alla scheda

---

## 3. Modulo Segreteria

### Obiettivo

La segreteria di Art&Tango deve poter gestire il ciclo completo di un'iscrizione senza dover modificare direttamente il database.

### MVP 0.9.1 — Inbox operativa ✅ completata

- [x] **Route `/segreteria`**: inbox con sezioni "Da verificare" e "Acconto ricevuto"
- [x] **4 stat card**: nuove iscrizioni, da verificare, acconti, saldati
- [x] **InboxCard**: dati partecipante, importi, bottoni azione contestuali
- [x] **Server Action `confirmDeposit`**: pending → deposit con audit
- [x] **Server Action `confirmPayment`**: any → paid, con email di conferma definitiva e audit
- [x] **Gestione email_failed**: se l'email fallisce, il pagamento non viene annullato
- [x] **Template `buildPaymentConfirmationEmail`**: bilingue IT/EN

### MVP 0.9.2 — Rifinitura Segreteria ✅ completata

- [x] **Bottoni azione prominenti**: stile filled (amber/green) con padding adeguato al touch
- [x] **Feedback post-azione**: redirect con query param, banner di conferma per acconto e pagamento
- [x] **Hint descrittivi sulle stat card**: breve testo sotto ogni contatore
- [x] **Logo responsivo**: ridimensionato su mobile
- [x] **Manuale operativo**: `docs/manuals/SEGRETERIA.md` per staff non tecnico

### MVP 0.9.3 — Timeline operativa e note staff ✅ completata

- [x] **Timeline arricchita**: ogni evento audit ha icona, label leggibile e colore per tipo (`registration_created`, `payment_deposit`, `payment_paid`, `email_sent`, `email_failed`, `event_checkin_completed`, `activity_checkin_completed`, `staff_note`)
- [x] **Note staff visivamente distinte**: sfondo evidenziato per le note rispetto agli eventi automatici
- [x] **Form "Aggiungi nota interna"**: textarea + bottone nella scheda partecipante
- [x] **Server Action `addStaffNote`**: insert in `event_participant_audit` con `event_type = "staff_note"`, `operator_name = "segreteria"`, gestione errori silenziosa
- [x] **Manuale aggiornato**: sezioni 12 e 13 su timeline e note in `docs/manuals/SEGRETERIA.md`

### Funzionalità future — Gestione iscrizioni

- [ ] **Modifica iscrizione**: aggiunta/rimozione attività post-registrazione, con ricalcolo automatico degli importi
- [ ] **Cancellazione iscrizione**: con email notifica al partecipante e aggiornamento audit
- [ ] **Inserimento iscrizione manuale**: per partecipanti che non riescono a iscriversi online
- [ ] **Iscrizioni di gruppo**: gestione di coppie o piccoli gruppi con un'unica operazione

### Funzionalità future — Gestione pagamenti

- [ ] **Nota di pagamento**: possibilità di aggiungere note a ogni transazione (es. "Bonifico del 12/01, ref. 2027-A3K9P2")
- [ ] **Storico pagamenti**: timeline visiva dei pagamenti ricevuti per ogni partecipante
- [ ] **Promemoria pagamento**: invio manuale (o automatico) di email di sollecito ai `pending` vicini alla scadenza
- [ ] **Report incassi**: totale giornaliero/settimanale degli aggiornamenti pagamento

### Funzionalità future — Comunicazioni

- [ ] **Ricerca avanzata**: filtri multipli (stato pagamento, ruolo, attività prenotate, lingua)
- [ ] **Selezione multipla**: selezione di un sottoinsieme di partecipanti per comunicazioni mirate

---

## 4. Autenticazione e ruoli

> **Stato MVP 0.9.8 — Security Foundation**: ✅ completata il 28 giugno 2026. Piano operativo completo in `docs/architecture/SECURITY_IMPLEMENTATION_PLAN.md`.

### Architettura di sicurezza attiva

```
Layer 1  src/proxy.ts        getClaims() — blocco a /admin/* senza sessione valida
Layer 2  src/lib/auth.ts     requireRole/requireAuth — Server Actions protette
Layer 3  getCurrentStaff()   401/403 JSON — API Routes protette
Layer 4  Supabase RLS        10 tabelle sensibili inaccessibili via client anon
```

### Implementato (MVP 0.9.6 → 0.9.8)

- [x] Tabella `staff` con 4 ruoli: `super_admin`, `segreteria`, `direzione`, `checkin`
- [x] `@supabase/ssr` 0.12.0 — sessioni cookie-based leggibili dal proxy
- [x] `src/proxy.ts` — protegge `/admin/*`, redirect a `/login?from=<path>`
- [x] `src/lib/auth.ts` — `requireAuth()`, `requireRole()`, `getCurrentStaff()`
- [x] Pagina login `/login` con email e password
- [x] Logout con `signOut()` + redirect a `/login`
- [x] Bottone "Esci" nei due hub di navigazione (`/admin`, `/admin/events`, `/admin/events/[id]`)
- [x] Server Actions `confirmDeposit`, `confirmPayment`, `addStaffNote` protette
- [x] API Routes sensibili protette con 401/403 JSON
- [x] `operator_name` e `checked_in_by` nell'audit trail riportano l'email reale
- [x] RLS attivata su 10 tabelle contenenti dati sensibili (senza policy — solo service role)

### Ruoli attivi

| Ruolo | Accesso |
|---|---|
| `super_admin` | Tutto — bypassa qualsiasi controllo di ruolo |
| `segreteria` | `confirmDeposit`, `confirmPayment`, tutto il backoffice |
| `direzione` | Export Excel, lettura backoffice |
| `checkin` | Scanner QR evento e attività |

### Rimandato a RC 1.0 (miglioramento architetturale, non gap di sicurezza)

- [ ] MS-RLS-B — policy pubbliche su `events`, `packages`, `event_sessions`
- [ ] Fix `admin/events/page.tsx` da `supabase` a `supabaseAdmin`
- [ ] AdminHeader condiviso con logout su tutte le 12 pagine operative

### Nota sul ruolo `checkin`

Il ruolo `checkin` è particolarmente importante dal punto di vista GDPR: consente al personale volontario di fare check-in senza accedere ai dati personali dei partecipanti. Il checker vede solo:
- "Check-in registrato" / "Già registrato" / "Non trovato"
- Il nome del partecipante (minimo indispensabile per verifica)

---

## 4b. RC 1.0 — Hardening finale e backoffice unificato

> **Priorità**: dopo il completamento delle funzionalità utente (§2bis A–D). Questi interventi non bloccano il deploy MVP ma devono essere chiusi prima della Release Candidate ufficiale.

### Scope RC 1.0 — AdminHeader condiviso

Esito della Design Review MS-G (28 giugno 2026): il bottone "Esci" è presente nei hub di navigazione (`/admin`, `/admin/events`, `/admin/events/[id]`). Le pagine operative profonde ne sono prive — gap accettato per MVP.

- [ ] Componente `AdminHeader` condiviso (Server Component)
  - Logo ABRAZO
  - Slot per breadcrumb / link "← Torna a X"
  - Bottone "Esci" sempre visibile
  - Badge email/ruolo dell'operatore autenticato
- [ ] Applicare `AdminHeader` a tutte le 12 pagine admin (Server e Client Components)
- [ ] Breadcrumb / navigazione back coerenti su tutte le pagine
- [ ] Stile uniforme del logo (dimensione consistente in tutti i contesti)

### Scope RC 1.0 — MS-RLS-B (policy pubbliche Supabase)

Non è un gap di sicurezza attivo — è un miglioramento di defense-in-depth.

- [ ] Fix codice: `src/app/admin/events/page.tsx` — sostituire `supabase` con `supabaseAdmin`
- [ ] `ALTER TABLE public.events ENABLE ROW LEVEL SECURITY` + policy `USING (true)`
- [ ] `ALTER TABLE public.packages ENABLE ROW LEVEL SECURITY` + policy `USING (is_public = true AND is_active = true)`
- [ ] `ALTER TABLE public.event_sessions ENABLE ROW LEVEL SECURITY` + policy `USING (is_bookable = true)`
- [ ] Test flusso pubblico di iscrizione end-to-end

### Scope RC 1.0 — Revisione architetturale finale

- [ ] Allineamento migration Supabase (vedi §4c)
- [ ] Schema baseline `002_event_participants_schema.sql`
- [ ] Documentazione `docs/01_ARCHITECTURE.md` — sezione autenticazione
- [ ] Documentazione `docs/04_GDPR_AND_SECURITY.md` — sicurezza tecnica aggiornata
- [ ] Decision Log DL-12, DL-13, DL-14 in `docs/06_PROJECT_HISTORY.md`

---

## 4c. Debito tecnico — Allineamento migration Supabase

> **Scoperto durante Design Review MVP 0.9.8** (28 giugno 2026).

### Problema

Il file `supabase/migrations/001_init_abrazo_schema.sql` rappresenta lo schema **MVP 0.5** e non è allineato con il database Supabase reale, che è evoluto significativamente nel corso dello sviluppo.

Tabelle presenti nell'applicazione ma **assenti dalla migration**:

| Tabella | Presente nel codice | Presente in migration |
|---|---|---|
| `event_participants` | ✓ | ✗ |
| `event_activities` | ✓ | ✗ (migration ha `event_sessions`) |
| `event_participant_activities` | ✓ | ✗ (migration ha `package_items`) |
| `event_participant_audit` | ✓ | ✗ |
| `package_activities` | ✓ | ✗ |
| `teacher_couples` | ✓ | ✗ |
| `staff` | ✓ | ✗ (aggiunta in MS-A) |
| `checkins` | ✓ | ⚠ struttura diversa |

### Rischio

Chiunque applichi le migration da zero otterrà uno schema diverso da quello di produzione. I rollback basati su migration non sono affidabili. Qualsiasi nuovo collaboratore che esegue `supabase db reset` parte da uno schema non corrispondente all'app.

### Soluzione — da fare prima di RC 1.0

- [ ] Produrre uno **schema baseline aggiornato** che rifletta il database reale: dump dello schema di produzione via `supabase db dump --schema-only` o export dal Dashboard
- [ ] Creare `supabase/migrations/002_event_participants_schema.sql` (o equivalente) con le tabelle mancanti
- [ ] Documentare in `docs/02_DATABASE.md` lo stato effettivo di tutte le tabelle
- [ ] Verificare che `supabase/migrations/` sia completo prima di onboardare nuovi sviluppatori

**Priorità**: alta per affidabilità del progetto, ma non blocca il deploy MVP se il database di produzione è già corretto.

---

## 5. Generalizzazione multi-evento

### Obiettivo

Eliminare l'hardcoding di Epico Tango Fest e rendere il sistema completamente parametrico.

### Passi

1. **Slug-based routing**: `/register/[slug]/` invece di `/register/epico-tango-fest-2027/`
2. **Server loader parametrico**: il loader legge l'evento per slug, non per ID hardcoded
3. **Form parametrico**: `RegisterClient` riceve la configurazione come prop senza logica event-specific
4. **Admin parametrico**: rimuovere riferimenti hardcoded all'event ID nell'admin dashboard

### Resultado atteso

Aggiungere un nuovo evento richiede solo:
1. Inserire l'evento nel DB con slug, date, venue
2. Inserire pacchetti, attività, coppie maestri
3. La pagina `/register/[slug]` funziona automaticamente

---

## 6. Gestione eventi, pacchetti e attività da backoffice

### Obiettivo

Lo staff deve poter creare e configurare un evento senza modificare il database direttamente.

### Pannello eventi

- [ ] Lista tutti gli eventi (attivi, passati, in bozza)
- [ ] Crea nuovo evento (nome, slug, date, venue, IBAN, beneficiario)
- [ ] Modifica evento esistente
- [ ] Attiva/disattiva evento (visibilità pubblica)

### Pannello pacchetti

- [ ] Lista pacchetti per evento
- [ ] Crea/modifica/elimina pacchetto (nome, prezzo, acconto, attività incluse)
- [ ] Riordino drag-and-drop

### Pannello attività

- [ ] Lista attività per evento con filtri (tipo, sala, maestri)
- [ ] Crea/modifica attività (codice, tipo, titolo IT/EN, sala, orari, prezzo, capienza)
- [ ] Associazione maestri a attività
- [ ] Definizione quali attività appartengono a quali pacchetti

### Pannello maestri

- [ ] Anagrafica insegnanti
- [ ] Coppie di maestri per evento
- [ ] Associazione foto

---

## 7. Comunicazioni e notifiche

### Email batch

- [ ] **Promemoria acconto**: email a tutti i `pending` X giorni prima della scadenza
- [ ] **Aggiornamento orari**: invio di variazioni al programma a tutti i partecipanti
- [ ] **Pre-evento**: email riepilogativa con programma, indirizzo, orari il giorno prima
- [ ] **Post-evento**: ringraziamento e link al prossimo evento

### Template personalizzabili

- [ ] Editor di template nell'admin (form semplice con variabili `{{nome}}`, `{{codice}}`, ecc.)
- [ ] Anteprima prima dell'invio
- [ ] Test send a indirizzo specifico

### Notifiche real-time

- [ ] Notifica admin a ogni nuova iscrizione (email o Supabase Realtime)
- [ ] Notifica admin a ogni aggiornamento pagamento (da bonifici ricevuti)

---

## 8. Check-in avanzato

### Payment-aware check-in

Il sistema attuale mostra già `payment_status` nella card dopo ogni scan. Evoluzioni previste:

- [x] **Segnalazione visiva esplicita** per check-in con pagamento incompleto: `PaymentPanel` con badge colorato, messaggio operativo e importi (totale / saldo residuo) — MVP 0.9.5
- [ ] **Blocco configurabile**: opzione per l'admin di abilitare un "blocco morbido" che richiede conferma esplicita prima di registrare il check-in di un partecipante con `payment_status ≠ "paid"`
- [ ] **Contatore pagamenti parziali** nella dashboard check-in (quante persone sono entrate con acconto ancora aperto)

> **Principio invariante**: il QR rimane un identificatore di identità, non di pagamento (vedi `DL-11`). Queste funzionalità aggiungono visibilità operativa senza modificare la semantica del codice.

### Dashboard presenze live

- [ ] Schermata live con contatore presenze aggiornato in tempo reale (Supabase Realtime)
- [ ] Visualizzazione per attività: iscritti / presenti / assenti in percentuale
- [ ] Display per schermo condiviso in sala (fullscreen, font grande)

### Modalità offline

- [ ] Service Worker per funzionamento base senza connessione
- [ ] Coda locale di check-in sincronizzata quando torna la connessione
- [ ] Indicatore stato connessione nell'interfaccia

### Stampa badge

- [ ] Generazione PDF badge per ogni partecipante (nome, codice, ruolo, QR)
- [ ] Stampa batch per tutti i partecipanti

---

## 9. Statistiche e dashboard direzione

### Dashboard evento

- [ ] Curva di iscrizioni nel tempo (grafico)
- [ ] Breakdown per pacchetto (quanti Full Pass, Stage Pass, ecc.)
- [ ] Breakdown per ruolo (leader/follower — bilanciamento)
- [ ] Breakdown per lingua
- [ ] Occupancy rate per attività (% di riempimento)
- [ ] Proiezione incasso totale vs. incassato reale

### Dashboard Art&Tango annuale

- [ ] Tutti gli eventi dell'anno su una schermata
- [ ] Confronto iscrizioni e incassi anno su anno
- [ ] Stagionalità (quali mesi hanno più eventi)
- [ ] Top partecipanti (chi partecipa a più eventi — per fidelizzazione)

### Export report

- [ ] **Export Excel da rivedere per layout e colonne (RC1)**: le tre schede (Iscrizioni, Attività, Riepilogo) producono dati corretti ma il formato colonne e i totali sono stati definiti nella fase MVP; vanno allineati al modello dati attuale (registration_payments ledger, colonne delta editor, is_exclusive). Revisione prevista post-RC1.
- [ ] PDF riepilogo evento per riunioni di board
- [ ] CSV dati grezzi per analisi esterne

---

## 10. Pagamenti online

### Valutazione

L'integrazione di pagamenti online (Stripe, PayPal, Satispay) è prevista come opzione futura, da valutare dopo aver stabilizzato il flusso con bonifico.

### Considerazioni

**Pro**:
- Elimina il tracking manuale dei bonifici
- Pagamento immediato alla conferma iscrizione
- Riduce i posti "occupati ma non pagati"

**Contro**:
- Commissioni (Stripe: 1.5% + 0.25€ per carta EU)
- Complessità legale (ricevute, IVA se applicabile)
- Onboarding più lungo (KYC/AML per Stripe)
- Cambia il flusso UX (attuale bonifico è familiare per il pubblico Tango)

**Approccio consigliato**:
- Mantenere il bonifico come default per i festival (importi elevati, margini alti)
- Considerare pagamento online per eventi minori (milonghe, serate) dove la rapidità è più importante

---

## 11. Bot Telegram

### Obiettivo

Notifiche in tempo reale per lo staff via Telegram — canale già usato nella comunicazione interna di Art&Tango.

### Funzionalità previste

- Notifica ad ogni nuova iscrizione: "Nuova iscrizione: Mario Rossi (EVP-A3K9P2) — Full Pass — €480"
- Notifica ad ogni aggiornamento pagamento: "Acconto registrato: Mario Rossi — €168"
- Report giornaliero: "Oggi: 5 nuove iscrizioni, 3 acconti ricevuti, totale iscritti: 142"
- Alert capienza: "ST01 Stage Avanzato: 28/30 iscritti — 2 posti rimasti"

### Implementazione

- Telegram Bot API (bot privato per il canale staff Art&Tango)
- Webhook su eventi Supabase o chiamata API Route
- Nessun dato sensibile nei messaggi Telegram (no email, no dati personali completi)

---

## 12. Gestione volontari

### Obiettivo

Art&Tango si avvale di volontari durante i festival per check-in, accoglienza, logistica. ABRAZO deve poterli gestire separatamente dai partecipanti.

### Funzionalità previste

- [ ] Anagrafica volontari (separata da `participants`)
- [ ] Assegnazione a turni e postazioni
- [ ] QR code volontario (`ABRAZO:VOL:VOL-XXXXXX`)
- [ ] Check-in turno
- [ ] Dashboard turni (chi è presente, chi manca)
- [ ] Comunicazioni dedicate ai volontari

---

## 13. Visione annuale Art&Tango

ABRAZO deve diventare il sistema operativo di Art&Tango per tutti gli eventi dell'anno.

### Calendario tipico annuale Art&Tango (indicativo)

| Periodo | Evento tipico |
|---|---|
| Autunno/Inverno | Corsi settimanali (iscrizioni stagionali) |
| Dicembre | Milonga di fine anno |
| Primavera | Workshop con maestro ospite |
| Estate | Epico Tango Fest (evento principale) |
| Anno rotondo | Milonghe mensili |

### Come ABRAZO supporta ogni tipo

| Evento | Funzionalità ABRAZO necessarie |
|---|---|
| Corsi | Iscrizioni stagionali, gestione lista allievi, ruoli leader/follower, presenze lezione |
| Milonghe | Biglietteria semplice, check-in rapido, nessuna selezione attività |
| Workshop | Capienza limitata, waiting list, un solo pacchetto |
| Festival (Epico) | Tutto il sistema completo |

---

## 14. Criteri di priorità

### Gerarchia attuale (post-MVP 0.9.8)

> Le fondamenta di sicurezza sono completate. La priorità passa alle funzionalità utente e operative.

1. **Flusso iscrizione affidabile end-to-end** → massima priorità (§2bis A)
2. **Esperienza utente sul form** → alta priorità (§2bis B — carrello dinamico)
3. **Iscrizioni multiple** → alta priorità (§2bis C — caso d'uso reale Art&Tango)
4. **Dashboard operativa stabile** → alta priorità (§2bis D — uso quotidiano dello staff)
5. **Generalizzazione multi-evento** → media priorità (§5 — necessaria per il secondo evento)
6. **RC 1.0 hardening** → media priorità (§4b — non blocca MVP ma va chiuso prima di 1.0)
7. **Funzionalità avanzate** → bassa priorità (statistiche, volontari, bot, pagamenti online)

### Regola di sviluppo

Ogni funzionalità deve essere:
- Necessaria a un caso d'uso reale già presente (non anticipazione)
- Implementabile in modo coerente con l'architettura esistente
- Testabile end-to-end prima del deploy
