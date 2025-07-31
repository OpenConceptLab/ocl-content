The Updates directory contains the following files:

 - Updates.csv
 - UpdatesAdditionalFields.csv
 - UpdatesReadMe.txt

The first row in the csv files contains column headings. All other rows contain data.

Overview:
LOINC follows good terminology management practices, so the changes to LOINC names reflect modifications to our naming convention rules, style, and efforts for consistency rather that changes to the concept meaning. 

The Updates.csv contains records for LOINC terms in which one of the six major axes or Class value changed since the last release. The UpdatesAdditionalFields.csv contains LOINC terms in which any of the six major axes, Class, or select other fields associated with the term, such as the Long Common Name, Short Name, OrderObs, or DefinitionDescription (see full list below) contain values that changed. The UpdatesAdditionalFields.csv also includes the other associated files listed above and described in more detail below.


KNOWN ISSUE: Terms with an update in the RELATEDNAMES2 field are included in the UpdatesAdditionalFields.csv (and have been in the past), but are not considered when calculating the VersionLastChanged and CHNG_TYPE values.

-----------------------------------
Updates.csv

Overview:
The Updates.csv version of the Updates file contains all LOINC terms in which one of the six major axis values or Class has changed since the previous release. It also contains records for new terms added since the previous release.

Columns (for descriptions of each column other than the RecType column, see Appendix A in the LOINC Users' Guide):
 - RecType - the type of record in a given row. Terms that have been updated will have two rows, one with a value of "BEFORE" and one with a value of "CHANGED" in the RecType column that indicate whether the information in that row represents the term in the previous release ("BEFORE") or the current release ("CHANGED"). Terms that have been added have a value of "ADD". 
 - LOINC_NUM
 - COMPONENT
 - PROPERTY
 - TIME_ASPCT
 - SYSTEM
 - SCALE_TYP
 - METHOD_TYP
 - CLASS

Each LOINC term that was updated will have two rows in the Updates csv file. Each new LOINC term will have a single row.

Note: 
Deprecated terms are not included in this file.

-----------------------------------
UpdatesAdditionalFields.csv

Overview:
This file contains the RecType column plus all of the columns found in the complete LOINC table. However, only LOINC terms that have updates in one of the columns indicated by an asterisk (*) below are considered updated and included in this table. For a description of each column other than RecType see the LOINC Users' Guide Appendix A.

Columns:
 - RecType - the type of record in a given row. Terms that have been updated will have two rows, one with a value of "BEFORE" and one with a value of "CHANGED" in the RecType column that indicate whether the information in that row represents the term in the previous release ("BEFORE") or the current release ("CHANGED"). Terms that have been added have a value of "ADD". 
 - LOINC_NUM
 - COMPONENT*
 - PROPERTY*
 - TIME_ASPCT*
 - SYSTEM*
 - SCALE_TYP*
 - METHOD_TYP*
 - CLASS*
 - VersionLastChanged
 - CHNG_TYPE
 - DefinitionDescription*
 - STATUS*
 - CONSUMER_NAME*
 - CLASSTYPE*
 - FORMULA*
 - SPECIES*
 - EXMPL_ANSWERS*
 - SURVEY_QUEST_TEXT*
 - SURVEY_QUEST_SRC*
 - UNITSREQUIRED*
 - RELATEDNAMES2 (see KNOWN ISSUE above)
 - SHORTNAME*
 - ORDER_OBS* 
 - HL7_FIELD_SUBFIELD_ID*
 - EXTERNAL_COPYRIGHT_NOTICE*
 - EXAMPLE_UNITS*
 - LONG_COMMON_NAME*
 - UnitsAndRange*
 - EXAMPLE_UCUM_UNITS*
 - STATUS_REASON*
 - STATUS_TEXT
 - CHANGE_REASON_PUBLIC
 - COMMON_TEST_RANK*
 - COMMON_ORDER_RANK*
 - HL7_ATTACHMENT_STRUCTURE*
 - EXTERNAL_COPYRIGHT_LINK*
 - PanelType*
 - AskAtOrderEntry*
 - AssociatedObservations*
 - VersionFirstReleased
 - ValidHL7AttachmentRequest*
 - DisplayName*
