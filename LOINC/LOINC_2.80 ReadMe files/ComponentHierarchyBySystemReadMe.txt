The ComponentHierarchyBySystem directory contains the following files:

 - ComponentHierarchyBySystem.csv
 - ComponentHierarchyBySystemReadMe.txt

The first row in the comma separated file contains column headings. All other rows contain data. Details about the file contents are provided below.

Overview:
The LOINC ComponentHierarchyBySystem (Formerly known as Multiaxial Hierarchy) file provides a way to organize LOINC codes based on multiple axes of each concept. LOINC Parts comprise all of the branches in the ComponentHierarchyBySystem, and LOINC terms comprise all of the leaf nodes. The ComponentHierarchyBySystem is generated using an automated process based on the Component hierarchy, which is maintained by hand and is primarily organized by Class, and the System. These hierarchies are not meant to be pure ontologies, and rather are tools for organizing sets of codes within different domains.

All LOINC hierarchies, including the ComponentHierarchyBySystem hierarchy, can be browsed and searched using the online Hierarchy Browser - https://loinc.org/tree/
 
The ComponentHierarchyBySystem was originally created for the Laboratory domain, but over time, a few other clinical domains (e.g. radiology, document ontology) were added. The release with LOINC Version 2.61 was a major update that incorporated all LOINC terms (across all domains), and going forward we plan to continue including all LOINC terms in the hierarchy.

The ComponentHierarchyBySystem contains four top-level branches to match the four broad types of LOINC codes: Laboratory, Clinical, Attachments, and Survey. All of the domains other than Radiology (which is contained within the Clinical branch) are organized by Class, then Component, and finally the System. Radiology terms are organized by System followed by the Method (modality). 
 
Each top-level branch (except for Attachments) contains a "NotYetCategorized" node, which includes all terms in a given class that could not be placed elsewhere in the hierarchy based on an issue with Component placement in the Component tree. Note that none of the Survey Components are included in the Component hierarchy, so all of the Survey terms are in the "SurveyNotYetCategorized" node. Over time, we intend to more fully develop the hierarchies in these areas and hope to reduce the number of LOINC terms in "NotYetCategorized" branches.

Parts that are no longer active nodes in the hierarchy are not included in this file. Previously published but now obsolete Parts are deprecated, and are included in the ChangeSnapshot artifact that indicates their change of status.
 
Columns:
 - PATH_TO_ROOT - the series of Part numbers delimited by dots (.) that represent the path from the root of the hierarchy to an individual LOINC Part or term
 - SEQUENCE - the order in which the LOINC Part or term in this row (specified in the CODE column) appears under its immediate parent (i.e., the Part in the IMMEDIATE_PARENT column)
 - IMMEDIATE_PARENT - the parent LOINC Part that immediately precedes a given code in the hierarchy. Note that the value contained in this field is always a LOINC Part number and can never be a LOINC term number
 - CODE - the LOINC Part or LOINC term whose hierarchy path is being described in a given row
 - CODE_TEXT - the name of the LOINC Part or the Short Name of the LOINC term depending on the concept in the CODE column
	
Sort order:
This file is sorted by ClassType, followed by the order of the manually constructed hierarchies on which the ComponentHierarchyBySystem is based: Class, Component, System, and Method. 