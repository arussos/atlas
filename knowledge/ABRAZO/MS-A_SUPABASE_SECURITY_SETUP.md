# MS-A Supabase Security Setup

## 1. SQL da eseguire
## 2. Checklist operativa
## 3. Query di verifica

Verifico il piano prima di produrre qualsiasi SQL.

Il piano è coerente. Verifiche superare:
- tabella: `staff` ✓
- ruoli: `super_admin`, `segreteria`, `direzione`, `checkin` (no `amministratore`) ✓
- `updated_at` esplicitato negli UPDATE — non serve trigger, la procedura §5.4 lo gestisce manualmente ✓
- RLS abilitata, nessuna policy pubblica: accesso solo via `supabaseAdmin` ✓

Un delta rispetto al piano: aggiungo la verifica che il `CHECK` constraint sul ruolo sia effettivamente attivo, e aggiungo uno step per recuperare l'UUID senza ambiguità. Tutto il resto è esecuzione fedele del documento.

---

## MS-A — Prerequisiti Supabase

### Script 1 — Creazione tabella `staff`

Da incollare nel **SQL Editor** del Dashboard Supabase ed eseguire **prima** di creare qualsiasi utente in Authentication.

```sql
-- ============================================================
-- ABRAZO — Security Foundation MS-A
-- Tabella: staff
-- Scopo: operatori autorizzati ad accedere al backoffice
-- ============================================================

-- 1. Creazione tabella
CREATE TABLE public.staff (
  id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       TEXT        NOT NULL,
  full_name   TEXT        NOT NULL,
  role        TEXT        NOT NULL CHECK (role IN ('super_admin', 'segreteria', 'direzione', 'checkin')),
  is_active   BOOLEAN     NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Row Level Security: abilitata senza policy pubbliche
--    Tutta la lettura/scrittura avviene via supabaseAdmin (service role),
--    che bypassa RLS. Nessun accesso da client anon o utenti autenticati.
ALTER TABLE public.staff ENABLE ROW LEVEL SECURITY;

-- 3. Indice parziale per i lookup is_active=true (path caldo in requireAuth)
CREATE INDEX staff_active_idx ON public.staff(id) WHERE is_active = true;

-- ============================================================
-- VERIFICA IMMEDIATA — eseguire subito dopo il blocco sopra
-- ============================================================

-- Verifica struttura colonne
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'staff'
ORDER BY ordinal_position;

-- Verifica che RLS sia abilitata
SELECT relname, relrowsecurity
FROM pg_class
WHERE relname = 'staff';
-- relrowsecurity deve essere: true

-- Verifica CHECK constraint sui ruoli
SELECT constraint_name, check_clause
FROM information_schema.check_constraints
WHERE constraint_schema = 'public'
AND constraint_name LIKE '%staff%';
```

---

### Script 2 — Inserimento primo operatore `super_admin`

Da eseguire **dopo** aver creato l'utente in Authentication → Users e copiato il suo UUID.

Sostituire i tre valori evidenziati con i dati reali.

```sql
-- ============================================================
-- ABRAZO — Security Foundation MS-A
-- Inserimento primo super_admin
-- SOSTITUIRE prima di eseguire:
--   REPLACE-WITH-UUID    → UUID copiato da Authentication → Users
--   REPLACE-WITH-EMAIL   → email usata in Authentication → Users
--   REPLACE-WITH-NAME    → nome e cognome completo
-- ============================================================

INSERT INTO public.staff (id, email, full_name, role)
VALUES (
  'REPLACE-WITH-UUID',
  'REPLACE-WITH-EMAIL',
  'REPLACE-WITH-NAME',
  'super_admin'
);
```

---

### Istruzioni operative — passo per passo

Seguire esattamente questa sequenza. Non invertire i passi 1 e 3.

---

**Passo 1 — Creare la tabella `staff`**

1. Aprire il **Dashboard Supabase** del progetto ABRAZO
2. Navigare in **SQL Editor** (menu laterale sinistro)
3. Aprire una nuova query (pulsante **+ New query**)
4. Incollare lo **Script 1** completo
5. Fare clic su **RUN** (o `Cmd+Enter`)
6. Verificare che il pannello Results non mostri errori
7. Leggere i risultati delle tre query di verifica nella parte inferiore del pannello:
   - La prima deve mostrare 7 colonne: `id`, `email`, `full_name`, `role`, `is_active`, `created_at`, `updated_at`
   - La seconda deve mostrare `relrowsecurity = true`
   - La terza deve mostrare il CHECK constraint con i quattro ruoli validi

---

**Passo 2 — Creare l'utente in Supabase Auth**

1. Navigare in **Authentication** → **Users** (menu laterale sinistro)
2. Fare clic su **Add user** → **Create new user**
3. Compilare:
   - **Email**: l'email del primo super_admin (es. `andrea.russos@gmail.com`)
   - **Password**: una password sicura (minimo 8 caratteri, almeno un numero)
   - Lasciare **Auto Confirm User** spuntato (altrimenti l'utente non può fare login finché non conferma l'email)
4. Fare clic su **Create user**
5. Supabase mostra il nuovo utente nella lista

---

**Passo 3 — Recuperare l'UUID dell'utente**

Due metodi equivalenti, scegliere il più comodo:

**Metodo A — dalla lista Users**:
1. Nella lista Authentication → Users, individuare l'utente appena creato
2. La colonna **User UID** mostra l'UUID nel formato `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
3. Fare clic sull'UUID per selezionarlo, copiarlo

**Metodo B — dal SQL Editor**:
```sql
SELECT id, email, created_at
FROM auth.users
WHERE email = 'REPLACE-WITH-EMAIL'
ORDER BY created_at DESC
LIMIT 1;
```
Eseguire questa query e copiare il valore della colonna `id`.

---

**Passo 4 — Inserire il record in `staff`**

1. Nel **SQL Editor**, aprire una nuova query
2. Incollare lo **Script 2**
3. Sostituire i tre placeholder:
   - `REPLACE-WITH-UUID` → l'UUID copiato al passo 3
   - `REPLACE-WITH-EMAIL` → la stessa email usata in Authentication
   - `REPLACE-WITH-NAME` → nome e cognome (es. `Andrea Russos`)
4. Verificare visivamente che l'UUID sia nella forma corretta (36 caratteri con trattini, nessuna virgolette mancante)
5. Fare clic su **RUN**

---

**Passo 5 — Verifica finale**

Eseguire nel SQL Editor:

```sql
-- Query di verifica completa MS-A
SELECT
  s.id,
  s.email,
  s.full_name,
  s.role,
  s.is_active,
  s.created_at,
  u.email AS auth_email,
  u.confirmed_at IS NOT NULL AS auth_confirmed
FROM public.staff s
JOIN auth.users u ON u.id = s.id;
```

**Risultato atteso**:

| Colonna | Valore atteso |
|---|---|
| `email` | email del super_admin |
| `full_name` | nome e cognome inseriti |
| `role` | `super_admin` |
| `is_active` | `true` |
| `auth_email` | uguale a `email` |
| `auth_confirmed` | `true` (se Auto Confirm era spuntato) |

Se `auth_confirmed` è `false`, l'utente non può ancora fare login. In quel caso: Authentication → Users → click sull'utente → **Send confirmation email**, oppure attivare la conferma manuale dal pannello utente.

---

### Query di rollback

Se qualcosa va storto e si vuole ripartire da zero:

```sql
-- ROLLBACK MS-A — rimuove tabella e tutti i dati
-- ATTENZIONE: irreversibile. Usare solo in caso di errore durante MS-A.

DROP TABLE IF EXISTS public.staff;

-- Verificare che la tabella sia stata rimossa
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'staff';
-- deve restituire 0 righe
```

L'utente creato in Authentication → Users va eliminato manualmente dal Dashboard: Authentication → Users → click sull'utente → **Delete user**.

---

### Checklist di completamento MS-A

```
## MS-A — Prerequisiti Supabase

☐ Script 1 eseguito senza errori nel SQL Editor

☐ Struttura tabella verificata (7 colonne nell'ordine corretto)

☐ RLS abilitata (relrowsecurity = true)

☐ CHECK constraint ruoli verificato (4 valori: super_admin, segreteria, direzione, checkin)

☐ Utente super_admin creato in Authentication → Users

☐ Auto Confirm User = spuntato (o conferma eseguita manualmente)

☐ UUID copiato correttamente

☐ Script 2 eseguito con UUID, email e nome reali

☐ Query di verifica finale eseguita — tutti i campi corretti

☐ auth_confirmed = true (utente può fare login)

☐ MS-A completata — pronta per MS-B
```

---

**Commit consigliato**: nessuno. MS-A non modifica file del repository. Il piano conferma: *"Commit previsto: nessuno (solo operazioni Dashboard)."*
