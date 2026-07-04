# Memory Roadmap — DeerFlow JE

**Statut :** Analyse préparatoire — aucune implémentation immédiate.
**Date :** 2026-07-04
**Version :** 1.0

---

## 1. Architecture actuelle

### 1.1 Vue d'ensemble

```
┌──────────────┐    ┌────────────────┐    ┌───────────────┐    ┌──────────────┐
│ MemoryMiddleware │───▶│ MemoryUpdateQueue │───▶│  MemoryUpdater │───▶│ MemoryStorage │
│ (middleware #14)  │    │ (debounce 30s)    │    │  (LLM extract)  │    │ (JSON file)    │
└──────────────┘    └────────────────┘    └───────────────┘    └──────────────┘
                                                                        │
                                                                        ▼
                                                               ┌──────────────┐
                                                               │ memory.json   │
                                                               │ per-user/agent│
                                                               └──────────────┘
                                                                        │
                                                                        ▼
┌────────────────────┐                                        ┌──────────────┐
│ DynamicContextMiddleware │◀─── format_memory_for_injection() ─│  load()       │
│ (injection <system-reminder>)  │                              └──────────────┘
└────────────────────┘
```

### 1.2 Composants

| Composant | Fichier | Rôle |
|-----------|---------|------|
| `MemoryMiddleware` | `agents/middlewares/memory_middleware.py` | Filtre les messages (user + AI final), envoie dans la queue |
| `MemoryUpdateQueue` | `agents/memory/queue.py` | Debounce 30s, déduplication par thread_id |
| `MemoryUpdater` | `agents/memory/updater.py` | Appelle un LLM pour extraire faits + résumés, sauvegarde atomique |
| `MemoryStorage` (ABC) | `agents/memory/storage.py` | Interface abstraite : `load()`, `reload()`, `save()` |
| `FileMemoryStorage` | `agents/memory/storage.py` | Implémentation JSON fichier avec cache mtime |
| `DynamicContextMiddleware` | `agents/middlewares/dynamic_context_middleware.py` | Injecte `<memory>` + `<current_date>` dans le prompt système |
| `format_memory_for_injection` | `agents/memory/prompt.py` | Formate les données mémoire dans la limite de tokens |

### 1.3 Structure des données (`memory.json`)

```json
{
  "version": "1.0",
  "lastUpdated": "2026-07-04T12:00:00Z",
  "user": {
    "workContext": {"summary": "...", "updatedAt": "..."},
    "personalContext": {"summary": "...", "updatedAt": "..."},
    "topOfMind": {"summary": "...", "updatedAt": "..."}
  },
  "history": {
    "recentMonths": {"summary": "...", "updatedAt": "..."},
    "earlierContext": {"summary": "...", "updatedAt": "..."},
    "longTermBackground": {"summary": "...", "updatedAt": "..."}
  },
  "facts": [
    {
      "id": "uuid",
      "content": "Utilise DeepSeek V4 pour le code",
      "category": "preference|knowledge|context|behavior|goal|correction",
      "confidence": 0.95,
      "createdAt": "2026-07-04T12:00:00Z",
      "source": "conversation"
    }
  ]
}
```

### 1.4 Points d'extension existants

| Point d'extension | Config | Mécanisme |
|-------------------|--------|-----------|
| `storage_class` | `config.yaml → memory.storage_class` | Classe Python chargée par réflexion (`importlib`) |
| `storage_path` | `config.yaml → memory.storage_path` | Chemin absolu ou relatif, isolation per-user |
| `model_name` | `config.yaml → memory.model_name` | Modèle LLM pour l'extraction des faits |
| `max_injection_tokens` | `config.yaml → memory.max_injection_tokens` | Budget tokens pour l'injection dans le prompt |
| `fact_confidence_threshold` | `config.yaml → memory.fact_confidence_threshold` | Seuil minimum de confiance pour sauvegarder |

### 1.5 Limites actuelles

1. **Pas de vectorisation** — les faits sont stockés en texte brut, la recherche est limitée au top-N par confiance
2. **Pas de RAG** — pas de retrieval augmenté, pas d'embeddings, pas de recherche sémantique
3. **Pas d'ingestion de documents** — les uploads sont éphémères (session-scoped), pas de persistance dans la mémoire
4. **Pas de graphe de connaissances** — les faits sont une liste plate, pas de relations entre entités
5. **Fenêtre de contexte limitée** — l'injection est plafonnée à 2000 tokens, les faits au-delà sont ignorés
6. **Extraction LLM uniquement** — dépend d'un appel LLM pour chaque mise à jour, pas d'extraction statique

---

## 2. Architecture cible

### 2.1 Vision

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           DEERFLOW MEMORY 2.0                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────────────┐   │
│  │   Docling    │    │   MemoryUpdater  │    │   MemoryMiddleware    │   │
│  │ (ingestion   │    │   (LLM extract)  │    │   (conversation)      │   │
│  │  documents)  │    └────────┬─────────┘    └───────────┬───────────┘   │
│  └──────┬───────┘             │                          │               │
│         │                     ▼                          ▼               │
│         │           ┌─────────────────────────────────────────┐         │
│         └──────────▶│           MemoryStorage (ABC)            │         │
│                     │  ┌─────────────────────────────────┐    │         │
│                     │  │  FileMemoryStorage (legacy)      │    │         │
│                     │  │  HybridVectorStorage  (nouveau)  │    │         │
│                     │  └─────────────────────────────────┘    │         │
│                     └────────────────┬────────────────────────┘         │
│                                      │                                   │
│                                      ▼                                   │
│                     ┌─────────────────────────────────────────┐         │
│                     │            LightRAG                      │         │
│                     │  ┌──────────┐  ┌────────────────────┐   │         │
│                     │  │ Vector DB│  │  Knowledge Graph   │   │         │
│                     │  │ (chroma/ │  │  (NetworkX/Neo4j)  │   │         │
│                     │  │  lancedb)│  │                    │   │         │
│                     │  └──────────┘  └────────────────────┘   │         │
│                     └────────────────┬────────────────────────┘         │
│                                      │                                   │
│                                      ▼                                   │
│                     ┌─────────────────────────────────────────┐         │
│                     │            Memori                        │         │
│                     │  (persistence, versioning, sync, UI)     │         │
│                     └─────────────────────────────────────────┘         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Les trois couches

#### Couche 1 : Docling — Ingestion de documents

**Rôle :** Convertir les documents uploadés (PDF, Word, Excel, PPT, Markdown) en texte structuré, prêt pour l'indexation.

**Pourquoi Docling :**
- IBM open-source, actif (2025+)
- Supporte PDF, DOCX, PPTX, XLSX, Markdown, HTML, Images
- Sortie en Markdown structuré avec métadonnées
- Extraction de tableaux, images, formules
- Pipeline de chunking intégré (HierarchicalChunker)

**Intégration DeerFlow :**
- Remplacer/augmenter `markitdown` dans le pipeline d'upload (`uploads/manager.py`)
- Ajouter un flag `persist_to_memory: true` dans la config uploads
- Les documents uploadés avec ce flag sont chunkés et indexés dans LightRAG

#### Couche 2 : LightRAG — Vectorisation + Graphe

**Rôle :** Indexer les faits mémoire et les documents dans une base hybride vecteur + graphe de connaissances.

**Pourquoi LightRAG :**
- Open-source, Python natif
- Indexation duale : embeddings vectoriels + graphe de connaissances (entités + relations)
- Supporte plusieurs backends vectoriels (ChromaDB, LanceDB, Milvus, Qdrant, Neo4j)
- Modes de retrieval : local (voisinage graphe), global (communautés), hybrid (mixte), naive (vectoriel pur)
- Incrémental : supporte l'ajout et la suppression de documents
- Léger : fonctionne en local sans infra externe (ChromaDB + NetworkX)

**Intégration DeerFlow :**
- Nouvelle classe `LightRAGMemoryStorage(MemoryStorage)` implémentant l'ABC
- Au `save()` : écrire dans le JSON legacy (compatibilité) + indexer dans LightRAG
- Au `load()` : requêter LightRAG pour les faits pertinents au contexte courant
- Nouveau champ config : `memory.lightrag` avec backend, mode de retrieval, top_k

#### Couche 3 : Memori — Persistance & UI

**Rôle :** Couche de persistance long-terme, versioning, synchronisation multi-appareils, interface de visualisation.

**Pourquoi Memori :**
- Projet JE (à créer ou adapter)
- Interface utilisateur pour explorer/éditer la mémoire
- Versioning des faits (historique, rollback)
- Export/import pour portabilité
- Optionnel : synchronisation cloud

**Intégration DeerFlow :**
- Phase 3 uniquement — dépend de LightRAG stable
- API Gateway : endpoints CRUD pour la mémoire
- Frontend : page `/memory` dans l'UI Next.js
- Format d'export standardisé (JSON/Markdown)

---

## 3. Gap Analysis

### 3.1 Ce qui existe déjà ✅

| Capacité | Statut | Détail |
|----------|--------|--------|
| Stockage JSON | ✅ | `FileMemoryStorage` avec cache mtime, isolation per-user |
| Extraction LLM | ✅ | `MemoryUpdater` avec debounce, déduplication, catégories |
| Injection prompt | ✅ | `DynamicContextMiddleware` avec budget tokens |
| Interface extensible | ✅ | `MemoryStorage` ABC, chargement par réflexion |
| Configuration | ✅ | `memory.*` dans `config.yaml`, hot-reload |
| Faits structurés | ✅ | Catégories, confiance, corrections |

### 3.2 Ce qui manque ❌

| Capacité | Priorité | Effort estimé | Dépendance |
|----------|----------|---------------|------------|
| Embeddings / vectorisation | P0 | 3-5 jours | LightRAG OU librairie embedding |
| Recherche sémantique | P0 | 2-3 jours | Vectorisation |
| Graphe de connaissances | P1 | 5-7 jours | LightRAG |
| Ingestion documents persistée | P1 | 2-3 jours | Docling + LightRAG |
| Retrieval contextuel (RAG) | P1 | 3-5 jours | Vectorisation |
| Interface mémoire (UI) | P2 | 5-7 jours | API Gateway |
| Versioning des faits | P2 | 2-3 jours | Memori |
| Synchro multi-appareils | P3 | 7-10 jours | Memori + cloud |
| Nettoyage automatique (faits obsolètes) | P2 | 1-2 jours | RAG |

### 3.3 Changements structurels nécessaires

1. **`MemoryStorage` ABC** — Ajouter des méthodes optionnelles :
   - `search(query: str, top_k: int) -> list[dict]` — recherche sémantique
   - `index_document(content: str, metadata: dict) -> str` — indexation document
   - `delete_fact(fact_id: str) -> bool` — suppression ciblée

2. **`MemoryConfig`** — Ajouter des champs :
   - `lightrag: LightRAGConfig` — configuration LightRAG
   - `embedding_model: str` — modèle d'embedding (ex: `text-embedding-3-small`)
   - `retrieval_top_k: int` — nombre de faits à récupérer

3. **`MemoryUpdater`** — Étendre pour :
   - Accepter des documents en entrée (pas seulement des conversations)
   - Appeler l'indexation vectorielle après sauvegarde

4. **Pipeline d'upload** — Ajouter un chemin :
   - Upload → Docling (conversion) → LightRAG (indexation) → `memory.json` (référence)

---

## 4. Plan d'implémentation

### Phase 4.1 — Fondations vectorielles (P0)

**Objectif :** Ajouter la recherche sémantique sans changer l'interface existante.

1. Ajouter `chromadb` ou `lancedb` comme dépendance optionnelle
2. Créer `HybridVectorStorage(MemoryStorage)` :
   - Hérite de `FileMemoryStorage` (garde le JSON)
   - Ajoute un index vectoriel pour les `facts[].content`
   - `search(query, top_k)` → retourne les faits les plus pertinents
3. Modifier `format_memory_for_injection()` pour utiliser la recherche sémantique
4. Ajouter la config `memory.vector` dans `config.yaml`

**Fichiers :**
- `agents/memory/vector_storage.py` (NOUVEAU)
- `agents/memory/embeddings.py` (NOUVEAU — wrapper embedding)
- `config/memory_config.py` (+ champs vector)
- `agents/memory/prompt.py` (modification injection)

### Phase 4.2 — LightRAG (P1)

**Objectif :** Remplacer l'index vectoriel simple par LightRAG (graphe + vecteur).

1. Ajouter `lightrag-hku` comme dépendance optionnelle
2. Créer `LightRAGMemoryStorage(MemoryStorage)`
3. Implémenter l'indexation duale (vecteur + graphe) des faits
4. Implémenter les 4 modes de retrieval LightRAG
5. Configurer le backend (ChromaDB local par défaut)

**Fichiers :**
- `agents/memory/lightrag_storage.py` (NOUVEAU)
- `config/lightrag_config.py` (NOUVEAU)
- `config.yaml` (+ section `memory.lightrag`)

### Phase 4.3 — Ingestion documents (P1)

**Objectif :** Persister les documents uploadés dans la mémoire.

1. Ajouter `docling` comme dépendance optionnelle
2. Créer un pipeline `DocumentIngestor` :
   - Conversion Docling (PDF/Word/Excel → Markdown structuré)
   - Chunking (HierarchicalChunker)
   - Indexation dans le storage mémoire
3. Modifier `uploads/manager.py` pour supporter `persist_to_memory`
4. Ajouter un tool agent `memorize_document` (accès au storage mémoire)

**Fichiers :**
- `agents/memory/document_ingestor.py` (NOUVEAU)
- `uploads/manager.py` (modification)
- `config.yaml` (+ section `memory.documents`)

### Phase 4.4 — Memori UI (P2)

**Objectif :** Interface utilisateur pour explorer et gérer la mémoire.

1. Ajouter des endpoints Gateway REST :
   - `GET /api/memory/facts` — liste paginée avec filtres
   - `PUT /api/memory/facts/{id}` — modifier un fait
   - `DELETE /api/memory/facts/{id}` — supprimer un fait
   - `GET /api/memory/search?q=...` — recherche sémantique
   - `POST /api/memory/export` — export JSON/Markdown
2. Créer une page frontend `/memory` :
   - Timeline des faits
   - Nuage de catégories
   - Recherche full-text + sémantique
   - Édition inline
3. Ajouter le versioning des faits (historique des modifications)

**Fichiers :**
- `app/gateway/routers/memory.py` (extension)
- `frontend/src/app/memory/` (NOUVEAU)
- `agents/memory/versioning.py` (NOUVEAU)

---

## 5. Configuration cible

### 5.1 `config.yaml` — section `memory` (cible)

```yaml
memory:
  enabled: true
  injection_enabled: true
  max_injection_tokens: 4000  # augmenté pour le RAG
  storage_class: "deerflow.agents.memory.lightrag_storage:LightRAGMemoryStorage"

  # Vectorisation
  embedding_model: "text-embedding-3-small"
  embedding_provider: "openai"  # openai | ollama | huggingface
  retrieval_top_k: 20
  retrieval_mode: "hybrid"  # local | global | hybrid | naive

  # LightRAG
  lightrag:
    enabled: true
    working_dir: ".deer-flow/lightrag"
    vector_backend: "chromadb"  # chromadb | lancedb | milvus | qdrant
    graph_backend: "networkx"   # networkx | neo4j
    chunk_size: 1200
    entity_extraction_model: "deepseek-v4-flash"

  # Ingestion documents
  documents:
    enabled: true
    persist_uploads: true
    chunker: "hierarchical"  # hierarchical | recursive | semantic
    max_document_tokens: 50000

  # Legacy (maintenu pour compatibilité)
  debounce_seconds: 30
  max_facts: 500  # augmenté grâce au stockage vectoriel
  fact_confidence_threshold: 0.7
```

---

## 6. Risques & Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| LightRAG instable ou non maintenu | Bloquant | Moyenne | Abstraire derrière l'ABC `MemoryStorage`, permettre un fallback simple (ChromaDB pur) |
| Coût embedding API | Budget | Élevée | Cache d'embeddings, modèle local (Ollama), embedding lazy (seulement au `search()`) |
| Complexité du graphe qui explose | Performance | Moyenne | Nettoyage périodique, TTL sur les faits, limite de nodes par entité |
| Incompatibilité avec le JSON legacy | Données | Basse | Garder `FileMemoryStorage` en écriture miroir, migration progressive |
| Docling dépendances lourdes | Build | Moyenne | Dépendance optionnelle (`pip install deerflow[memory]`) |

---

## 7. Références

- [LightRAG](https://github.com/HKUDS/LightRAG) — HKUDS, 10k+ stars
- [Docling](https://github.com/DS4SD/docling) — IBM Research, 25k+ stars
- [ChromaDB](https://github.com/chroma-core/chroma) — Vector database embedded
- [Memori](https://github.com/your-org/memori) — À créer/spécifier
