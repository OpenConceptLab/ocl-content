The LoincRsnaRadiologyPlaybook directory contains the following files:

 - LoincRsnaRadiologyPlaybook.csv
 - LoincRsnaRadiologyPlaybookReadMe.txt

The first row in the comma separated file contains column headings and all other rows contain data. Details about the file contents are provided below.

Overview:
The LOINC/RSNA Radiology Playbook is the product of a collaboration between the Radiological Society of North America (RSNA) and Regenstrief Institute, Inc. to develop a unified model for naming radiology procedures. The CSV file contains linkages between LOINC radiology terms, the unified Playbook attribute values expressed as both LOINC Radiology Parts and RadLex features, and any applicable mappings from LOINC terms to RadLex Core Playbook terms. The LOINC Radiology Parts are based on the Unified Playbook model and classified according to their type (Modality type, Region imaged, Imaging focus, etc). For more details regarding the LOINC/RSNA collaboration of the Unified Playbook model, see the LOINC Users' Guide Annex.

Some LOINC terms contain combinations of LOINC Part values within the LOINC Component, System or Method fields, and the PartSequenceOrder value indicates the proper order of each one within that field. The PartSequenceOrder is also used to represent parallelism in studies where multiple views are obtained or more than one Modality is performed, and to show which attributes are associated with each other.

Columns:
 - LoincNumber - the LOINC term identifier, which is a unique numeric identifier with a check digit
 - LongCommonName - the LOINC Long Common Name
 - PartNumber - the LOINC Radiology Part number, which is a unique identifier that starts with the prefix "LP"
 - PartTypeName - the type of LOINC Radiology Part. Examples: Rad.Timing, Rad.Modality.Modality Subtype
 - PartName - the name of the LOINC Radiology Part. Examples: Neck, Views, XR
 - PartSequenceOrder - indicates the proper sequence of Part values within an attribute and/or the relationship(s) between values across multiple attributes (for details regarding the PartSequenceOrder value, see below)
 - RID - the RadLex identifier for an attribute value in the RadLex ontology
 - PreferredName - the preferred name for the attribute value in the RadLex ontology
 - RPID - the RadLex Playbook identifier, a unique alphanumeric code for each RadLex Playbook procedure 
 - LongName - the RadLex Playbook Long Name for the procedure

Sort order:
This file is sorted by LoincNumber followed by PartSequenceOrder.

Note:
This file does not contain any deprecated LOINC terms.

-----------------------------------

PartSequenceOrder details:
The PartSequenceOrder value is used to represent two different features: 1) the sequence of Part values within an attribute for attributes that contain more than one value; and 2) the relationship(s) between values across multiple attributes in cases where one or more specific values in one attribute are associated with one or more specific values in another attribute. 

The values in this field consist of upper case letters (e.g., "A", "B") delimited by dots (.). 

Letter value:
The letters themselves represent the sequence of that value within an attribute. For example, "A" is first, "B" is second, etc.

Position number:
The number of positions valued in the PartSequenceOrder for a given LOINC Radiology Part (e.g., A.A has two positions valued and A.A.A has three) depends on the number of values for a given attribute as follows:
1) Terms with a single value in every attribute will have a single letter value in the sequence;
2) Terms with more than one value in the Anatomic Location, View (Aggregation or View type), Reason for Exam, or Guidance attribute will have two positions valued; and
3) Terms with more than one value in the Maneuver or Pharmaceutical attributes will have one more position valued relative to the View they are associated with.

The Modality (Method) values determine the letter value of the first position. In almost all cases, a single LOINC term has a single Modality value, so the first position gets a sequence of "A". However, in a limited number of cases, a single procedure code actually represents two independent procedures with the SAME Modality, such as AP Chest and Upright Abdomen X-ray, and for these, the Modality, which is common to both procedures, is given a combined sequence value of "AB", all of the attribute values related to the first (AP Chest) procedure are indicated by an "A" in the first position, and those related to the second (Upright Abdomen) procedure are indicated by a "B".

Similarly, if a single LOINC term represents two independent procedures with DIFFERENT Modalities, such as Chest X-ray and Fluoroscopy, the attribute values related to the X-ray will be given a value of "A", those related to Fluoroscopy will be given a value of "B", and because both studies apply to a single anatomic location, the anatomic location will be given a combined sequence value, e.g. "AB", in the first position. 

Examples:
1) Terms with a single value in every attribute

36572-6 View AP:Find:Pt:Chest:Doc:XR
LP199962-4	Rad.Anatomic Location.Region Imaged	Chest	A
LP222059-0	Rad.View.Aggregation			View	A
LP220552-6	Rad.View.View type			AP	A
LP212285-3	Rad.Modality.Modality type		XR	A

39034-4	Multisection^WO & W contrast IV:Find:Pt:Upper extremity:Doc:MR
LP199954-1	Rad.Anatomic Location.Laterality.Presence	TRUE		A
LP199955-8	Rad.Anatomic Location.Laterality		Unspecified	A
LP206549-0	Rad.Modality.Modality type			MR		A
LP200090-1	Rad.Timing					WO & W		A
LP200085-1	Rad.Pharmaceutical.Substance Given		Contrast	A
LP200078-6	Rad.Pharmaceutical.Route			IV		A
LP200031-5	Rad.Anatomic Location.Region Imaged		Upper extremity	A

2) Terms with more than one value in the Anatomic Location, View (Aggregation or View type), Reason for Exam, or Guidance attribute

39383-5 Views 3 + Sunrise:Find:Pt:Lower extremity.right>Knee:Doc:XR
LP199953-3	Rad.Anatomic Location.Laterality		Right		A
LP199954-1	Rad.Anatomic Location.Laterality.Presence	TRUE		A
LP199985-5	Rad.Anatomic Location.Region Imaged		Lower extremity	A
LP199984-8	Rad.Anatomic Location.Imaging Focus		Knee		A
LP212285-3	Rad.Modality.Modality type			XR		A
LP220532-8	Rad.View.Aggregation				Views 3		A.A
LP220602-9	Rad.View.View type				Sunrise		A.B

3) Terms with more than one value in the Maneuver or Pharmaceutical attribute

39720-8 Views perfusion^at rest+W dipyridamole IV+W Tc-99m Sestamibi IV:Find:Pt:Chest>Heart:Doc:NM
LP248197-8	Rad.View.Aggregation			Perfusion		A
LP208891-4	Rad.Modality.Modality type		NM			A
LP199962-4	Rad.Anatomic Location.Region Imaged	Chest			A
LP199927-7	Rad.Anatomic Location.Imaging Focus	Heart			A
LP221404-9	Rad.View.Aggregation			Views			A
LP207666-1	Rad.Maneuver.Maneuver type		At rest			A.A
LP200088-5	Rad.Timing				W			A.B
LP208668-6	Rad.Pharmaceutical.Substance Given	Dipyridamole		A.B
LP200078-6	Rad.Pharmaceutical.Route		IV			A.B
LP208666-0	Rad.Pharmaceutical.Substance Given	Tc-99m Sestamibi	A.C
LP200088-5	Rad.Timing				W			A.C
LP200078-6	Rad.Pharmaceutical.Route		IV			A.C

83021-6 (Views 2 or 3) + (Views^W flexion + W extension):Find:Pt:Neck>Spine.cervical:Doc:XR
LP212285-3	Rad.Modality.Modality type		XR		A
LP199995-4	Rad.Anatomic Location.Region Imaged	Neck		A
LP200017-4	Rad.Anatomic Location.Imaging Focus	Spine.cervical	A
LP221404-9	Rad.View.Aggregation			Views		A
LP220531-0	Rad.View.Aggregation			Views 2 or 3	A.A
LP206622-5	Rad.Maneuver.Maneuver type		Flexion		A.B.A
LP200088-5	Rad.Timing				W		A.B.A
LP200088-5	Rad.Timing				W		A.B.B
LP206621-7	Rad.Maneuver.Maneuver type		Extension	A.B.B

4) Terms with more than one Modality
36751-6 Views PA + lateral && Views:Find:Pt:Chest:Doc:XR && RF
LP212285-3	Rad.Modality.Modality Type		XR	A
LP220588-0	Rad.View.View Type			PA	A.A
LP220572-4	Rad.View.View Type			lateral	A.B
LP199962-4	Rad.Anatomic Location.Region Imaged	Chest	AB
	<Note: Chest has a sequence value of AB because the Region imaged attribute value is common across the two studies>
LP220472-7	Rad.Modality.Modality Type		RF	B
LP221404-9	Rad.View.Aggregation			Views	B
LP221404-9	Rad.View.Aggregation			Views	B