# Atlas

Piattaforma personale per la costruzione, conservazione e interrogazione del patrimonio professionale.

Questo repository contiene le fondamenta architetturali dell'ecosistema Atlas.

---

## Struttura del repository

```
atlas/
├── knowledge/          # Documenti Markdown per progetto
│   ├── ATLAS/
│   ├── ABRAZO/
│   └── NOEMA/
├── .state/             # Indice SHA256 e stato sync (uno per progetto)
│   ├── ATLAS.json
│   ├── ABRAZO.json
│   └── NOEMA.json
├── FOUNDATION/         # Documenti costituzionali dell'ecosistema
└── tools/
    ├── atlas-import.py       # Importer multi-progetto
    └── test_atlas_import.py  # Suite di test automatici
```

---

## atlas-import.py

Importa e sincronizza i documenti Markdown di un progetto verso una Knowledge Collection di Open WebUI.

### Comandi

```bash
# Scansiona e rileva modifiche (nessuna chiamata HTTP)
python3 tools/atlas-import.py scan ATLAS

# Mostra cosa verrebbe sincronizzato (nessuna chiamata HTTP, nessun aggiornamento dello stato)
python3 tools/atlas-import.py dry-run ABRAZO

# Sincronizza i documenti NEW / PENDING / FAILED verso Open WebUI
python3 tools/atlas-import.py sync NOEMA
```

Il nome del progetto (es. `ATLAS`) determina:

- la directory sorgente: `knowledge/ATLAS/`
- la Knowledge Collection di Open WebUI: `ATLAS` (creata automaticamente se assente)
- il file di stato: `.state/ATLAS.json`

### Variabili d'ambiente

| Variabile | Descrizione | Richiesta |
|---|---|---|
| `ATLAS_OPENWEBUI_URL` | URL base di Open WebUI (es. `http://localhost:3000`) | sì |
| `ATLAS_OPENWEBUI_EMAIL` | Email per l'autenticazione | sì |
| `ATLAS_OPENWEBUI_PASSWORD` | Password per l'autenticazione | sì |
| `ATLAS_PROCESS_TIMEOUT` | Timeout processing in secondi (default: `300`) | no |

### Flusso di sync

1. Scansiona `knowledge/<PROJECT>/` e calcola SHA256 per ogni file `.md`.
2. Confronta con `.state/<PROJECT>.json` → classifica NEW / MODIFIED / UNCHANGED / DELETED.
3. Autentica contro Open WebUI e individua la Knowledge Collection (la crea se non esiste).
4. Per ogni documento NEW (o PENDING / FAILED da run precedenti):
   - Upload multipart del file
   - Attesa elaborazione asincrona
   - Associazione alla Knowledge Collection
5. Salva lo stato aggiornato dopo ogni documento (il progresso non va perso in caso di interruzione).

### Aggiungere un nuovo progetto

```bash
mkdir -p knowledge/MIOPROGETTO
# aggiungere documenti .md
python3 tools/atlas-import.py sync MIOPROGETTO
```

La Knowledge Collection viene creata automaticamente in Open WebUI al primo sync.

---

## Test

```bash
python3 tools/test_atlas_import.py
```

La suite copre: configurazione, autenticazione, upload, processing, associazione, retry, stato atomico, rilevamento modifiche, parsing risposta API, multi-progetto.
