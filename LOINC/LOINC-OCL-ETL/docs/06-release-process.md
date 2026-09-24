# 06. Release Process

This is the end-to-end runbook for loading a new LOINC release into OCL. It goes from
downloading the release to checking the result in OCL. LOINC publishes new releases about
twice a year. Budget most of a day: the notebook takes minutes, but
review, the QA load and the production load take longer.

The top-level [README](../README.md) covers environment setup and running the notebook.
This doc adds what happens before and after.

```mermaid
flowchart LR
    A["Step 1: Get release"] --> B["Step 2: Refresh UMLS<br/>(optional)"]
    B --> C["Step 3: Configure notebook"]
    C --> D["Step 4: Run notebook"]
    D --> E["Step 5: Review run log"]
    E --> F["Step 6: Validate output"]
    F --> G["Step 7: Update Source<br/>definition if needed"]
    G --> H["Step 8: QA load"]
    H --> I["Step 9: Production load"]
    I --> J["Step 10: Post-load checks"]
    J --> K["Step 11: Commit and record"]
```

## 1. Get the release

1. Download the full LOINC release zip from <https://loinc.org/downloads/> (LOINC
   account required).
2. Unzip into `ocl-content/LOINC/loinc-releases/Loinc_<version>/`. Keep the zip's
   internal folders. Discovery searches recursively.
3. Skim LOINC's release notes and `AccessoryFiles/Loinc_<version>_DifferenceReport.pdf`
   for:
   - New or renamed columns in `Loinc.csv`, `Part.csv`, `AnswerList.csv`,
     `PanelsAndForms.csv` or `LoincAnswerListLink.csv`.
   - New or dropped linguistic variant locales.
   - Changes to `ComponentHierarchyBySystem.csv`, especially the top node
     `LP432695-7` and its four children.

## 2. Refresh UMLS (optional, recommended)

If a newer UMLS release than the last cache is available:

1. Download the MRCONSO-only file from UTS and place `MRCONSO.RRF` at `Input/MRCONSO.RRF`.
2. Set `umls_release` (Phase 5, "UMLS Cache Setup" cell) to the new label, for example
   `"2026AA"`.

A new label means a new cache file name, so the extractor runs again automatically.
Details are in the top-level README.

## 3. Configure the notebook

| Setting | Cell | Change |
|---|---|---|
| `source_loinc_directory` | Phase 0, "LOINC FILE DISCOVERY" | `../loinc-releases/Loinc_<version>` |
| `mode` | Phase 0, "CONFIGURATION" | Leave at `0` |
| `umls_release` | Phase 5, "UMLS Cache Setup" | Only if you refreshed UMLS |
| `global_organization`, `global_source` | Phase 0, "CONFIGURATION" | Leave as `Regenstrief` / `LOINC` unless loading to a different Source |

If step 1 found new columns, add them to the right field-mapping dict (cells 7 to 9) or
decide to leave them unmapped. Then update [04 Field mappings](04-field-mappings.md).

## 4. Run the notebook

Restart the kernel and run all cells, or run headlessly:

```bash
uv run jupyter nbconvert --to notebook --execute \
  --output executed_<version>.ipynb \
  --ExecutePreprocessor.timeout=1800 \
  loinc_to_ocl_transformer.ipynb
```

## 5. Review the run log

Read the printed output phase by phase. For each checkpoint below, the "Expect" column
shows what a healthy run looks like. It is based on 2.82.

| Phase | Look for | Expect |
|---|---|---|
| 0 | `Found N/7 required files` | 7/7 |
| 0 | `Found N linguistic variant files` | Locale files + 1 index file (22 in 2.82) |
| 0 | Which path each file was copied from | Canonical folder (see [02](02-input-model.md#where-the-inputs-come-from)); if a duplicate copy was picked, confirm it is identical |
| 1 | `N CSV files, M valid linguistic variant files` | M = locale count (21) |
| 2 | `Warning: Unmapped fields found in ...` | No warnings. Any warning means LOINC added a column; decide whether to map it. |
| 2 | Concept counts per class | Close to the previous release |
| 2 | `Number of missing concepts identified` | Multiaxial part count, close to previous (41,693) |
| 3 | Per-type mapping counts, `Consolidated N duplicate rows` | Close to previous |
| 3 | Conflicting map types | A short list. Review for anything new. |
| 3 | Self-maps removed | Mostly `Has Element` panel header rows (~2,700) |
| 3 | Malformed `/concepts//` rows | Only `Has Answer`, roughly the number of externally defined answer-list links (~190) |
| 4 | Concepts by number of parents | Similar shape to [05](05-hierarchy-model.md#multiple-parents) |
| 5 | `UMLS mapping coverage` | ~90% or higher with a current UMLS; 0 with no cache |
| 6 | Orphans assigned to containers | Only `Answer List` and `LOINC Part` |
| 6 | `Concepts with missing parents` | Exactly the 4 root exceptions |
| 6 | `Concepts in cycles` | 0 |
| 6 | `Possible circular dependencies detected` | Expected today; see [05](05-hierarchy-model.md#ordering-in-conceptsjson) |
| 7 | QA sample summary | All 7 classes, all 5 map types |

## 6. Validate the output

Run the checklist in [07 Data quality](07-data-quality-and-known-issues.md#verification-checklist).
At minimum confirm the following:

- No literal `NaN` in either file.
- Every mapping endpoint exists as a concept.
- Class and map-type counts are in line with the previous release.
- Spot-checked concepts and mappings look right.

## 7. Update the Source definition (only if needed)

Edit a copy of the newest file in [`Source-Import-files/`](../Source-Import-files/) when
any of these changed:

- **Locales:** add or remove entries in `supported_locales` to match the linguistic
  variant files.
- **New extras:** add a `properties` entry (and, if useful, a `filters` entry) for any
  new `extras` key that should be documented or filterable in OCL.

Save it as `LOINC-Source-Import LOINC_updated<DDMonYYYY>.json` and move the previous file
to `Archive/`. If the Source already exists in the target OCL environment, send the
changed parts as PUTs to the Source (see `Source-PUTs-LOINC-22Sep2025` for the shape)
rather than re-creating it.

## 8. QA load

Use the committed QA sample first. It is small, fast and consistent with the full run.

1. On a QA OCL instance, create the `LOINC` Source under the `Regenstrief` org, or
   update it, from the Source definition file.
2. Bulk Import `QA-Load-files/qa_concepts.json` (Hierarchy option unchecked).
3. Bulk Import `QA-Load-files/qa_mappings.json`.
4. POST `QA-Load-files/qa_hierarchy_only.json` to `/admin/concepts/amend-hierarchy/`
   (admin token).
5. In the OCL UI, browse from `ROOT` down the anchor chain printed by Phase 7. Open a
   concept of each class and a mapping of each type, and confirm names, extras and
   parents render as expected.

Fix anything found here before touching production.

## 9. Production load

These steps expand the notebook's final "Now What?" cell.

1. **Make sure the Source exists** with the current definition (step 7).
2. **Import only the `ROOT` concept** (the line with `"id": "ROOT"` from
   `concepts.json`).
3. **Set `hierarchy_root_url`** on the Source with a PUT, to
   `/orgs/Regenstrief/sources/LOINC/concepts/ROOT/`. Confirm it shows up on a GET of
   the Source. It has to reference a concept that already exists, which is why `ROOT`
   goes in first.
4. **Split large files if needed.** OCL's Bulk Import has upload size limits. Use
   [`File Splitter.ipynb`](../File%20Splitter.ipynb). For 2.81 the settings were:
   concepts in 30 MB chunks, mappings in 50,000-line chunks, hierarchy in 5 MB chunks.
   Update the hard-coded input/output paths and file-name prefixes in each cell first.
   Also set `text_to_find = ""`: the `en-GB` to `en` substitution is no longer needed,
   because the pipeline now emits `en`.
5. **Bulk Import concepts**, all chunks, with the **Hierarchy option unchecked**.
6. **Bulk Import mappings**, all chunks, after all concepts have finished. Mappings
   need both endpoints to exist.
7. **Apply the hierarchy.** POST `hierarchy_only.json` (or each chunk) to
   `/admin/concepts/amend-hierarchy/` with an admin token. Each call returns a task ID.
   Wait for tasks to finish.

> Re-loading into a Source that already holds an earlier LOINC release updates existing
> concepts in place and adds new ones. The hierarchy step only *adds* parent links. A
> parent removed by LOINC in the new release stays linked in OCL unless it is removed
> separately.

## 10. Post-load checks

- **Counts:** concepts per `concept_class` and mappings per `map_type` in OCL match the
  file counts.
- **Containers:** open each container. `LOINC_PARTS_CONTAINER` and
  `ANSWER_LISTS_CONTAINER` should hold roughly the counts in
  [03](03-output-model.md#root-and-container). `LOINC_CONTAINER` and
  `LOINC_ANSWERS_CONTAINER` should be empty or nearly so. A large number there means
  hierarchy parents failed to apply.
- **Hierarchy:** browse `ROOT` > Laboratory > ... down to a LOINC term.
- **Extras:** open one concept per class and check that extras display cleanly. Look
  for `NaN`, `None`, or floats like `1.0` where integers are expected (the float issue
  is known, see [07](07-data-quality-and-known-issues.md)).
- **Translations:** switch the UI locale, or check `names`, on a term with many
  translations.
- **Search and filters:** the Source's configured filters (CLASS, STATUS, SYSTEM, ...)
  return results.

## 11. Commit and record

In `ocl-content`, commit:

- The notebook, with `source_loinc_directory` and `umls_release` updated. Prefer a
  clean copy without large outputs. Keep `executed_<version>.ipynb` out of git.
- `QA-Load-files/` regenerated by Phase 7.
- Any Source definition change.
- Updated docs: the key numbers in [docs/README.md](README.md) and any new or resolved
  issues in [07](07-data-quality-and-known-issues.md).

Do **not** commit `Input/`, `output/`, `MRCONSO.RRF` or the UMLS cache. They are
git-ignored, large, and in the RRF's case licensed. Share `output/` through the team's
shared drive with whoever runs the OCL load.
