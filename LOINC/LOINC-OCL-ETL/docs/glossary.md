# Glossary

## LOINC terms

| Term | Meaning |
|---|---|
| **LOINC term** (LOINC code, `LOINC_NUM`) | A code for an observation or measurement, for example `2345-7` Glucose [Mass/volume] in Serum or Plasma. Format `nnnnn-n` (the last digit is a check digit). Becomes OCL class `LOINC`. |
| **Six axes** | The parts of a LOINC name: `COMPONENT` (what is measured), `PROPERTY` (kind of quantity), `TIME_ASPCT` (point in time vs interval), `SYSTEM` (specimen), `SCALE_TYP` (quantitative, ordinal, nominal, narrative, ...) and `METHOD_TYP`. Stored as extras. |
| **Fully-Specified Name (FSN)** | The six axes joined with `:`. |
| **Long Common Name (LCN)** | The human-readable full name. Used as the preferred English name in OCL. |
| **Short name**, **Display name**, **Consumer name** | Shorter or friendlier alternative names published by LOINC. |
| **LOINC Part** (`LP` code) | A reusable building block of LOINC names, for example a specific analyte or specimen. Format `LPnnnnn-n`. Parts are listed in `Part.csv`. |
| **Multi-axial hierarchy** | LOINC's browsable tree of Parts and terms, published as `ComponentHierarchyBySystem.csv`. A node can have more than one parent (a polyhierarchy). |
| **`{component}`** (`LP432695-7`) | LOINC's top node of the multi-axial hierarchy. Not created in OCL. `ROOT` replaces it. |
| **Answer List** (`LL` code) | A set of allowed answers for a question-type term, for example `LL1-9` Gender_M/F. Format `LLnnnn-n`. |
| **Answer** (`LA` code) | One allowed answer, reusable across lists, for example `LA1-0` UTD. Format `LAnnnnn-n`. |
| **Answer list link type** | How binding a list is for a term: `NORMATIVE` (only these answers), `PREFERRED`, or `EXAMPLE`. |
| **Externally defined answer list** | A list whose answers live in another code system (`ExtDefinedYN = Y`). It has no `LA` answers in the release. |
| **Panel** | A LOINC term that groups other terms (elements), for example a lab panel or survey form. Structure is in `PanelsAndForms.csv`. |
| **Ask at Order Entry (AOE)** | A question to ask when ordering a test. |
| **Associated Observations** | Other terms commonly reported alongside a given term. |
| **Map To** | LOINC's pointer from a deprecated term to its replacement. |
| **STATUS** | `ACTIVE`, `TRIAL`, `DISCOURAGED` or `DEPRECATED`. Only `DEPRECATED` makes a concept `retired` in OCL. |
| **Linguistic variant** | A translation of LOINC names for one locale, for example `esMX28LinguisticVariant.csv` for Spanish (Mexico). |

## OCL terms

| Term | Meaning |
|---|---|
| **Organization / Source** | OCL's owner and code-system containers. LOINC lives at `/orgs/Regenstrief/sources/LOINC/`. |
| **Concept** | A code in a Source, with `names`, `descriptions`, `extras`, `concept_class`, `datatype`, `retired`, and optional parents. |
| **`concept_class`** | A free-text category. This pipeline uses seven: `LOINC`, `LOINC Part`, `LOINC Part (Multiaxial)`, `Answer List`, `LOINC Answer`, `Container`, `Root`. |
| **`extras`** | Free-form key/value attributes on a concept or mapping. Most LOINC columns land here. |
| **`name_type`, `locale`, `locale_preferred`** | Per-name attributes. At most one name per locale should be preferred. |
| **Mapping** | A directed relationship between two concepts with a `map_type`. |
| **`parent_concept_urls` / hierarchy** | A concept's parents in the Source's browsable tree. |
| **`hierarchy_root_url`** | Source setting naming the top concept of its tree (`ROOT` here). |
| **Bulk Import** | OCL's JSON Lines import. Each line is one resource (`"type": "Concept"`, `"Mapping"`, `"Source"`, ...). |
| **`amend-hierarchy`** | Admin API endpoint `POST /admin/concepts/amend-hierarchy/`. It takes a `{parent_url: [child_urls]}` map and adds those parent links. |
| **Container** | A synthetic concept created by this pipeline to hold concepts that have no LOINC hierarchy parent. |

## UMLS terms

| Term | Meaning |
|---|---|
| **UMLS** | NLM's Unified Medical Language System, which links codes across terminologies. |
| **CUI** | Concept Unique Identifier (`Cnnnnnnn`). Stored as `external_id` and `extras.UMLS_CUI`. |
| **`MRCONSO.RRF`** | The UMLS file that lists every source code with its CUI. |
| **`SAB = LNC`** | The UMLS source abbreviation for LOINC. |
| **UTS** | UMLS Terminology Services, the NLM account and download portal. |
