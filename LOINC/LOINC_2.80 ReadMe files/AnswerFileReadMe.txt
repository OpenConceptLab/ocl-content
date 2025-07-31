The AnswerFile directory contains the following files:

 - AnswerList.csv
 - LoincAnswerListLink.csv
 - AnswerFileReadMe.txt

The comma separated files are designed as relational tables with each line in the file representing a row in the table. The first row of each table contains column headings. All other rows contain data. The details for each table and relationships within the tables are provided below.

-----------------------------------
AnswerList.csv

Overview: 
This file contains all of the Answer Lists that are associated with any of the LOINC terms included in the current LOINC release. There are two types of Answer Lists included in this file: 
1. Answer Lists that contain an enumerated list of LOINC answer strings; and 
2. Externally defined Answer Lists, which are not enumerated in LOINC but rather include pointers (e.g., OID, URL) to the external site where that answer list is maintained. 

Note that Answer Lists that were previously released but that are no longer linked to any published LOINC term are not included in this file. However, lists associated with Deprecated LOINC terms ARE included in this file, because those terms continue to be released.

The columns in the Answer List files are given below. Only the columns indicated by an asterisk (*) will be populated for every row. All of the other columns may or may not be valued depending on whether the answer list is externally defined, it was submitted with local answer codes, and/or specific answer strings are mapped to an external code.

Columns:
 - AnswerListId* - a unique identifier for each LOINC answer list that begins with the prefix "LL". This field is also contained in the LoincAnswerListLink file described below and defines the relationship between the two tables contained in the LOINC Answer file.
 - AnswerListName* - the name given to an Answer List
 - AnswerListOID* - the OID associated with the Answer List
 - ExtDefinedYN* - the field defining whether or not a list is externally defined
 - ExtDefinedAnswerListCodeSystem - the code system that is the source for answers in externally defined lists
 - ExtDefinedAnswerListLink - the link to an externally defined Answer List, such as a URL or URI
 - AnswerStringId - the LOINC Answer String Id, which uniquely identifies an answer string and starts with the prefix "LA"
 - LocalAnswerCode - the code or label used to represent the answer on the submitter's form
 - LocalAnswerCodeSystem - the code system from which the answer on the submitter's form is drawn
 - SequenceNumber - the sequence in which the answer strings appear in the Answer List
 - DisplayText - the answer string
 - ExtCodeId - the unique identifier in an external coding system that the answer string concept is mapped to
 - ExtCodeDisplayName - the display name from the external coding system for the external code 
 - ExtCodeSystem - the coding system to which the external code belongs
 - ExtCodeSystemVersion - the version of the coding system to which the external code belongs
 - ExtCodeSystemCopyrightNotice - provides copyright information for external codes, if applicable
 - SubsequentTextPrompt - the text associated with answers such as "Other" that indicates what extra information the user should enter, for example, "Please specify:"
 - Description - description, if one exists, associated with the answer string
 - Score - the numeric score associated with a specific answer, if applicable, that can be used in various applications such as automatically computing the total score for a validated survey instrument
	
Sort order:
This file is sorted by alphabetically by the AnswerListId

-----------------------------------
LoincAnswerListLink.csv

Overview:
This file contains every LOINC term in the current LOINC release that is associated with an Answer List, as well as the name and unique identifier of the Answer list, the link type, and, if applicable, the panel context in which a list or link type other than the default is associated with a given LOINC term.

Columns:
 - LoincNumber - the LOINC term identifier, which is a unique numeric identifier with a check digit
 - LongCommonName - the LOINC Long Common Name
 - AnswerListId - a unique identifier for each LOINC answer list that begins with the prefix "LL". This field is also contained in the AnswerList file described above and defines the relationship between the two tables contained in the LOINC Answer file.
 - AnswerListName - the name of the Answer List
 - AnswerListLinkType - the type of linkage between the LOINC term and the Answer List, such as "PREFERRED" and "EXAMPLE"
 - ApplicableContext - if populated, this field provides the LOINC number for the parent panel (that contains the child term indicated by the LoincNumber field) providing further context for the association to the Answer List and its link type. The parent panel listed is the topmost parent panel that has a PanelType=Panel (see Appendix A in the LOINC Users' Guide for a description of the PanelType field). Note that the LOINC number in this column may be different from the ParentLoinc value in the PanelsAndForms file for the analogous row because the ParentLoinc in the PanelsAndForms file is the immediate parent LOINC, not the topmost. If null, the association between the LoincNumber, AnswerListId, and AnswerListLinkType represents the default list and link type for the LOINC term.

Sort order:
This file is sorted by alphabetically by the LoincNumber followed by the AnswerListId