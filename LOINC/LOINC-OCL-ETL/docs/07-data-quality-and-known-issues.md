# 07. Data Quality and Known Issues

This doc covers three things: the checks the notebook runs on its own, a checklist and
script for validating a run, and the list of open issues. Issues were found by reading
the notebook and profiling the 2.82 output.

## Checks built into the notebook

| Where | Check | Action |
|---|---|---|
| Phase 0 | Required files found | Stops if fewer than 4 of 7 are found |
| Phase 1 | Linguistic variant file name pattern and core columns | Skips bad files with a warning |
| Phase 2 | Source columns not covered by a field map | Prints a warning (does not stop) |
| Phase 2 | Blank `AnswerListId` / `AnswerStringId` | Row skipped for that concept type |
| Phase 3 | Mapping missing `from` or `to` | Dropped |
| Phase 3 | Duplicate (`from`, `to`, `map_type`) | Collapsed to the first row |
| Phase 3 | Same (`from`, `to`) with different `map_type` | **Reported only**, all kept |
| Phase 3 | Self-maps | Removed and counted by type |
| Phase 3 | `to_concept_url` containing `/concepts//` | Removed and counted by type |
| Phase 6 | Concepts still without a parent | Warning (should be none) |
| Phase 6 | Parent cycles, missing parents, multi-parent counts | Diagnostic printout |
| Phase 6 | CUI count before/after cleanup | Warns if any CUI was lost |
| Phase 6 | Concept row with blank `id` | Skipped |

## Verification checklist

After every full run, before handing off output:

- [ ] Run the script below against `output/`. It should report `Problems: none`. The
      only hierarchy key that is not a concept should be `LP432695-7` (issue H2).
- [ ] Compare class and map-type counts with the previous release (see
      [key numbers](README.md#key-numbers-loinc-282-run)). Investigate any class that
      moves more than a few percent.
- [ ] Open three random `LOINC` lines and check them:
  - English names: Long-Common preferred, Display, Short.
  - Translations are present.
  - Axis extras are present.
  - `parent_concept_urls` points to an `LP` code.
- [ ] Open a `Has Answer` mapping and check it has `Answer List ID`, `Answer List Type`
      and `Sequence`.
- [ ] Open a `Map To` mapping that has a `COMMENT`.
- [ ] Confirm that `UMLS_CUI` coverage matches what the Phase 5 log printed.
- [ ] Run the script against `QA-Load-files/` with the `qa_` prefix. It should also
      report `Problems: none`, with an empty dangling-key list.

```python
# validate_output.py  -  usage: python validate_output.py [folder] [file prefix]
#   python validate_output.py output
#   python validate_output.py QA-Load-files qa_
import json, sys
from collections import Counter

out = sys.argv[1] if len(sys.argv) > 1 else "output"
pre = sys.argv[2] if len(sys.argv) > 2 else ""  # pass "qa_" for QA-Load-files
prefix = "/orgs/Regenstrief/sources/LOINC/concepts/"
ids, classes, problems = set(), Counter(), Counter()
parents = []

with open(f"{out}/{pre}concepts.json", encoding="utf-8") as f:
    for line in f:
        if "NaN" in line: problems["concept line contains NaN"] += 1
        c = json.loads(line)
        if not c.get("id"): problems["concept without id"] += 1; continue
        if c["id"] in ids: problems["duplicate concept id"] += 1
        ids.add(c["id"]); classes[c.get("concept_class")] += 1
        if not c.get("names"): problems["concept without names"] += 1
        if c["id"] != "ROOT" and not c.get("parent_concept_urls"): problems["non-ROOT concept without parent"] += 1
        parents += c.get("parent_concept_urls", [])

map_types = Counter()
with open(f"{out}/{pre}mappings.json", encoding="utf-8") as f:
    for line in f:
        if "NaN" in line: problems["mapping line contains NaN"] += 1
        m = json.loads(line); map_types[m.get("map_type")] += 1
        for side in ("from_concept_url", "to_concept_url"):
            url = m.get(side) or ""
            if url[len(prefix):].rstrip("/") not in ids: problems[f"mapping {side} not a concept"] += 1

for p in parents:
    if p[len(prefix):].rstrip("/") not in ids: problems["parent URL not a concept"] += 1

with open(f"{out}/{pre}hierarchy_only.json", encoding="utf-8") as f:
    hierarchy = json.load(f)
dangling = [k for k in hierarchy if k[len(prefix):].rstrip("/") not in ids]

print("Concepts:", sum(classes.values()), dict(classes.most_common()))
print("Mappings:", sum(map_types.values()), dict(map_types.most_common()))
print("Hierarchy parent keys:", len(hierarchy), "edges:", sum(map(len, hierarchy.values())))
print("Hierarchy keys that are not concepts:", dangling)
print("Problems:", dict(problems) or "none")
```

Run it from `LOINC-OCL-ETL/`. It takes about a minute on the full output. The `NaN`
test is a plain substring match, so if it fires, check the flagged lines before
treating them as errors.

## Open issues

Severity key:

- **High:** data is wrong or missing in OCL.
- **Medium:** data is present but imperfect, or a process risk.
- **Low:** cosmetic or code hygiene.

### Output content

| ID | Severity | Issue | Evidence (2.82) | Suggested fix |
|---|---|---|---|---|
| C1 | High | `Has Element` extras `Sequence`, `Required` and `Cardinality` are never populated. The `Panel-to-Test` config reads `SequenceInPanel`, `Required`, `CardinalityMin` and `CardinalityMax`, and none of these columns exist in `PanelsAndForms.csv`. Panel order and required-ness are lost. (The top-level README describes these as only sometimes populated. In fact they never are.) | 0 of 55,326 `Has Element` mappings carry them | Map `SEQUENCE` to `Sequence` and `ObservationRequiredInPanel` to `Required`. Decide how to represent `QuestionCardinality` / `AnswerCardinality`. |
| C2 | Medium | `Root` and `Container` concepts lose their `extras` (`Code_Type`, `Code_in_Source`, `Container_For`) and `descriptions`. Phase 6 rebuilds `extras` from flat `extras.*` columns and `descriptions` from `description`, which overwrites the nested dicts these concepts were built with. | All 6 have neither field | Merge existing nested `extras`/`descriptions` in cell 42, as is already done for mappings. |
| C3 | Medium | `LOINC Part (Multiaxial)` concepts lose `extras.Code_in_Source` for the same reason. They never get `Code_Type` or `STATUS`, so they are the only classes you can't filter by `Code_Type`. | 41,693 concepts | Same fix as C2, and add `Code_Type: LOINC Part (Multiaxial)`. |
| C4 | Low | Integer fields are written as floats: `CLASSTYPE` `1.0`, `COMMON_TEST_RANK` `7688.0`, `COMMON_ORDER_RANK`, `HIERARCHY_SEQUENCE` `2.0`. The int conversion in Phase 2 is undone by later DataFrame merges. | Every `LOINC` concept | Cast in cell 42 when building `extras`. |
| C5 | Medium | An answer used in several lists gets only the first list as parent. Its concept-level `SequenceNumber`, `Score` and `LocalAnswerCode` also come from that first list, so they may not apply in other lists. | 4,127 answers in more than one list | Accept and document (per-list values are on `Has Answer` extras), or drop list-specific extras from the Answer concept, or allow multiple Answer List parents. |
| C6 | Medium | Terms bound to **externally defined** answer lists get no relationship at all. Their `Has Answer` rows have a blank target, so they are removed as malformed. The Answer List concept exists, but nothing links a term to it. | 224 term-to-list rows in 2.82 (186 after dedup in 2.81) | Emit a mapping from the term to the Answer List concept when `AnswerStringId` is blank. |
| C7 | Low | Translated names differ from LOINC conventions in four ways. The Fully-Specified name includes `CLASS` as a seventh part. The translated `LONG_COMMON_NAME` is typed `Display`, not `Long-Common`. No translated name is `locale_preferred`. There is no English Fully-Specified name. | All `LOINC` concepts | Decide the intended name model, then adjust cell 15 and the `locale_preferred` rules in cell 42. |
| C8 | Low | Duplicate `Has Element` rows with different `Answer List Override` values are meant to be merged, but `merge_extras` only parses string extras and they are dicts. The first row wins. | Affects duplicates only | Operate on dicts directly. |
| C9 | Low | The `COMMON_ORDER_RANK` transformation rule is a no-op: its `transformations` value is a set containing a lambda, not a dict. Zero values are still dropped by a separate check. | | Remove or rewrite the rule. |
| C10 | Low | One blank-id `LOINC Answer` row can appear during the Phase 4 consolidation (about 1 per run). It is now skipped when `concepts.json` is written, so it no longer reaches output. | Mitigated in cell 42 | Find the source in Phase 4. |

### Hierarchy

| ID | Severity | Issue | Evidence | Suggested fix |
|---|---|---|---|---|
| H1 | Medium | The topological sort gives up (`Possible circular dependencies detected`) and appends the whole multi-axial tree in arbitrary order. **Likely root cause:** at sort time, the four top-level Parts still point to the uncreated `LP432695-7`. Their re-parenting to `ROOT` only happens later, in cell 42. See [05](05-hierarchy-model.md#ordering-in-conceptsjson). | 180,578 unsorted in 2.81, which equals the unique hierarchy codes minus `LP432695-7` | Apply the root-exception override in cell 40, before sorting. |
| H2 | Low | `hierarchy_only.json` has a parent key for `LP432695-7`, which is not a concept. `amend-hierarchy` logs it and skips it, so it does no harm in OCL. | 1 key, 4 children | Filter it out in cell 43. |
| H3 | Medium | The hierarchy step in OCL only adds parents. A parent link that LOINC removes in a new release stays in OCL. | By design of `make_hierarchy` | Decide on a cleanup step for re-loads (for example, diff parent sets between releases). |
| H4 | Low | The four root-exception codes are hard-coded in three cells. | cells 40, 42, 43 | Define once in Phase 0. |

### Inputs and process

| ID | Severity | Issue | Suggested fix |
|---|---|---|---|
| P1 | Medium | Phase 0 takes the first matching file name anywhere in the release. `Loinc.csv`, `AnswerList.csv`, `LoincAnswerListLink.csv` and `MapTo.csv` each ship in two folders. They are identical in 2.82, but nothing checks this. | Prefer canonical folders, or assert that duplicates are identical. |
| P2 | Medium | The Source definition is maintained by hand and has drifted from the emitted extras (see [03](03-output-model.md#source-properties-vs-emitted-extras)). `supported_locales` must also be kept in sync with the linguistic variant files by hand. | Generate `supported_locales` (and optionally `properties`) from the run. |
| P3 | Low | The UMLS cache file is git-ignored only because `.gitignore` has `LOINC_*` and git on Windows is case-insensitive. On macOS or Linux it would show as untracked. | Add an explicit `loinc_cui_simple_lookup_*.json` pattern. |
| P4 | Low | `File Splitter.ipynb` has hard-coded paths from the 2.81 production load, and an `en-GB` to `en` substitution that is no longer needed. | Parameterize the paths, and default the substitution to off. |
| P5 | Low | Dead code: demo/test modes 1 and 2, the live UMLS API search path in `SimpleLOINCMapper` (never called with an API key), and the commented-out `fix_missing_parent_references`. | Remove, or move to an archive notebook. |
| P6 | Low | The top-level README says conflicting map types are "dropped". The notebook only reports them. | Correct the README wording. |

### Modeling gaps (not bugs)

These are LOINC content that the current model does not carry into OCL. Some are from
the "Known missing pieces" note in notebook cell 1.

- **LOINC-to-Part links** (`LoincPartLink_Primary/Supplementary.csv`). A term's parts
  are only stored as axis text in extras and implied by the hierarchy. There are no
  mappings from terms to their `LP` Part concepts.
- **Answer-list context** (`LoincAnswerListLink.ApplicableContext`). A list that
  applies only within a given panel is treated as universal.
- **Panel form details**: most `PanelsAndForms.csv` columns are unused (display names
  for forms, skip logic, entry type, conditions, coding instructions).
- **Group files** and the other accessory files listed in
  [02](02-input-model.md#release-files-the-pipeline-does-not-use).
- **Community mappings** (for example, to SNOMED or other code systems).
- **Mapping guidance** text for specific terms.
- **Richer container hierarchy** similar to the LOINC 2.71 OCL model: more Part
  containers, and Answer Lists placed under Parts.

## Fixed in earlier passes

Kept here so they are not re-investigated. Details are in the top-level README and
notebook cell 1.

- `en-GB` locales changed to `en` throughout.
- Mapping `extras` were being overwritten with an empty dict in Phase 6. `Has Answer`
  extras also referenced post-merge column names that never existed. Both fixed.
- A blank `LOINC Answer` above `LA1-0` from blank answer rows is now skipped in Phase 2.
- Phase 5 no longer crashes with `KeyError: 'external_id'` when no UMLS cache is
  available.
- The UMLS extractor wrote to a hard-coded cache file name that the reader did not use,
  which led to zero CUIs with no error. Fixed.
- `extras.VersionLastChanged` held the literal string `"None"` on non-term concepts.
  Fixed by checking `pd.isna` first. Literal `"None"` in some source text fields (for
  example `EXAMPLE_UNITS`) is real LOINC data and should be left alone.
