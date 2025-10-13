# WHO-ATC Content Pipeline for OCL

This repository contains the pipeline and documentation for obtaining, processing, and loading WHO Anatomical Therapeutic Chemical (ATC) classification content into Open Concept Lab (OCL).

## About WHO-ATC

The Anatomical Therapeutic Chemical (ATC) classification system is maintained by the WHO Collaborating Centre for Drug Statistics Methodology. It divides active pharmaceutical substances into different groups according to the organ or system on which they act and their therapeutic, pharmacological, and chemical properties.

The ATC system has five levels:
- **Level 1**: Main anatomical or pharmacological group (14 groups)
- **Level 2**: Therapeutic/pharmacological subgroup
- **Level 3**: Chemical/pharmacological/therapeutic subgroup
- **Level 4**: Chemical/pharmacological/therapeutic subgroup
- **Level 5**: Chemical substance (individual drug)

## Data Sources

### Primary Source
- **NCBO BioPortal**: [https://bioportal.bioontology.org/ontologies/ATC](https://bioportal.bioontology.org/ontologies/ATC)
  - Most recent version: January 16, 2025
  - Format: CSV file containing the complete ATC hierarchy
  - File: `ATC.csv`

### Supporting Resources
- **WHO ATC/DDD Index**: [https://atcddd.fhi.no/atc_ddd_index/](https://atcddd.fhi.no/atc_ddd_index/)
  - Used for reference and validation
  - Contains the official 2025 ATC content

- **ATC Alterations Lists**: [https://atcddd.fhi.no/atc_ddd_alterations__cumulative/atc_alterations/](https://atcddd.fhi.no/atc_ddd_alterations__cumulative/atc_alterations/)
  - Documents changes between ATC versions
  - Useful for tracking deprecated and new codes

## OCL Repository
- **OCL Source**: [https://app.openconceptlab.org/#/orgs/WHO/sources/WHOATC/about](https://app.openconceptlab.org/#/orgs/WHO/sources/WHOATC/about)
- **Owner**: WHO Organization
- **Source ID**: WHOATC

## Processing Pipeline

### Tools Used
- **OpenRefine**: Used for data transformation and cleanup
- **Custom Scripts**: JSON-based transformation script for OpenRefine

### Pipeline Steps

#### 1. Source Data Acquisition
Download the latest ATC.csv file from NCBO BioPortal:
```
Source: https://bioportal.bioontology.org/ontologies/ATC
File: ATC.csv
```

#### 2. Data Transformation
Use OpenRefine with the provided transformation script to convert the BioPortal format to OCL-compatible CSV:

**Input**: `ATC.csv` (from BioPortal)  
**Process**: Apply `OpenRefine Script - WHO ATC for OCL.json`  
**Output**: `WHO-ATC-2025-concepts.csv`

The transformation script:
- Converts BioPortal's hierarchical structure to OCL's flat concept format
- Creates proper parent-child relationships using `parent_concept_urls`
- Adds OCL-required fields: `resource_type`, `owner_id`, `owner_type`, `source`
- Sets concept metadata:
  - `concept_class`: "Drug"
  - `datatype`: "None"
  - Custom attributes: `CUI`, `ATC_LEVEL`, `Is_Drug_Class`
- Handles both fully specified names and short names

#### 3. Identify Retired Concepts
Compare the new concept list with the previous version in OCL to identify concepts that no longer exist:

**Process**:
1. Export current concepts from OCL's WHOATC source
2. Compare concept IDs between versions
3. Generate retirement CSV for concepts present in old version but absent in new version

**Output**: `Concepts to Retire from Previous WHOATC before 2025 load.csv`

**Important**: Retired concepts are marked with `retired: TRUE` but remain in the source to:
- Maintain historical record
- Support CIEL mapping workflows
- Enable identification of mappings requiring replacement

#### 4. OCL Data Loading
Load the transformed data into OCL in the following order:

1. **Load New/Updated Concepts**:
   - File: `WHO-ATC-2025-concepts.csv`
   - Contains all active ATC concepts with hierarchy

2. **Retire Obsolete Concepts**:
   - File: `Concepts to Retire from Previous WHOATC before 2025 load.csv`
   - Marks deprecated concepts as retired without deletion

## File Structure

```
WHO ATC 2025/
├── ATC.csv                                                    # Raw source from BioPortal
├── ATC.csv.gz                                                 # Compressed source file
├── OpenRefine Script - WHO ATC for OCL.json                   # Transformation script
├── WHO-ATC-2025.openrefine.tar.gz                            # OpenRefine project archive
├── WHO-ATC-2025-concepts.csv                                 # OCL-formatted concepts (ready to load)
└── Concepts to Retire from Previous WHOATC before 2025 load.csv  # Retirement list
```

## CSV Format Details

### Concepts CSV Structure
```csv
resource_type,owner_id,owner_type,source,concept_class,datatype,id,name[1],name_type[1],name_type[2],name[2],retired,attr:CUI,parent_concept_urls,attr:ATC_LEVEL,attr:Is_Drug_Class
Concept,WHO,Organization,WHOATC,Drug,None,A,ALIMENTARY TRACT AND METABOLISM DRUGS,Fully Specified,Short,ALIMENTARY TRACT AND METABOLISM,FALSE,C3653992,/orgs/WHO/sources/WHOATC/concepts/Root/,1,Y
```

### Key Fields
- **resource_type**: Always "Concept"
- **owner_id**: "WHO"
- **owner_type**: "Organization"
- **source**: "WHOATC"
- **concept_class**: "Drug"
- **datatype**: "None"
- **id**: ATC code (e.g., "A", "A01", "A01AA", "A01AA01")
- **name[1]**: Primary name (Fully Specified)
- **name[2]**: Short name (if different)
- **retired**: "TRUE" or "FALSE"
- **attr:CUI**: UMLS Concept Unique Identifier
- **parent_concept_urls**: URL pointing to parent concept in hierarchy
- **attr:ATC_LEVEL**: Level in ATC hierarchy (1-5)
- **attr:Is_Drug_Class**: "Y" for classification levels, empty for actual drugs

## Version Information

- **Current Version**: 2025
- **Source Update Date**: January 16, 2025 (BioPortal)
- **Last OCL Update**: October 2025

## Update Process

When a new ATC version is released:

1. **Check for Updates**:
   - Monitor BioPortal: [https://bioportal.bioontology.org/ontologies/ATC](https://bioportal.bioontology.org/ontologies/ATC)
   - Check WHO ATC/DDD Index: [https://atcddd.fhi.no/atc_ddd_index/](https://atcddd.fhi.no/atc_ddd_index/)

2. **Download New Data**:
   - Download latest `ATC.csv` from BioPortal

3. **Run Transformation**:
   - Load `ATC.csv` into OpenRefine
   - Apply `OpenRefine Script - WHO ATC for OCL.json`
   - Export as CSV

4. **Generate Retirement List**:
   - Compare new concepts with existing OCL version
   - Create retirement CSV for removed concepts

5. **Validate**:
   - Check concept counts
   - Verify hierarchy integrity
   - Review sample concepts at each level

6. **Load to OCL**:
   - Load new/updated concepts
   - Process retirements
   - Verify in OCL interface

## Integration with CIEL

The WHOATC source is used by CIEL (Columbia International eHealth Laboratory) for:
- Drug classification mappings
- Identifying mappings that need replacement when ATC codes are retired
- Maintaining consistency across medical terminology systems

Retired concepts are kept with `retired: true` flag to:
- Support CIEL workflows for identifying deprecated mappings
- Maintain historical data integrity
- Enable migration paths for existing implementations

## Support and Maintenance

**Original Implementation**: [Joe Amlung](https://github.com/jamlung-ri)

For questions or issues:
- Check OCL documentation: [https://docs.openconceptlab.org/](https://docs.openconceptlab.org/)
- Review ATC methodology: [https://www.who.int/tools/atc-ddd-toolkit](https://www.who.int/tools/atc-ddd-toolkit)

## License

The ATC classification system is maintained by the WHO Collaborating Centre for Drug Statistics Methodology. Users should comply with WHO's terms of use for ATC data.

## References

1. WHO Collaborating Centre for Drug Statistics Methodology: [https://www.whocc.no/](https://www.whocc.no/)
2. ATC/DDD Toolkit: [https://www.who.int/tools/atc-ddd-toolkit](https://www.who.int/tools/atc-ddd-toolkit)
3. NCBO BioPortal: [https://bioportal.bioontology.org/](https://bioportal.bioontology.org/)
4. Open Concept Lab: [https://openconceptlab.org/](https://openconceptlab.org/)
