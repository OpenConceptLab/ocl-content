The PanelsAndForms directory contains the following files:

 - PanelsAndForms.csv
 - Loinc.csv
 - AnswerList.csv
 - LoincAnswerListLink.csv
 - PanelsAndFormsReadMe.txt
 
The comma separated files are designed as relational tables with each line in the file representing a row in the table. The first row of each table contains column headings. All other rows contain data. The details for each table and relationships within the tables are provided below.

-----------------------------------
PanelsAndForms.csv

The LOINC PanelsAndForms files provides all of the panels contained in the LOINC database with their full panel structure. The first row contains column headings. All other rows contain data. The details for the structure are provided below. 

Overview:
The file contains all the panels in LOINC, with one row representing each individual term within the panel along with information specific to the instance of that term within the panel, including the display name for the specific form, cardinality, skip logic and form coding instructions. Some LOINC panels contain child panels nested underneath. For the nested panels, the row for each term within that panel will have the value for the immediate parent in the "Parent" column. And for the nested panel terms themselves, the panel terms that contain them will be contained in their "Parent" column. For example, if Panel A contains Panel B and C, and Panel B contains Terms 1, 2 and 3 and Panel C contains Terms 4, 5 and 6, this would be represented as:

PARENT			CHILD
Panel A			Panel B
Panel B			Term 1
Panel B			Term 2
Panel B			Term 3
Panel A			Panel C
Panel C			Term 4
Panel C			Term 5
Panel C			Term 6

Columns (only the columns indicated by an asterisk (*) will be populated for every row. All of the other columns may or may not be valued depending on the panel being represented):
 - ParentId* - an internal unique identifier that identifies the parent LOINC panel term that contains the child term indicated by the Loinc field. The rows in which the ParentId and Id is the same represent the root for a given panel. Note that this ParentId should not be used as an identifier for the parent LOINC term because it is temporary (i.e., may change from release to release) and has no meaning external to the LOINC database.
 - ParentLoinc* - the unique LOINC identifier for the parent LOINC panel term that contains the child term indicated by the Loinc field
 - ParentName* - a LOINC name for the Parent LOINC. Terms in the Survey class will display the Short Name if one exists and otherwise the Formal Name, and all other terms will display the Short Name
 - ID* - an internal unique identifier that identifies the LOINC term indicated in the Loinc column. The rows in which the ParentId and Id is the same represent the root for a given panel. Note that this Id should not be used as an identifier for the LOINC term because it is temporary (i.e., may change from release to release) and has no meaning external to the LOINC database.
 - SEQUENCE* - the order of the LOINC term within the panel
 - Loinc* - the LOINC number, a unique numeric identifier with check digit for each term. The LOINC number in this column corresponds to the LOINC number in other related LOINC artifacts. Additional information about a LOINC term can be found in the LOINC Table File and LOINC Table Core artifacts (linked to the field called "LOINC_NUM"). Any answer lists associated with a particular LOINC term are represented in the LOINC Answer File.
 - LoincName* - a LOINC name for the child LOINC. Terms in the Survey class will display the Short Name if one exists and otherwise the Formal Name, and all other terms will display the Short Name
 - DisplayNameForForm - form-specific display text for the LOINC term in the context of this panel. See LOINC Users' Guide for more information on choosing the "display text" for a question or variable.
 - ObservationRequiredInPanel - denotes conditionality of each element of the panel. See Section 7.4 'Representing conditionality' of the LOINC Users' Guide for definitions of LOINC conditionality values.
 - ObservationIdInForm - form-specific observation ID for this panel element. The contents contain a string that uniquely identifies the question within the context of a particular form or survey instrument.
 - SkipLogicHelpText - describes the differentiated paths through the survey instrument based on the user's response to that data element
 - DefaultValue - denotes a default answer which could be used in electronically rendered forms
 - EntryType - the type of entry (Q = Question, expects user entry; C = Question, computer calculates response; H = Header (not a question))
 - DataTypeInForm - field designated for future use
 - DataTypeSource - field designated for future use
 - AnswerSequenceOverride - a value of "REVERSE" in this field indicates that the defined order of the answer list should be reversed for this item in this panel
 - ConditionForInclusion - a narrative statement of the condition under which result must be included in the panel
 - AllowableAlternative - the allowable alternatives to this LOINC that will satisfy the requirements of the panel
 - ObservationCategory - field designated for future use
 - Context - text on a form that provides the user with the context for filling out the form, or any other text in the form that falls outside of the coding instructions.
 - ConsistencyChecks - information that can be used to validate the accuracy of the response
 - RelevanceEquation - the equation that allows one to compute the relevance of a question
 - CodingInstructions - text on a form that provides the user with additional information about completing the form or entering coded data
 - QuestionCardinality - controls the cardinality of a question on a form. The lower range will be 0 for optional questions or 1 for mandatory questions. The upper range is a number > 0. This value indicates number of times that this question can be asked. "*" is used as a special flag to indicate that there is no upper bound.
 - AnswerCardinality - controls the number of acceptable answers for a given question. The lower range will be 0 for questions that may be left blank and 1 for mandatory questions. The upper range is a number > 0. This value indicates the number of answer values that may be resulted for that question. "*" is used as a special flag to indicate that there is no upper bound or the upper bound is unknown.
 - AnswerListIdOverride - when populated, this field provides the identifier for the LOINC answer list that is associated with the LOINC term within the instance of the panel LOINC term given in the ParentLoinc column. Note that this field is ONLY populated if the LOINC term is associated with an answer list and/or answer list link type other than the default values given in the LoincAnswerListLink.csv within the LOINC Answer file (the default row will not have an ApplicableContext value).
 - AnswerListTypeOverride - when populated, this field provides the type of linkage (such as "NORMATIVE") between the LOINC term and the override answer list that is associated with the LOINC term within the instance of the panel LOINC term given in the ParentLoinc column. Note that this field is only populated if the LOINC term is associated with an answer list and/or link type other than the default values given in the LoincAnswerListLink.csv within the LOINC Answer file (the default row will not have an ApplicableContext value). Also, the LOINC number in the ParentLoinc column may not be the same as the ApplicableContext value in the LoincAnswerListLink file for the analogous row because the ParentLoinc value is the LOINC number for the immediate parent panel, while the ApplicableContext value is the LOINC number for the top-most panel that has a PanelType=Panel. If null, the association between the LoincNumber, AnswerListId, and AnswerListLinkType represents the default list and link type for the LOINC term.
 - EXTERNAL_COPYRIGHT_NOTICE - external copyright holder's notice for this LOINC term, if applicable
 - AdditionalCopyright - additional external copyright holder's notice for this LOINC term, if applicable. This field is within the context of the panel.

Sort order:
The data in this file are sorted by the ParentId followed by the Id values.

-----------------------------------
AnswerList.csv

The structure of this file is documented in the ReadMe file of the "AnswerFile" archive.

-----------------------------------
LoincAnswerListLink.csv

The structure of this file is documented in the ReadMe file of the "AnswerFile" archive.

-----------------------------------
Loinc.csv

The structure of this file is documented in Appendix A of the LOINC Users' Guide.
