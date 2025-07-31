The LoincTableCore directory contains the following files:

 - LoincTableCore.csv
 - MapTo.csv
 - LoincTableCoreReadMe.txt

The first row in the comma separated file contains column headings and all other rows contain data. Details about the file contents are provided below.

Overview:
The purpose of the core LOINC table is to provide the essential LOINC content in a format that is stable over the long-run. The core table contains all of the LOINC terms that are in the complete table (i.e., the same number of rows), but a subset of the fields (i.e., different number of columns). The fields included in the core table are ones that are both crucial for defining each LOINC term and whose structure is not likely to change in the short-term. We are providing this format in order to make it easier for implementers to update to the latest LOINC release without having to make changes to their database structure. However, depending on their use case, some implementers may still need to refer to the complete LOINC table in order to find all of the relevant information.
 
The LoincTableCore contains the following columns (for descriptions of each column, see Appendix A in the LOINC Users' Guide):
 - LOINC_NUM
 - COMPONENT
 - PROPERTY
 - TIME_ASPCT
 - SYSTEM
 - SCALE_TYP
 - METHOD_TYP
 - CLASS
 - CLASSTYPE
 - LONG_COMMON_NAME
 - SHORTNAME
 - EXTERNAL_COPYRIGHT_NOTICE
 - STATUS
 - VersionFirstReleased
 - VersionLastChanged

The MapTo.csv file is included so that users can update their mappings for deprecated terms without having to download a separate artifact.