# ADR-001 — Registration Payment Ledger

**Status**: Accepted  
**Date**: 2026-07-05  
**Authors**: Art&Tango / ABRAZO  
**Supersedes**: nessun ADR precedente  

---

## Contesto

ABRAZO è la piattaforma digitale di gestione eventi di Art&Tango. La visione progettuale è quella di un sistema multi-evento riutilizzabile dall'associazione per qualsiasi tipo di appuntamento (festival, workshop, milonghe, stage, corsi) e potenzialmente commercializzabile verso altre organizzazioni che gestiscono eventi analoghi.

Ogni decisione architetturale deve essere valutata con questa prospettiva di medio-lungo periodo. La solidità del modello di dominio ha precedenza rispetto alle scorciatoie implementative.

Il ciclo di vita di una registrazione prevede: iscrizione pubblica, conferma acconto, conferma saldo, eventuale integrazione dell'iscrizione, check-in evento, check-in attività. I pagamenti sono oggi esclusivamente manuali (bonifico bancario o contanti). In futuro ABRAZO supporterà pagamenti online tramite provider esterni.

Al momento della progettazione iniziale, il modello economico era contenuto interamente in `event_participants`:

```
total_amount         — importo totale dell'iscrizione
deposit_amount       — acconto dovuto (strutturale, definito all'iscrizione)
balance_amount       — saldo dovuto (strutturale: total - deposit)
payment_status       — pending | deposit | paid
deposit_received_at  — timestamp conferma acconto
balance_received_at  — timestamp conferma saldo
```

Questo modello era sufficiente per il caso base. Ha mostrato i suoi limiti nel momento in cui è stato necessario supportare supplementi post-saldo, importi effettivi ricevuti, storia dei pagamenti e pagamenti online futuri.

---

## Problema del modello precedente

### 1. I timestamp non sostituiscono i record

`deposit_received_at` e `balance_received_at` registrano *quando* un pagamento è stato confermato, non *quanto* è stato ricevuto. Il sistema assume implicitamente che il partecipante abbia sempre pagato esattamente `deposit_amount` all'acconto e `balance_amount` al saldo. Questa assunzione si spezza con pagamenti parziali, supplementi post-saldo e rettifiche amministrative.

### 2. `supplement_amount` è una patch, non un modello

La proposta intermedia introduceva una colonna `supplement_amount numeric` e `supplement_paid_at timestamptz`. Questa soluzione modella un solo supplemento per registrazione come scalare: non gestisce N supplementi distinti nel tempo, non registra l'importo effettivo di ciascuno, non tiene traccia di chi ha registrato cosa e quando. Una colonna scalare non può rappresentare una sequenza di eventi economici.

### 3. Il modello non è estendibile verso pagamenti online

Aggiungere un provider online al modello con timestamp richiederebbe nuove colonne direttamente su `event_participants` per ogni provider. Ogni nuovo provider è una migration strutturale. Questo approccio non regge in una piattaforma multi-evento e potenzialmente multi-organizzazione.

---

## Decisione

Introduciamo la tabella **`registration_payments`**: un registro immutabile di ogni movimento economico ricevuto, associato a un `event_participant`.

```
registration_payments:
  id                       — UUID PK
  event_participant_id     — FK → event_participants (ON DELETE RESTRICT)
  event_id                 — FK → events (denormalizzato per reporting)
  amount                   — importo del movimento (sempre > 0)
  currency                 — valuta (text, default EUR, senza vincolo strutturale)
  payment_type             — deposit | balance | supplement | adjustment
  payment_method           — bank_transfer | cash | external
  provider_name            — nome provider (null per pagamenti manuali)
  provider_transaction_id  — ID transazione provider (null per manuali)
  description              — descrizione del movimento economico
  recorded_by              — UUID FK → auth.users (operatore che ha registrato)
  recorded_at              — quando la segreteria ha registrato il pagamento
  created_at               — timestamp di INSERT nel DB
```

**Invariante fondamentale**:

```
outstanding(participant) = event_participants.total_amount
                         - SUM(registration_payments.amount)
                           WHERE event_participant_id = participant.id
```

### Il campo `payment_type`

I quattro valori coprono l'intero dominio dei movimenti economici prevedibili:

- `deposit` — acconto iniziale
- `balance` — saldo finale
- `supplement` — pagamento post-saldo per attività aggiunte successivamente
- `adjustment` — rettifiche, arrotondamenti, accrediti, sconti eccezionali, correzioni amministrative

`adjustment` è introdotto subito perché non tutti i movimenti economici sono pagamenti nel senso stretto. Evita future migration e mantiene il modello aderente al dominio reale di una segreteria che gestisce eccezioni.

### Il campo `description`

Rinominato da `notes` a `description` perché il campo descrive il movimento economico, non aggiunge annotazioni opzionali. La descrizione è il documento primario del pagamento:

- "Bonifico CRO 12345 del 15/07"
- "Pagamento contanti evento"
- "Saldo integrativo Stage ST04"
- "Sconto socio attivo applicato"

Le note operative della segreteria (commenti interni, follow-up) vivono nella timeline del fascicolo come eventi `staff_note` in `event_participant_audit`.

### Il campo `currency` senza vincolo strutturale

`currency` è `text NOT NULL DEFAULT 'EUR'` senza `CHECK` constraint. L'applicazione applica EUR in tutti i path RC1. La decisione di non vincolare strutturalmente la tabella è intenzionale: eventi internazionali, sedi estere, sponsor multi-valuta sono scenari realistici in una piattaforma aperta. Aggiungere una valuta richiederà modifiche applicative, non una migration strutturale. Il modello rimane aperto.

### Il campo `recorded_by` come UUID

`recorded_by uuid NOT NULL REFERENCES auth.users(id)` invece di `text`. L'email di un operatore può cambiare; il suo UUID in `auth.users` è stabile per tutta la vita del sistema. Questo garantisce la tracciabilità degli operatori anche dopo cambi di email o ruolo.

### Il campo `event_id` (denormalizzazione intenzionale)

`registration_payments.event_id` è tecnicamente derivabile da `event_participant_id → event_participants.event_id`. La sua presenza è una **denormalizzazione intenzionale e documentata**, non una ridondanza accidentale.

Motivazioni:

- **Report e dashboard amministrative**: le query più frequenti in segreteria aggregano pagamenti per evento (`WHERE event_id = ?`). Senza `event_id` diretto, ogni aggregazione richiederebbe un join con `event_participants`, aumentando la complessità e la latenza su dataset grandi.
- **Export e riconciliazione**: l'export Excel per evento, il calcolo degli incassi totali, le statistiche di cassa partono dall'`event_id`. Averlo nella riga rende queste query dirette.
- **Coerenza con il resto del modello**: tutte le tabelle satellite di un evento (`event_participant_activities`, `checkins`, `event_participant_audit`) portano `event_id` come campo diretto. `registration_payments` segue lo stesso pattern.
- **Stabilità della chiave**: `event_id` è un UUID immutabile. Non può cambiare durante la vita della registrazione. Il rischio di inconsistenza tra `event_id` su `registration_payments` e l'`event_id` derivato da `event_participants` è strutturalmente impossibile: entrambi i campi sono scritti nello stesso INSERT dalla stessa Server Action.

**Questa denormalizzazione non deve essere rimossa come "ridondante" senza una nuova ADR** che valuti l'impatto sulle query amministrative e sul reporting.

---

## Perché separiamo acquisti e pagamenti

La tabella `event_participant_activities` registra già *cosa è stato acquistato* (ogni attività con prezzo, sorgente e package_id). È il lato "acquisti" del registro.

`registration_payments` registra *cosa è stato pagato*. Le due responsabilità sono distinte e questa separazione è il principio architetturale centrale:

- Un partecipante può acquistare uno stage senza averlo ancora pagato.
- Un pagamento può coprire parzialmente o totalmente più acquisti.
- Aggiungere un'attività (acquisto) non crea automaticamente un pagamento.

Separare le due tabelle elimina l'ambiguità, consente query precise su entrambi gli aspetti e prepara il terreno per un eventuale modello a invoice lines in futuro.

---

## Perché non usiamo `supplement_amount`

`supplement_amount` è uno scalare che modella un caso particolare come se fosse il caso generale. I problemi:

- Non gestisce N supplementi distinti nel tempo.
- Non registra l'importo effettivo di ciascun supplemento.
- Non registra chi ha registrato il supplemento né quando.
- Richiederebbe aggiornamenti (non INSERT) su dati già confermati — contrario al principio di immutabilità dei record economici.

Ogni evento economico — acconto, saldo, supplemento, rettifica — è distinto e deve avere la propria riga immutabile in `registration_payments`.

---

## Perché non usiamo subito un ledger contabile completo

Un ledger a partita doppia (movimenti credit/debit con segno) è il modello più corretto dal punto di vista contabile formale. Sarebbe adatto a sistemi con rimborsi automatici, valute multiple, fatturazione formale, riconciliazione automatica con home banking.

ABRAZO, nella sua fase attuale, non ha nessuno di questi requisiti operativi immediati. I pagamenti sono manuali, la valuta è unica, i rimborsi sono gestiti fuori sistema. Il ledger completo richiederebbe una comprensione del modello debit/credit da parte della segreteria, query più complesse e una migration più onerosa.

`registration_payments` è il punto di equilibrio: introduce la storia dei pagamenti e la separazione tra acquisti e incassi, senza la complessità contabile. L'evoluzione al ledger completo è naturale e non richiede cambiamenti al modello di dominio della registrazione.

---

## Impatto sui pagamenti manuali (RC1)

Per i pagamenti manuali RC1 (bonifico, contanti):

- `payment_method = 'bank_transfer'` oppure `'cash'`
- `provider_name = NULL`, `provider_transaction_id = NULL`
- `recorded_by` = UUID dell'operatore staff da `requireAuth()`
- `description` = descrizione leggibile del bonifico o del pagamento
- `recorded_at = now()` al momento della registrazione

Le azioni segreteria (`confirmDeposit`, `confirmPayment`) producono due effetti atomici in sequenza:
1. `INSERT INTO registration_payments (...)`
2. `UPDATE event_participants SET payment_status = ...`

Se la prima scrittura fallisce, la seconda non viene eseguita. Se la prima riesce e la seconda fallisce, si registra l'errore e si comunica alla segreteria di riprovare: il record in `registration_payments` è immutabile e non viene cancellato.

---

## Immutabilità logica dei record

In RC1, l'immutabilità di `registration_payments` è **logica**, non ancora fisicamente enforced a livello di database.

Questo significa:

- Il database **consente** tecnicamente `UPDATE` e `DELETE` su righe esistenti.
- Il codice applicativo **non deve mai** eseguire `UPDATE` o `DELETE` su righe di `registration_payments`.
- Questa regola è imposta a livello di disciplina architetturale e di revisione del codice, non da un trigger o policy.

### Come gestire correzioni ed eccezioni

Correzioni, sconti, arrotondamenti, rettifiche amministrative non si eseguono modificando una riga esistente. Si aggiunge una nuova riga:

```
payment_type = 'adjustment'
amount       = importo della rettifica
description  = "Rettifica: [motivazione chiara]"
recorded_by  = UUID dell'operatore che ha autorizzato la rettifica
recorded_at  = now()
```

Questo approccio preserva la storia completa, è auditabile, e mantiene l'invariante `outstanding = total_amount - SUM(amount)` sempre calcolabile correttamente.

### Enforcement fisico futuro

Quando la maturità del sistema lo richiederà, l'immutabilità potrà essere enforced a livello di database aggiungendo un trigger PostgreSQL:

```sql
-- (non parte di questa migration — da valutare in una ADR futura)
CREATE OR REPLACE FUNCTION prevent_payment_mutation()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'registration_payments è immutabile. Usare adjustment per correzioni.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_update_registration_payments
  BEFORE UPDATE OR DELETE ON registration_payments
  FOR EACH ROW EXECUTE FUNCTION prevent_payment_mutation();
```

Fino a quando il trigger non è attivo, la correttezza è responsabilità del codice applicativo e della revisione del codice.

---

## Future Evolution

`registration_payments` è progettato per evolvere senza refactoring del modello di dominio.

### Pagamenti online e provider esterni

Qualunque provider esterno (Stripe, PayPal, Nexi, Satispay, wallet digitali, gateway futuri) si integra valorizzando tre campi esistenti:

```
payment_method          = 'external'
provider_name           = 'stripe'          -- oppure 'paypal', 'nexi', 'satispay', ...
provider_transaction_id = 'pi_3abc123...'   -- ID univoco del provider
```

Nessuna modifica strutturale alla tabella. Il provider specifico non è nella constraint di `payment_method` (che usa il valore generico `'external'`) ma nel campo `provider_name`. Ogni nuovo provider è una riga, non una migration.

### Dal ledger operativo al ledger finanziario

`registration_payments` è oggi un **ledger operativo**: registra i pagamenti ricevuti dalla segreteria. In futuro potrà evolvere in un **ledger finanziario** più completo, aggiungendo:

- Righe con importo negativo per rimborsi (o una tabella `registration_refunds` separata)
- Riconciliazione automatica con home banking tramite webhook
- Emissione di documenti fiscali (ricevute, fatture) a partire dai record

Questa evoluzione aggiunge tabelle o colonne senza modificare il modello di dominio della registrazione. La relazione `event_participant → registration_payments` rimane invariata.

### Piattaforma multi-organizzazione

L'architettura attuale è single-tenant (un progetto Supabase per organizzazione). Se ABRAZO evolverà in una piattaforma SaaS multi-tenant, il campo `event_id` sarà il punto di partenza per isolare i dati per organizzazione tramite RLS e partitioning. La struttura della tabella non richiede modifiche: si aggiunge `organization_id` come colonna e si ridefiniscono le policies.

---

## Conseguenze

### Positive

- Ogni movimento economico è un record immutabile con importo reale, tipo, metodo, operatore e timestamp.
- `outstanding` è sempre calcolabile e preciso, indipendentemente dal numero di supplementi o rettifiche.
- La storia completa dei pagamenti è interrogabile direttamente.
- L'aggiunta di provider online non richiede refactoring strutturale.
- `recorded_by` come UUID FK garantisce tracciabilità stabile degli operatori.
- Il reporting economico è immediato: `SUM(amount) GROUP BY payment_type, payment_method`.
- Il modello regge su una piattaforma multi-evento senza modifiche.

### Negative / Attenzioni

- Ogni lettura di `outstanding` richiede un join con aggregato su `registration_payments`. Non è una semplice lettura di colonna. Per query frequenti (es. lista partecipanti con outstanding) valutare una colonna calcolata o una view materializzata in futuro.
- `payment_status` su `event_participants` è un campo denormalizzato (stato operativo): deve essere mantenuto in sync con la payments table all'interno di ogni azione. La sequenza corretta è: prima INSERT in `registration_payments`, poi UPDATE su `event_participants`. Se il DB non supporta transazioni esplicite nel client (Supabase non le espone nativamente nell'SDK), il rischio di inconsistenza in caso di errore parziale è reale e va gestito con retry e logging.
- I record storici migrati in Fase 0 hanno `amount` stimato (uguale a `deposit_amount` o `balance_amount`), non l'importo effettivo ricevuto. Documentato nel campo `description` di ogni riga migrata.

---

## Technical Debt

Questa sezione documenta i debiti tecnici consapevoli introdotti o mantenuti dalla presente decisione. Non sono lacune accidentali: sono decisioni di deferimento con motivazione esplicita.

### 1. Campi deprecati su `event_participants`

I seguenti campi rimangono su `event_participants` per retrocompatibilità con il codice esistente che li legge e li scrive:

| Campo | Stato | Note |
|---|---|---|
| `payment_status` | Mantenuto come stato operativo denormalizzato | Utile per filtri rapidi in segreteria; in futuro derivabile da `registration_payments` |
| `deposit_received_at` | Deprecato | Sostituito da `recorded_at` della riga `payment_type='deposit'` in `registration_payments` |
| `balance_received_at` | Deprecato | Sostituito da `recorded_at` della riga `payment_type='balance'` in `registration_payments` |

Nel medio periodo la fonte di verità per la storia dei pagamenti diventerà progressivamente `registration_payments`. La rimozione di `deposit_received_at` e `balance_received_at` avverrà in una migration di cleanup, dopo che tutto il codice che li legge sarà aggiornato.

**Trigger per affrontarlo**: quando si aggiorna l'ultima pagina che legge questi campi (`/admin/events/[id]/payments`).

### 2. Assenza di `event_participant_packages`

I pacchetti acquistati sono tracciati solo implicitamente via `package_id` sulle righe di `event_participant_activities`. Se un pacchetto ha zero attività associate, non lascia traccia.

**Trigger per affrontarlo**: primo pacchetto senza attività, o necessità di reportistica "ricavi per pacchetto".

### 3. Assenza di rimborsi

Non esiste un modello per movimenti negativi (rimborsi, cancellazioni parziali). I rimborsi sono gestiti fuori sistema.

**Trigger per affrontarlo**: quando la segreteria inizia a gestire rimborsi sistematicamente.

### 4. `outstanding` senza cache

Il calcolo di `outstanding` richiede un join e un aggregato ogni volta. Per volumi piccoli (centinaia di iscritti) è trascurabile. Per volumi più grandi o per query che listano tutti i partecipanti con outstanding, diventa rilevante.

**Trigger per affrontarlo**: quando le query di lista partecipanti mostrano latenza percepibile.

### 5. Mancanza di transazioni esplicite

Le azioni di pagamento eseguono due scritture in sequenza (INSERT + UPDATE) senza transazione atomica. L'SDK Supabase non espone `BEGIN/COMMIT` nativamente nel client TypeScript. In caso di errore tra le due operazioni, i dati possono essere temporaneamente inconsistenti.

**Trigger per affrontarlo**: se si osservano inconsistenze reali, migrare le azioni a Supabase RPC (funzioni PostgreSQL) che eseguono entrambe le scritture in una singola transazione.

### 6. Importi seeding stimati

I record migrati dalla Fase 0 usano `deposit_amount` e `balance_amount` come proxy per l'importo effettivo ricevuto. Non è retroattivamente correggibile senza intervento manuale della segreteria.

**Non affrontabile retroattivamente**: documentato nel campo `description` di ogni riga migrata.

---

## Stabilità di questa ADR

Le ADR documentano decisioni architetturali al momento in cui vengono prese. Devono essere considerate **stabili**: non si modificano per riflettere evoluzioni successive, ma si affiancano con una nuova ADR che le supera o le integra.

- Cambi di decisione architetturale → nuova ADR con campo `Supersedes: ADR-001`
- Evoluzione delle specifiche funzionali → aggiornamento di `docs/` e `CLAUDE.md`, non di questa ADR
- Correzioni di fatto (errori materiali nel testo) → modifica diretta con nota in commit message

Le specifiche funzionali (flussi, UI, Server Actions) possono evolvere nel tempo senza richiedere una nuova ADR. Le decisioni architetturali documentate qui — separazione acquisti/pagamenti, immutabilità logica, denormalizzazione di `event_id`, modello `payment_type`, estensibilità dei provider — richiedono una nuova ADR per essere cambiate.
