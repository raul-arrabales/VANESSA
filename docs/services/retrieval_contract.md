# Retrieval Contract (Backend <-> Agent Engine)

This note is the canonical source of truth for retrieval semantics shared by backend and agent engine.

It covers:

- the execution-scoped retrieval request contract
- normalized retrieval result fields
- scoring and fusion semantics
- ownership boundaries across backend, agent engine, and provider adapters

It does not cover frontend display rules or KB-admin UI behavior.

## Canonical Request

Retrieval is optional and execution-scoped.

Canonical request fields:

- `index`: active vector index or KB-backed provider index name
- `query`: retrieval query text
- `top_k`: requested result count
- `filters`: provider-agnostic exact-match filter bag
- `search_method`: `semantic | keyword | hybrid`
- `query_preprocessing`: `none | normalize`
- `hybrid_alpha`: optional hybrid semantic weight

Defaults:

- `top_k = 5`
- `search_method = semantic`
- `query_preprocessing = none`
- `hybrid_alpha = 0.5` only when `search_method = hybrid`

Canonical example:

```json
{
  "retrieval": {
    "index": "kb_product_docs",
    "query": "How does retrieval work?",
    "top_k": 5,
    "filters": {},
    "search_method": "hybrid",
    "query_preprocessing": "normalize",
    "hybrid_alpha": 0.5
  }
}
```

## Canonical Result Shape

Agent engine emits normalized retrieval call metadata plus per-result canonical relevance fields.

Canonical retrieval call metadata:

- `index`
- `query`
- `top_k`
- `search_method`
- `query_preprocessing`
- `hybrid_alpha?`
- `result_count`

Canonical retrieval result item:

- `id`
- `text`
- `metadata`
- `relevance_score`
- `relevance_kind`
- `relevance_components?`
- `score`
- `score_kind`

`relevance_kind` is one of:

- `similarity`
- `keyword_score`
- `hybrid_score`

`relevance_components`, when present, contains:

- `semantic_score?`
- `keyword_score?`

Canonical result example:

```json
{
  "retrieval_calls": [
    {
      "index": "kb_product_docs",
      "query": "how does retrieval work",
      "top_k": 5,
      "search_method": "hybrid",
      "query_preprocessing": "normalize",
      "hybrid_alpha": 0.5,
      "result_count": 1,
      "results": [
        {
          "id": "doc-1",
          "text": "Hybrid retrieval blends semantic recall with lexical precision.",
          "metadata": {
            "title": "Architecture Overview",
            "uri": "https://example.com/architecture"
          },
          "score": 0.94,
          "score_kind": "hybrid_score",
          "relevance_score": 0.94,
          "relevance_kind": "hybrid_score",
          "relevance_components": {
            "semantic_score": 0.91,
            "keyword_score": 0.97
          }
        }
      ]
    }
  ]
}
```

## Scoring Semantics

- `semantic`
  - uses the active `embeddings` binding plus the active `vector_store` binding
  - canonical `relevance_score` is normalized similarity
  - canonical `relevance_kind` is `similarity`

- `keyword`
  - uses the active `vector_store` binding without embeddings
  - canonical `relevance_score` is the provider keyword score used for ranking
  - canonical `relevance_kind` is `keyword_score`

- `hybrid`
  - runs semantic and keyword branches in backend/agent-engine retrieval logic, not in the provider contract
  - canonical `relevance_score` is the fused hybrid score
  - canonical `relevance_kind` is `hybrid_score`
  - `relevance_components.semantic_score` and `relevance_components.keyword_score` are the normalized branch scores actually used in fusion

Hybrid fusion rules:

- preprocess the query once using `query_preprocessing`
- over-fetch both branches with `min(max(top_k * 3, 10), 50)`
- normalize semantic branch as similarity
- normalize keyword branch per result set with min-max scaling
- if all keyword scores are equal and keyword results exist, assign `1.0` to all keyword matches
- fuse with `hybrid_score = alpha * semantic + (1 - alpha) * keyword`

## Ownership Boundaries

- Backend owns:
  - product/public retrieval request shaping
  - active KB resolution and deployment-runtime selection
  - forwarding canonical retrieval requests to agent engine
  - projecting retrieval results into knowledge-chat and playground-facing source payloads

- Agent engine owns:
  - execution-time retrieval normalization
  - semantic / keyword / hybrid branch execution
  - hybrid fusion
  - canonical `retrieval_calls[*]` result emission

- Provider adapters own:
  - translating canonical retrieval requests into provider-native query calls
  - returning provider-native `score` / `score_kind`
  - they do not define canonical hybrid behavior

## Provider Boundary and Non-Goals

- Provider-native hybrid search is not part of the canonical contract.
- Frontend score labels, snippets, numbering, and source-card presentation are not part of this note.
- Backend KB retrieval QA pages and knowledge chat may project retrieval results differently for UX, but they should preserve canonical retrieval semantics from this contract.

## Related Docs

- [Agent Execution Contract](agent_execution_contract.md)
- [Backend Service Notes](backend.md)
- [Agent Engine Service Notes](agent-engine.md)
