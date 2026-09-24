# LOINC → OCL ETL

Transforms a LOINC release (the CSV files LOINC ships in its release zip) into
OCL Bulk Import JSON-lines files: concepts (LOINC terms, LOINC Parts, Answer
Lists, Answers) and mappings (panel/element, question/answer, order-entry,
code-evolution, and associated-observations relationships), plus a
hierarchy-only file used to apply parent/child structure after import.

This process is meant to be repeated for every new LOINC release. This
document is the step-by-step for doing that.

## Prerequisites

- Python 3.13+ and [uv](https://docs.astral.sh/uv/) on your PATH.
- The new LOINC release, downloaded from https://loinc.org/downloads/ and
  unzipped somewhere under `ocl-content/LOINC/loinc-releases/` (e.g.
  `loinc-releases/Loinc_2.83/`). The zip's internal folder structure varies
  release to release, but the notebook searches recursively for the files it
  needs, so it's fine to unzip it as-is.
- No UMLS account/API key is required. Phase 5 (UMLS Enhancement) is
  optional CUI enrichment; the notebook runs correctly without it and simply
  skips that enrichment (see "Known limitations" below).

## One-time environment setup

From this directory (`LOINC/LOINC-OCL-ETL/`):

```bash
uv sync --group dev
```

This creates `.venv/` with the pipeline's own dependencies (pandas, numpy,
requests) plus the `dev` group needed to execute the notebook headlessly
(jupyter, nbconvert, ipykernel). If you only plan to run the notebook
interactively in an IDE with its own Jupyter integration, `uv sync` (without
`--group dev`) is enough — just point your IDE's Python interpreter at
`.venv/`.

## Running it for a new release

1. **Point the notebook at the new release.** Open
   [`loinc_to_ocl_transformer.ipynb`](loinc_to_ocl_transformer.ipynb), find
   the `source_loinc_directory` variable in the "LOINC FILE DISCOVERY AND
   COMPILATION" cell (Phase 0), and update the release folder name, e.g.:

   ```python
   source_loinc_directory = r"../loinc-releases/Loinc_2.83"  # UPDATE THIS PATH each release
   ```

   Leave `mode = 0` in the "CONFIGURATION & DEMO VARIABLES" cell — modes 1
   and 2 (test/demo data) are dead code left over from earlier development
   and don't currently work.

2. **Run the whole notebook top to bottom.** Either open it in Jupyter/VS
   Code and "Run All", or run it headlessly from the command line:

   ```bash
   uv run jupyter nbconvert --to notebook --execute \
     --output executed_<release>.ipynb \
     --ExecutePreprocessor.timeout=1800 \
     loinc_to_ocl_transformer.ipynb
   ```

   (`--output` writes to a separate file so you don't clutter the tracked
   notebook's git diff with cell outputs; delete that executed copy when
   you're done reviewing it. A full release run — roughly 250k concepts,
   190k mappings — takes on the order of a few minutes.)

   Cell 3 (Phase 0) copies the specific CSVs it needs out of the release
   folder into a local `Input/` directory; Phase 6 writes the final files
   to a local `output/` directory. Both are git-ignored — nothing here gets
   committed automatically.

3. **Sanity-check the output before handing it off.** At minimum, open
   `output/concepts.json` and `output/mappings.json` and check:
   - Row counts look right for the release (compare concept counts across
     concept classes to the previous release; they shouldn't swing wildly).
   - No literal `NaN` strings anywhere in the file.
   - Every mapping has both `from_concept_url` and `to_concept_url`.
   - Spot-check a `Has Answer` mapping and a `Map To` mapping for the
     `extras` you'd expect (Answer List ID/Type, COMMENT, etc.) — see
     "Known limitations" below for which mapping types are expected to have
     no extras at all.

   The notebook's own "Now What?" cell at the very end (Phase 6) also runs
   a dependency/hierarchy analysis and prints counts of concepts with
   missing or multiple parents — skim that output for anything that looks
   off relative to the previous release.

4. **Hand off `output/concepts.json`, `output/mappings.json`, and
   `output/hierarchy_only.json`.** These files are large (the 2.82 run
   produced a ~700MB concepts.json) and are not meant to be committed to
   git — share them with whoever is doing the actual OCL import (e.g. via a
   shared drive) rather than checking them in.

5. **Use the QA Load sample to smoke-test the import first.** Phase 7 (the
   last cell in the notebook) writes a small, representative subset to
   `QA-Load-files/` — `qa_concepts.json`, `qa_mappings.json`, and
   `qa_hierarchy_only.json`. It's small enough to commit, but is currently
   git-ignored (see `.gitignore`), so treat it like `output/`: a local,
   regenerated-every-run artifact, not a versioned fixture. Import it first
   against a QA OCL instance and confirm it loads cleanly before handing off
   the full files. See "What's
   in the QA Load sample" below for exactly what it contains.

6. **Follow the import steps in the notebook's final "Now What?" cell** for
   loading the Source, importing concepts/mappings via OCL's Bulk Import,
   and applying the hierarchy via the Admin API. That part of the process
   (and any pipeline reliability/monitoring work around it) is out of scope
   for this notebook.

## What the notebook actually does (phases)

1. **Phase 0 — Configuration & field mapping.** Locates and copies the
   release's CSVs into `Input/`, and defines the CSV-column → OCL-field
   mapping dictionaries for each concept/mapping type.
2. **Phase 1 — Data loading & validation.** Loads the CSVs into DataFrames
   and checks for any source columns that aren't covered by a mapping.
3. **Phase 2 — Concept creation.** Builds OCL Concept objects for LOINC
   terms, LOINC Parts, Answer Lists, and Answers, then adds any
   "multi-axial" LOINC Parts found in `ComponentHierarchyBySystem.csv` that
   aren't already covered by the primary Part file.
4. **Phase 3 — Mapping creation.** Builds OCL Mapping objects for
   Panel-to-Test ("Has Element"), Question-to-Answer ("Has Answer"),
   Ask-at-Order-Entry, Code Evolution ("Map To"), and Associated
   Observations relationships, per the `MAPPING_CONFIGS` dictionary. Also
   de-duplicates mappings and drops self-maps and rows with conflicting map
   types between the same two concepts (these get printed as warnings —
   review them, but they're expected to be non-zero).
5. **Phase 4 — Hierarchy creation.** Consolidates parent/child relationships
   (a concept can have more than one parent) and produces a dependency-
   ordered concept list for output.
6. **Phase 5 — UMLS enhancement (optional).** If a UMLS API key or a local
   `MRCONSO.RRF`-derived cache is configured, adds a UMLS CUI to each
   concept's `extras`. Without either, this phase is a no-op — every
   concept simply ends up with no CUI, which is the expected/normal case.
7. **Phase 6 — Output generation.** Writes `output/concepts.json`,
   `output/mappings.json`, and `output/hierarchy_only.json`.
8. **Phase 7 — QA Load sample.** Derives a small subset of the Phase 6
   output (see below) and writes it to `QA-Load-files/`.

Note: there's a separate, hand-maintained file in
[`Source-Import-files/`](Source-Import-files/) that defines the LOINC
*Source* resource itself in OCL (its `extras` property schema,
`supported_locales`, `hierarchy_root_url`, etc.) — the notebook doesn't
generate this. It only needs to change if the release adds/removes a field
this pipeline maps to `extras`, or adds/removes a linguistic-variant
language.

## What's in the QA Load sample

Phase 7 builds the QA subset directly from the same in-memory `concepts_data`
and `mappings_data` that Phase 6 writes to `output/`, so it's always
consistent with the full load for that run. It picks:

- An **anchor LOINC concept** that has both a real `Has Answer` mapping and a
  reasonably deep parent chain, then walks that chain all the way to `ROOT` —
  giving a genuine, complete hierarchy tree (`ROOT` → several `LOINC Part` /
  `LOINC Part (Multiaxial)` levels → the `LOINC` concept), not a synthetic
  one. For the 2.82 run this came out 7 levels deep, e.g.:

  ```
  ROOT -> LP29693-6 -> LP343406-7 -> LP7755-4 -> LP31426-7 -> LP267482-0 -> LP431707-1 -> 100041-3
  ```

- A few **sibling `LOINC` concepts** under that same immediate parent, to
  show a part with more than one child.
- The **Answer(s) and Answer List** reached by the anchor's `Has Answer`
  mapping, plus a few sibling Answers under the same Answer List.
- One **flat `LOINC Part`** example (a part whose parent is the
  `LOINC_PARTS_CONTAINER`, not part of the multi-axial tree), to represent
  that structurally different concept type.
- One example mapping of each remaining `map_type` (`Has Element`, `Map To`,
  `Ask At Order Entry`, `Associated Observations`), plus both endpoint
  concepts for each.
- `ROOT` and every `Container` concept (there are only 5 total).
- The **full ancestor closure** of everything above — every parent a sampled
  concept points to is also included, all the way to `ROOT` — plus any
  additional mapping whose both endpoints happen to already be in the
  sample, for a bit more realistic density without growing the concept set.

The 2.82 run produced 55 concepts (covering all 7 concept classes) and 6
mappings (one of each `map_type`). This is regenerated by Phase 7 on every
run, so re-run the notebook (or just re-run that one cell, once the earlier
cells' variables are in memory) after a new release to refresh it — don't
hand-edit these files.

## Known limitations (as of the 2.82 run)

- **Concepts with missing parents**: only the 4 root-exception LOINC Parts
  (`LP29693-6`, `LP29695-1`, `LP29696-9`, `LP7787-7`, whose real parent
  `LP432695-7` ("{component}") is intentionally omitted) show up here. This
  is expected — Phase 6 explicitly re-parents them to `ROOT`.
- **Hierarchical sort warning**: Phase 4/6 prints "Possible circular
  dependencies detected" and falls back to sorting the remaining ~180k
  concepts by dependency count rather than a strict topological sort, even
  though the dependency analysis reports 0 true cycles. This affects only
  the *order* of concepts within `concepts.json`, not the `parent_concept_urls`
  values themselves — not yet root-caused; worth another look if OCL's
  bulk importer turns out to be order-sensitive.
- **Mapping `extras`**: `Has Answer` and `Map To` mappings should always/
  sometimes carry `extras` respectively; `Ask At Order Entry` and
  `Associated Observations` mappings never carry `extras` by design (their
  `MAPPING_CONFIGS` entries define no extras fields). Most `Has Element`
  (Panel-to-Test) mappings having no `extras` is expected too — those
  fields (Required, Sequence, Cardinality, Answer List Override) are only
  populated for a subset of panel rows in the source CSV.
- **One blank `LOINC Answer` concept** (no `id`) can still slip through, but
  it isn't the one Phase 2 used to produce — it comes from the Phase 4
  multi-parent hierarchy consolidation step and appears at a rate of about
  1 in 250k concepts. Filter it out of the final output if you see it.
- **Fixed**: `extras.VersionLastChanged` was showing up as the literal
  string `"None"` on every Container/`ROOT`/`LOINC Part`/`LOINC Part
  (Multiaxial)`/Answer List/`LOINC Answer` concept (45 of 55 in the QA
  sample) — none of these concept types ever populate that field, so the
  underlying value was Python `None`, and the cleanup line in cell 41
  (`.astype(str).replace('nan', '')`) only caught the `NaN`-derived
  `"nan"` string, not `None`-derived `"None"`. Fixed by checking
  `pd.isna()` first. A handful of *genuine* literal `"None"` values do
  still appear in `extras` for a few `LOINC`/`LOINC Answer` concepts (e.g.
  `EXAMPLE_UNITS`, answer `DisplayText`) — those are real source-CSV text
  (LOINC's own convention for "no units"/"none of the above"-type answers),
  not a bug, and should be left alone.
- See the "Issues" note at the top of the notebook for the full list of
  what was fixed vs. still open, with the reasoning behind each.
