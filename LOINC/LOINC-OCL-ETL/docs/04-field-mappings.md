# 04. Field Mappings

This doc is the column-by-column crosswalk from LOINC CSV to OCL fields. It mirrors the
configuration dictionaries in notebook cells 7 to 12. If you change those dictionaries,
change this doc too.

## How the concept builder reads a field map

Concept field maps are plain dicts: `{ "<CSV column>": "<target>" }` or
`{ "<CSV column>": ["<target 1>", "<target 2>"] }`. A column can feed several targets.
Target strings use a flat notation that Phase 6 later nests:

| Target notation | Becomes in `concepts.json` |
|---|---|
| `id`, `datatype`, `retired`, ... | Top-level field of the same name |
| `extras.<KEY>` | `extras: { "<KEY>": value }` |
| `names.<NameType>.<locale>[<n>]` | An entry in `names`: `{name, name_type: NameType, locale, locale_preferred}` |
| `description` | `descriptions: [{description, locale: "en", description_type: "Full"}]` |

For each source row, `create_ocl_concept_from_row()` applies three steps in order:

1. **Fixed values:** the class's `fixed_values_*` dict (`type`, `concept_class`,
   `source`, `owner`, `extras.Code_Type`, and so on).
2. **Field map:** copies each non-null column into its targets. Blank strings are
   copied too, and dropped later at output.
3. **Transformation rules:** overwrite specific targets based on the source value.

Every concept's `source` is `LOINC`, `owner` is `Regenstrief` and `owner_type` is
`Organization`. These come from `global_source` and `global_organization` in cell 4,
so they are not repeated in the tables below.

## `LOINC` (cell 7: `loinc_to_ocl_mapping`, `fixed_values_loinc`)

Fixed: `type: Concept`, `concept_class: LOINC`, `extras.Code_Type: LOINC`.

| `Loinc.csv` column | Target(s) |
|---|---|
| `LOINC_NUM` | `id`, `extras.Code_in_Source` |
| `LONG_COMMON_NAME` | `names.Long-Common.en[1]`, `extras.LONG_COMMON_NAME` |
| `DisplayName` | `names.Display.en[1]`, `extras.DisplayName` |
| `SHORTNAME` | `names.Short.en[1]`, `extras.SHORTNAME` |
| `CONSUMER_NAME` | `names.Consumer.en[1]`, `extras.CONSUMER_NAME` |
| `SCALE_TYP` | `datatype`, `extras.SCALE_TYP` |
| `STATUS` | `retired` (via rule), `extras.STATUS` |
| `DefinitionDescription` | `description`, `extras.DEFINITION_DESCRIPTION` |
| `COMPONENT`, `PROPERTY`, `TIME_ASPCT`, `SYSTEM`, `METHOD_TYP`, `CLASS`, `CLASSTYPE`, `VersionFirstReleased`, `VersionLastChanged`, `ORDER_OBS`, `HL7_FIELD_SUBFIELD_ID`, `EXTERNAL_COPYRIGHT_NOTICE`, `EXTERNAL_COPYRIGHT_LINK`, `SURVEY_QUEST_TEXT`, `SURVEY_QUEST_SRC`, `UNITSREQUIRED`, `RELATEDNAMES2`, `ValidHL7AttachmentRequest`, `CHNG_TYPE`, `STATUS_TEXT`, `STATUS_REASON`, `PanelType`, `CHANGE_REASON_PUBLIC`, `COMMON_TEST_RANK`, `COMMON_ORDER_RANK`, `AskAtOrderEntry`, `AssociatedObservations`, `EXAMPLE_UNITS`, `EXMPL_ANSWERS`, `EXAMPLE_UCUM_UNITS`, `HL7_ATTACHMENT_STRUCTURE`, `FORMULA` | `extras.<same name>` |

Added later in the pipeline:

| Target | Added by | From |
|---|---|---|
| `names.<Type>.<locale>[n]` for translated names | Phase 1 (cell 15) | Linguistic variant files, see [below](#linguistic-variants) |
| `parent_concept_urls` | Phase 4 | `ComponentHierarchyBySystem.IMMEDIATE_PARENT` |
| `extras.PATH_TO_ROOT` | Phase 4 | `ComponentHierarchyBySystem.PATH_TO_ROOT` |
| `extras.HIERARCHY_SEQUENCE` | Phase 4 | `ComponentHierarchyBySystem.SEQUENCE` |
| `external_id`, `extras.UMLS_CUI` | Phase 5 | UMLS cache lookup by `id` |

## `LOINC Part` (cell 8: `loinc_part_to_ocl_mapping`, `fixed_values_loinc_parts`)

Fixed: `type: Concept`, `concept_class: LOINC Part`, `datatype: N/A`,
`extras.Code_Type: LOINC Part`. One concept per unique `PartNumber` (first row wins).

| `Part.csv` column | Target(s) |
|---|---|
| `PartNumber` | `id`, `extras.Code_in_Source` |
| `PartName` | `names.Long-Common.en[1]`, `extras.LONG_COMMON_NAME` |
| `PartDisplayName` | `names.Display.en[1]`, `extras.PartDisplayName` |
| `Status` | `retired` (via rule), `extras.STATUS` |
| `PartTypeName` | `extras.PartTypeName` |

Later: `parent_concept_urls`, `extras.PATH_TO_ROOT`, `extras.HIERARCHY_SEQUENCE` (only
for Parts found in the hierarchy file), `external_id`, `extras.UMLS_CUI`.

## `Answer List` (cell 9: `answer_list_to_ocl_mapping`, `fixed_values_answer_list`)

Fixed: `type: Concept`, `concept_class: Answer List`, `datatype: N/A`,
`retired: false`, `extras.Code_Type: LOINC Answer List`. One concept per unique
non-null `AnswerListId`.

| `AnswerList.csv` column | Target(s) |
|---|---|
| `AnswerListId` | `id`, `extras.Code_in_Source` |
| `AnswerListName` | `names.Display.en[1]`, `extras.AnswerListName` |
| `AnswerListOID` | `extras.AnswerListOID` |
| `ExtDefinedYN` | `extras.ExtDefinedYN` |
| `ExtDefinedAnswerListCodeSystem` | `extras.ExtDefinedAnswerListCodeSystem` |
| `ExtDefinedAnswerListLink` | `extras.ExtDefinedAnswerListLink` |

## `LOINC Answer` (cell 9: `answer_to_ocl_mapping`, `fixed_values_answer`)

Fixed: `type: Concept`, `concept_class: LOINC Answer`, `datatype: N/A`,
`retired: false`, `extras.Code_Type: LOINC Answer`. One concept per unique non-null
`AnswerStringId` (first row wins). The builder also records `ParentAnswerListId` (the
row's `AnswerListId`), which Phase 4 turns into the parent. The working column is
dropped before output.

| `AnswerList.csv` column | Target(s) |
|---|---|
| `AnswerStringId` | `id`, `extras.Code_in_Source` |
| `DisplayText` | `names.Display.en[1]`, `extras.DisplayText` |
| `ExtCodeDisplayName` | `names.External.en[1]`, `extras.ExtCodeDisplayName` |
| `LocalAnswerCode`, `LocalAnswerCodeSystem`, `SequenceNumber`, `ExtCodeId`, `ExtCodeSystem`, `ExtCodeSystemVersion`, `ExtCodeSystemCopyrightNotice`, `SubsequentTextPrompt`, `Description`, `Score` | `extras.<same name>` |

> `Description` on an Answer goes to `extras.Description`, not to OCL `descriptions`.
> Only `LOINC` terms get OCL descriptions.

## `LOINC Part (Multiaxial)` (cell 25: `create_ocl_concept_from_hierarchy_row`)

Built directly as nested dicts, not through a field map. Created for every unique `CODE`
in `ComponentHierarchyBySystem.csv` that starts with `LP`, is not already a concept, and
is not `LP432695-7`.

| Hierarchy column | Target |
|---|---|
| `CODE` | `id`, `extras.Code_in_Source` (the extra is lost at output, see [07](07-data-quality-and-known-issues.md)) |
| `CODE_TEXT` | `names: [{name, name_type: Long-Common, locale: en, locale_preferred: true}]` |
| `IMMEDIATE_PARENT` | `parent_concept_urls` |
| `PATH_TO_ROOT` | `extras.PATH_TO_ROOT` (lost at output; re-added by the Phase 4 merge) |
| `SEQUENCE` | `extras.HIERARCHY_SEQUENCE` (same) |

Fixed: `type: Concept`, `datatype: N/A`, `retired: false`.

## `Root` and `Container` (cell 40: `create_container_concepts`)

Hard-coded. See the table in [03](03-output-model.md#root-and-container).

## Transformation rules (cell 10: `transformation_rules`)

| Source column | Target | Rule |
|---|---|---|
| `STATUS` (LOINC), `Status` (Part) | `retired` | `DEPRECATED` becomes `true`. `ACTIVE`, `TRIAL` and `DISCOURAGED` become `false`. Any other value leaves `retired` unset. |
| `COMMON_TEST_RANK` | `extras.COMMON_TEST_RANK` | `0` is omitted. The rule maps `"0"`/`""` to `None`, but values load as numbers, so the omission actually comes from an explicit `== 0` skip in the builder. |
| `COMMON_ORDER_RANK` | `extras.COMMON_ORDER_RANK` | Intended to convert decimal strings to integers and drop 0. The rule's `transformations` is a set containing a lambda rather than a dict, so it never matches. The `== 0` skip in the builder is what actually drops zeros. |

Type handling: `CLASSTYPE`, `COMMON_TEST_RANK`, `COMMON_ORDER_RANK` and
`HIERARCHY_SEQUENCE` are converted from float to int when built. Later DataFrame merges
turn them back into floats, so they are written as `1.0`, `7688.0`, and so on. See
[07](07-data-quality-and-known-issues.md).

## Linguistic variants

Cell 15 converts each `<ll><CC><n>LinguisticVariant.csv` file into name rows. The locale
is `<ll>-<CC>`, taken from the file name. Per LOINC term and locale:

| Name type | Built from | Condition |
|---|---|---|
| `Fully-Specified` | `COMPONENT:PROPERTY:TIME_ASPCT:SYSTEM:SCALE_TYP:METHOD_TYP:CLASS`, skipping blank parts | At least one of those columns exists |
| `Short` | `SHORTNAME` | Non-blank |
| `Display` | `LONG_COMMON_NAME` | Non-blank |
| `Related` | `RELATEDNAMES2` | Non-blank |

The rows are numbered within (`LOINC_NUM`, name type, locale). They are pivoted to
columns named `names.<NameType>.<locale>[<n>]` and left-joined onto `Loinc.csv` rows.
In practice `n` is always 1, because each file has one row per term.

Two things differ from LOINC's own conventions:

- LOINC's Fully-Specified Name is the six axes (`COMPONENT` through `METHOD_TYP`)
  joined with `:`. This pipeline also appends `CLASS`.
- The translated `LONG_COMMON_NAME` becomes name type `Display`, not `Long-Common`.

### `locale_preferred` rules (cell 42)

When Phase 6 turns the flat `names.*` columns into the `names` list, it sets
`locale_preferred` as follows:

- `Long-Common` names on `LOINC` concepts: `true`.
- `Display` names on `Answer List`, `LOINC Answer`, `Root`, `Container`, `LOINC Part`:
  `true`.
- Everything else: `false`. This includes every translated name.

`LOINC Part (Multiaxial)`, `Root` and `Container` names are built as nested lists in
code rather than flat columns, so they keep the flag they were created with (`true` on
the primary name).

## Mapping configs (cell 11: `MAPPING_CONFIGS`)

Each config has a list of `field_mappings`. Each entry sets one `ocl_field` in one of
three ways:

- `source_value`: a constant.
- `source_field`: a column value, optionally passed through a `rule`.
- `source_field_min` + `source_field_max` + `rule`: two columns combined.

`ocl_field` values of the form `extras["Key"]` go into the mapping's `extras` dict.
Every config sets `type: Mapping`, its `map_type`, `source: LOINC`,
`owner_type: Organization` and `owner: Regenstrief`. The `from`/`to` rule is always
`CONCEPT_URL_PREFIX + value + "/"`.

| Config key | `map_type` | Input rows | `from_concept_url` | `to_concept_url` | Extras (`extras["..."]` from column) |
|---|---|---|---|---|---|
| `Panel-to-Test` | `Has Element` | `PanelsAndForms.csv` | `ParentLoinc` | `Loinc` | `Sequence` from `SequenceInPanel`\*; `Required` from `Required`\*; `Cardinality` = `CardinalityMin..CardinalityMax`\*; `Answer List Override` from `AnswerListIdOverride`; `Answer List Type Override` from `AnswerListTypeOverride` |
| `Question-to-Answer` | `Has Answer` | `LoincAnswerListLink.csv` inner-joined to `AnswerList.csv` on `AnswerListId` | `LoincNumber` | `AnswerStringId` | `Answer List ID` from `AnswerListId`; `Answer List Type` from `AnswerListLinkType`; `Sequence` from `SequenceNumber`; `Score` from `Score`; `Local Answer Code` from `LocalAnswerCode` |
| `Ask at Order Entry` | `Ask At Order Entry` | `Loinc.csv` rows with non-blank `AskAtOrderEntry` | `LOINC_NUM` | `AskAtOrderEntry` | none |
| `Code Evolution` | `Map To` | `MapTo.csv` | `LOINC` | `MAP_TO` | `COMMENT` from `COMMENT` |
| `Associated Observations` | `Associated Observations` | `Loinc.csv`, one row per code in `AssociatedObservations` | `LOINC_NUM` | each code | none |

\* These columns do not exist in `PanelsAndForms.csv`, so these extras are never
populated. See [02](02-input-model.md#panelsandformscsv-panel-structure).

`Associated Observations` preprocessing: the field is split on `;`, `,` or `|`. Each
piece is trimmed and kept only if it matches `^\d{1,5}-\d{1,2}$`. `AskAtOrderEntry` is
not split. It held a single code in every 2.82 row.

### Mapping post-processing (cells 29 to 31, 42)

Applied in order:

1. **Deduplicate** on (`from_concept_url`, `to_concept_url`, `map_type`), keeping the
   first row. The merge function was meant to combine differing
   `Answer List Override` values, but it only handles extras stored as strings, and
   extras are dicts. In practice the first row's extras win.
2. **Report conflicts**: pairs with more than one `map_type` are printed. Nothing is
   removed.
3. **Remove self-maps** (`from == to`). These are mostly panel header rows in
   `PanelsAndForms.csv`.
4. **Strip empty extras**: specific keys with value `None`/`""` are removed.
5. **Remove malformed targets**: any `to_concept_url` containing `/concepts//` (a blank
   code). These are the `Has Answer` rows for externally defined answer lists that have
   no `AnswerStringId`.
6. **Output cleanup**: in Phase 6, `None`/NaN/empty extras are dropped, and an empty
   `extras` dict is omitted entirely.
