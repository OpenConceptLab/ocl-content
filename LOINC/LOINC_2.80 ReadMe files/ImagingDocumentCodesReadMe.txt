The ImagingDocuments directory contains the following files:

 - ImagingDocumentCodes.csv
 - ImagingDocumentCodesReadMe.txt

The first row in the comma separated file contains column headings. All other rows contain data. Details about the file contents are provided below.

Overview:
The LOINC Imaging Document codes file contains a subset of document codes in LOINC that represent imaging procedures and reports. Such documents contain a consulting specialist's interpretation of image data and are used in Radiology, Endoscopy, Cardiology, and other imaging specialties. At the present time, the majority of the codes for imaging documents in LOINC are radiology studies (found in the Class: RAD), but some imaging document codes are also included in other classes. The value set of imaging document codes is defined based on imaging Methods with the Scale Doc using the following SQL statement:

SELECT 
  LOINC_NUM,
  LONG_COMMON_NAME FROM loinc.LOINC 
WHERE 
  SCALE_TYP = 'Doc' AND 
  Status not like 'DEPRECATED' AND
  (METHOD_TYP like 'XR%'
    OR METHOD_TYP like 'US'
    OR METHOD_TYP like 'US.%'
    OR METHOD_TYP like 'US &&%'
    OR METHOD_TYP like 'MR%'
    OR METHOD_TYP like 'NM%'
    OR METHOD_TYP like 'DXA%'
    OR METHOD_TYP like 'CT%'
    OR METHOD_TYP like 'RF%'
    OR METHOD_TYP like '{Imaging%'
    OR METHOD_TYP like 'MG%'
    OR METHOD_TYP like 'PT%'
    OR METHOD_TYP like '%scopy%')

Columns:
	- LOINC_NUM - the LOINC term identifier, which is a unique numeric identifier with a check digit
	- LOINC_LONG_COMMON_NAME - the LOINC Long Common Name for the term

Sort order:
This file is sorted alphabetically by LOINC number.

Note:
This file does not contain any deprecated LOINC terms.