The ChangeSnapshot directory contains the files listed below:

 - LoincChangeSnapshot.csv
 - PartChangeSnapshot.csv
 - ChangeSnapshotReadMe.txt

The first row in the comma separated files contain column headings. All other rows contain data as described below. 

-----------------------------------
LoincChangeSnapshot.csv

Overview: 
This file contains key changes to LOINC terms since the last release.

Columns:
 - VersionEffective - the release version in which the change is effective
 - LOINC_NUM - the LOINC term identifier, which is a unique numeric identifier with a check digit
 - Property - the attribute containing the value that changed; not to be confused with the LOINC Property
 - ValuePrior - the previous value for the property
 - ValueCurrent - the value for the property in the LOINC version indicated in the VersionEffective field
 - ChangeReason - the reason for the change

Sort order:
This file is sorted by the LOINC_NUM

-----------------------------------
PartChangeSnapshot.csv

Overview: 
This file contains key changes to LOINC Parts since the last release. This file may include Parts that are published in the Part file (those directly linked to LOINC terms) as well as multi-axial Parts that are only published in the Component Hierarchy By System file (those used to organize LOINC terms).

Columns:
 - VersionEffective - the release version in which the change is effective
 - PartNumber - the Part identifier, which is a unique identifier that starts with the prefix "LP"
 - Property - the attribute containing the value that changed; not to be confused with the LOINC Property
 - ValuePrior - the previous value for the property
 - ValueCurrent - the value for the property in the LOINC version indicated in the VersionEffective field
 - ChangeReason - the reason for the change

Parts with a Status of DEPRECATED may either be Parts that are: 1) not used for defining any published LOINC term or organizing part of the Component Hierarchy By System, and are not expected to be used in the future; or 2) those that are only used to define a deprecated LOINC term. Parts with a Status of INACTIVE are Parts that are no longer used, but that may be used again in the future.

Sort order:
This file is sorted by the PartNumber