# Atlas — Retrieval Benchmark Framework

## Scopo

Questo framework misura la qualità del retrieval RAG nell'ecosistema Atlas: data una domanda, il retriever deve restituire il contesto giusto affinché l'LLM possa rispondere correttamente.

Il benchmark non testa l'LLM. Non testa la pipeline end-to-end nella sua interezza. Testa esclusivamente la capacità del retriever di trovare i documenti e i passaggi rilevanti per ciascuna domanda.

La qualità del retrieval è il fattore più critico in un sistema RAG: se il contesto recuperato è sbagliato, nessun modello — per quanto capace — può produrre una risposta corretta.

---

## Struttura

```
benchmark/
├── README.md                        # questo file
├── generic/                         # benchmark riutilizzabili tra progetti
└── abrazo/
    └── retrieval-benchmark.yaml    # dataset di valutazione ABRAZO
```

Ogni progetto Knowledge ha la propria sottodirectory. I benchmark `generic/` contengono domande di struttura applicabili a qualsiasi Knowledge Collection (es. "il sistema sa dove trovare la documentazione di architettura?") e vengono specializzati al momento dell'esecuzione.

---

## Formato YAML

```yaml
questions:
  - id: PRJ-CATEGORY-NNN          # identificatore univoco
    category: CATEGORY             # categoria tematica
    question: "Testo della domanda come la porrebbe un utente reale"
    expected_documents:            # documenti che DEVONO apparire nel contesto
      - nome-file.md
    must_contain:                  # termini chiave che devono comparire nel contesto recuperato
      - termine1
      - termine2
    must_not_contain:              # termini che NON devono comparire (opzionale)
      - termine_errato
    notes: "Nota su ambiguità, difficoltà, o perché questa domanda è rappresentativa"
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `id` | string | Identificatore univoco nel formato `PRJ-CATEGORY-NNN` |
| `category` | string | Categoria tematica (definita per progetto) |
| `question` | string | La domanda esatta posta al sistema |
| `expected_documents` | list | File che devono comparire nel contesto recuperato |
| `must_contain` | list | Termini che devono essere presenti nel contesto |
| `must_not_contain` | list | Termini che non devono comparire (per verifica di non-contaminazione) |
| `notes` | string | Note per chi interpreta i risultati (opzionale) |

---

## Principio: una sola variabile alla volta

Ogni esperimento di retrieval deve variare **un solo parametro** rispetto alla baseline. Esempi di parametri:

- dimensione dei chunk (`chunk_size`)
- sovrapposizione tra chunk (`chunk_overlap`)
- modello di embedding (`embedding_model`)
- numero di documenti recuperati (`top_k`)
- strategia di retrieval (similarity, BM25, hybrid)
- soglia di similarità (`score_threshold`)

**Perché**: se si cambiano due variabili contemporaneamente e il risultato migliora, non si sa quale delle due ha prodotto il miglioramento — e non si sa quale ha peggiorato l'altra metrica. Un benchmark non è un esperimento se non isola la causa dell'effetto osservato.

**Procedura consigliata**:
1. Eseguire il benchmark sulla configurazione baseline e registrare i risultati.
2. Cambiare un solo parametro.
3. Eseguire di nuovo il benchmark.
4. Confrontare. Solo allora procedere con la prossima variazione.

---

## Pipeline di valutazione

```
Domanda
   │
   ▼
Retriever ──────────────────────────────────────────────────────┐
   │  (embedding della domanda → ricerca vettoriale)            │
   │                                                            │
   ▼                                                            │
Contesto recuperato                                             │
   │  (top-k chunk dal vector store)                            │
   │                                                            │
   ▼                                                            │
Valutazione retrieval ◄─────────────────────────────────────────┘
   │
   ├── expected_documents ⊆ sorgenti nel contesto?   → Hit / Miss
   ├── must_contain ⊆ testo nel contesto?            → Pass / Fail
   └── must_not_contain ∩ testo nel contesto = ∅?   → Pass / Fail
```

### Metriche di retrieval

| Metrica | Definizione |
|---|---|
| **Document Hit Rate** | % di domande per cui tutti gli `expected_documents` sono stati recuperati |
| **Term Coverage** | % di domande per cui tutti i `must_contain` compaiono nel contesto |
| **Negative Precision** | % di domande per cui nessun `must_not_contain` compare nel contesto |
| **Full Pass Rate** | % di domande che superano tutti e tre i criteri |

---

## Aggiungere nuove domande

Una domanda di benchmark è valida se:

1. **È reale**: corrisponde a qualcosa che un utente potrebbe effettivamente chiedere al sistema.
2. **È verificabile**: la risposta corretta è presente nella documentazione esistente e identificabile senza ambiguità.
3. **Testa il retrieval**: la risposta richiede il recupero di un passaggio specifico, non è deducibile da conoscenza generale.
4. **Non è ridondante**: testa un aspetto diverso rispetto alle domande già presenti nella stessa categoria.

Non aggiungere domande la cui risposta non sia presente nei documenti della Knowledge Collection. Un retriever non può recuperare ciò che non esiste.

---

## Runner

Il dataset è indipendente dal motore RAG: lo stesso YAML può essere usato per valutare Open WebUI, qualsiasi altro retriever, o retriever futuri senza modificare le domande. Il dataset cambia solo se cambiano i documenti sorgente o i criteri di valutazione — non quando cambia il retriever che si sta testando.

I runner vivono in questo repository, nella directory `benchmark/`. Il primo runner sarà implementato nella milestone M3.2 e leggerà questo YAML per interrogare il retriever configurato, raccogliere i contesti restituiti e produrre i risultati di valutazione per ciascuna domanda.
