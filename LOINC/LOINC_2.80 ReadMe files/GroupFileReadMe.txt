***This is a Beta release***

The GroupFile directory contains the following files:

 - ParentGroup.csv
 - ParentGroupAttributes.csv
 - Group.csv
 - GroupAttributes.csv
 - GroupLoincTerms.csv
 - GroupFileReadMe.txt

IMPORTANT NOTES:
1. The LOINC Group project is a work in progress. The contents of this file may change from release to release as we receive feedback from users and refine our processes.
2. The contents of the file and the groupings MUST be validated by the user prior to implementation in any aspect of clinical care. We have created Groups that may be useful in specific contexts, but these Groups have not been vetted for use in either patient care or research and should be used with caution.


The first row in the comma separated files contains column headings and all other rows contain data. Details about the file contents are provided below.

Overview:
The goal of the LOINC groups project is to create a flexible, extensible, and computable mechanism for rolling up groups of LOINC codes for various purposes. Representative use cases include aggregating data for displaying on a flowsheet within an electronic health record (EHR) system, retrieving data for quality measure reporting, and processing data for research.

LOINC Groups are value sets of LOINC codes designed for specific purposes. We intend for the LG codes to serve as a coded value set identifier. (For more information, see https://www.hl7.org/fhir/valueset.html). As, such they correspond to a particular "definition" of what should be included in the group. Following best practices, we intend to keep that logical definition stable in meaning over time. However, the members of the group may change as the underlying terminology (LOINC) evolves. For example, new concepts may be added that fulfill a group's definition and are thus included.

-----------------------------------
ParentGroup.csv

Columns:
 - ParentGroupId - the unique identifier for the ParentGroup that has a prefix of "LG".
 - ParentGroup - a systematic name for the high-level group from which all the individual groups are created.
 - Status - the current state of this ParentGroup, e.g., whether or not the group is active, inactive, or deprecated. An Inactive ParentGroup is one that contains no child Groups. A Deprecated ParentGroup is one that has been identified as erroneous or duplicative and should no longer be used.

Sort order:
This file is sorted by the ParentGroup name.

-----------------------------------
ParentGroupAttributes.csv

Columns:
 - ParentGroupId - the unique identifier for the ParentGroup that has a prefix of "LG".
 - Type - the category of attribute, such as "Description".
 - Value - the text of the attribute.

Sort order:
This file is sorted by the ParentGroupId, then by the Type and Value.

-----------------------------------
Group.csv

Columns:
 - ParentGroupId - Identifies the ParentGroup for this record. This value can be used as a foreign key into the ParentGroup file.
 - GroupId - the unique identifier for a single Group that also has prefix "LG".
 - Group - the systematic name for a single Group containing a set of LOINC codes that could potentially be rolled up in certain contexts.
 - Archetype - the LOINC number of the most general representative term for a specific Group. For example, in a Group rolled up by method, the methodless term is the archetype term. Note that the Archetype field is only valued for a subset of Groups.
 - Status - the current state of this Group, e.g., whether or not the Group is active, inactive, or deprecated. Groups are given a status of Inactive when they contain zero or one LOINC term (and are therefore not very helpful Groups). Currently Inactive Groups may have previously contained more child LOINC terms and been Active, but due to content edits they now only contain zero or one. With subsequent content edits, it is possible that an Inactive Group may later change back to a status of Active. A Deprecated Group is one that has been identified as erroneous or duplicative and should no longer be used, or one that only contains Deprecated LOINC terms.
 - VersionFirstReleased - the LOINC version number in which the record was first released. This field will be populated once the Groups are in production status.

Sort order:
This file is sorted by the ParentGroupId followed by the Group.

-----------------------------------
GroupAttributes.csv

Columns:
 - ParentGroupId - Identifies the ParentGroup for this record. This value can be used as a foreign key into the ParentGroup file.
 - GroupId - the unique identifier for a single Group that also has prefix "LG". 
 - Type - the category of attribute, such as "Description" or "UsageNotes".
 - Value - the text of the attribute.

Sort order:
This file is sorted by the ParentGroupId followed by the GroupId.

-----------------------------------
GroupLoincTerms.csv

Columns:
 - Category - a short description that identifies the general purpose of the group, such as "Flowsheet", "Reportable microbiology" or "Document ontology grouped by role and subject matter domain"
 - GroupId - the unique identifier for a single Group that also has prefix "LG". 
 - Archetype - the LOINC number of the most general representative term for a specific Group. For example, in a Group rolled up by method, the methodless term is the archetype term.
 - LoincNumber - the unique identifier for a given LOINC term 
 - LongCommonName - the Long Common Name for the LOINC term  

Sort order:
This file is sorted by the Category followed by the GroupId.

-----------------------------------
ParentGroup and Group Names:

For ParentGroups that are based on Part-level inclusion/exclusion criteria, each ParentGroup is named as a concatenation of the:
1) high-level group concept;
2) in angle brackets, axes that have the same value for each term in a given group;
3) (if applicable) in angle brackets, a specific value within an axis or values that are purposely grouped together; and
4) (if applicable) in angle brackets, axes that are purposely ignored and therefore automatically grouped together (rolled up).

For example, the ParentGroup "VitalsRoutine<SAME:Comp|Prop><Tm:Pt|Chal:None><ROLLUP:Sys|Meth>" contains:
1) terms that represent routine vital signs;
2) where all of the LOINC terms in each individual group have the same Component and Property;
3) where the Time aspect has a value of "Pt" and none of the terms include a Challenge; and
4) terms are grouped together in a single Group regardless of the System and whether they are methodless or have a specific Method.

ParentGroups that represent broader clinical concepts and are not strictly based on Part-level inclusion/exclusion criteria have a high-level name that does not include the angle bracket notation, for example, SocialDeterminantsOfHealth and ExerciseOrActivityTerms.

Each Group that is based on Part-specific inclusion/exclusion criteria is named as a concatenation of the following pieces delimited by vertical bars (|):
1) values in the axes that contain the same value for all LOINC terms in a Group, which corresponds to the first set of angle brackets in the ParentGroup; and
2) label assigned to the set of values in a given axis that are purposely grouped together, which corresponds to the second set of angle brackets in the ParentGroup.

Note that the axes that are automatically rolled together, corresponding to the third set of angle brackets in the ParentGroup, are not represented in the individual Group names. In addition, if specific values are purposely excluded in any of the axes as defined in the ParentGroup attributes, those exclusions are not included in the Group name.

For example, the "Intravascular systolic|Pres|Pt|Chal:None" Group, which is part of the VitalsRoutine ParentGroup described above, contains terms that have:
1) Component "Intravascular systolic", Property "Pres", Timing "Pt"; 
2) No Challenge;
3) Any System; and
4) Any Method

Terms in the 'Intravascular systolic|Pres|Pt|Chal:None' Group:
8508-4	Brachial artery Systolic blood pressure
76215-3	Invasive Systolic blood pressure
8480-6	Systolic blood pressure
75997-7	Systolic blood pressure by Continuous non-invasive monitoring
76534-7	Systolic blood pressure by Noninvasive
8479-8	Systolic blood pressure by palpation

Similar to ParentGroups, Groups that represent broader clinical concepts have a high-level name without the vertical bar notation, such as Exercise/Activity and Smoking-related Terms.