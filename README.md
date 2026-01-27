# What is _Moirai-SE_?

`Moirai-SE` is an open-source Python toolkit for **model composition** in Capella/ARCADIA-based MBSE: it merges independently-developed sub-product models into a coherent “product” model baseline and prepares the result for automation-friendly (CI) workflows.

| | |
|---| ---|
| ![alt](./examples/test%20data/Test%206/System1/[SAB]%20System11.jpg) | ![alt](./examples/test%20data/Test%206/System2/[SAB]%20System21.jpg) |
| ![alt](./examples/test%20data/Test%206/System3/[SAB]%20System31.jpg) | ![alt](./examples/test%20data/Test%206/[SAB]%20Structure1.jpg) |


## Key ideas

- Composition over “150% + filtering”: the final product model is treated as the emergence of independent models.
- Traceable automation: the merge process maintains a mapping of elements across source/base/destination models to support repeatable merges and stable cross-links.
- Extension-aware: the tool includes explicit handling for libraries and for REC Catalog / RPL-related elements (replica concepts) so that common Capella collaboration patterns remain workable after merging.

## What it currently does

- Merge structural model elements across Capella layers using dedicated processors.
- Merge exchanges/interfaces.
- Transfer Functional Chains.
- Merge and link libraries into the destination model.
- Merge extensions: REC Catalog and RPL elements and their linking structure.

## Architecture

### Intent

ARCADIA specifies horizontal separation of the design steps and provides robust decomposition tools like System-to-Subsystem Transition. Although it supports collaborative modelling, it remains monorepo-centric in practice, and true parallel development is often limited by the complexity of model diff/merge.

`moirai-se` introduces vertical separation: splitting a product into multiple repositories by product domains, features, or parts, then using CI to integrate and deliver an emergent product model.

### Implementation

The merge engine is built on `py-capellambse` and uses a processor/dispatcher architecture: per-element-type handlers implement clone + merge logic.

### Merge pipeline

At a high level the merge orchestration follows this sequence:

1. Load base, destination (target), and one or more source models.
2. Merge libraries into the destination model.
3. Merge extensions into the destination model:
   - REC / RPL Catalogs.
4. Merge model structure using dedicated processors.
5. Persist the destination model.

## Status

- Early-stage and evolving.  
  Depends on open PR-619 for `py-capellambse`: https://github.com/dbinfrago/py-capellambse/pull/619/  
- Many match rules are currently **name-based**; a more strict match is necessary.

# Usage

## Installation

```bash
git clone https://github.com/open-modeling/moirai-se.git
cd moirai-se
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e 
```

## Command-line

* Create cli configuration based on [example](./examples/empty_config.yaml)
* Setup logging based on [example](./examples/model-merge.sh)
* Run merger as 
  ```
  python -m arcadiaMergeTool <config.yaml>
  ```

### Logging

Logging can be fine-tuned by using env vars based on the qualified module name
Example: `arcadiaMergeTool/merger/elements` matches `LOG_LEVEL_ARCADIAMERGETOOL_MERGER_ELEMENTS`

# Contributing

Contributions are welcome.

 * Use issues for feature requests and bug reports.
 * Add features and bugfixes as PRs

# Roadmap

* [ ] Implement Behaviour merge
* [ ] Implement Requirements merge
* [ ] Implement PVMT based merge
* [ ] Implement Diagmams transition
* [ ] Implement generation of the overview diagrams
* [ ] Implement validation
* [ ] Add support for the interfaces based on cross-model REC/RPL entities
* [ ] Add VSS generation

# Licence
This project is licensed under the Eclipse Public License 2.0 (EPL-2.0).

(c) 2026 Julia WingedFox Lebedeva
