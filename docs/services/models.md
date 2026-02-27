# Models

Model assets are organized for local-first runtime and offline operation where required.

## LLM Models

- Host path pattern: `models/llm/<model-name>/...`
- Runtime mapping is controlled via compose environment configuration.

## KWS Models

- Wake-word model assets live under `models/kws/`.

Canonical model layout notes: [`models/README.md`](https://github.com/<org-or-user>/VANESSA/blob/main/models/README.md).

> Owner: LLM and KWS maintainers. Update cadence: whenever model directory conventions or runtime path contracts change.
