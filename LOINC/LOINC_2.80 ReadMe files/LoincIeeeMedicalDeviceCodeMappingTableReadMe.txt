The LoincIeeeMedicalDeviceCodeMappingTable directory contains the following files:

Directory listing:
 - LoincIeeeMedicalDeviceCodeMappingTable.csv
 - LoincIeeeMedicalDeviceCodeMappingTableReadMe.txt

The first row in the comma separated file contains column headings. All other rows contain data. Details about the file contents are provided below.

Overview:
The LOINC/IEEE Medical Device Code Mapping Table is distributed by Regenstrief as a product of a collaboration between the IEEE-SA and Regenstrief Institute, Inc. The file contains linkages between LOINC terms and content from the IEEE 11073(TM) 10101 family of Standards for Health informatics - Point-of-care medical device communication.
 
Columns:
 - LOINC_NUM - the source LOINC term identifier, which is a unique numeric identifier with a check digit
 - LOINC_LONG_COMMON_NAME - the LOINC Long Common Name for the term
 - IEEE_CF_CODE10 - the target IEEE 11073-10101/10101a/10101R numeric identifier for the concept
 - IEEE_REFID - the unique IEEE 11073-10101/10101a/10101R text identifier for the concept
 - EQUIVALENCE - whether the target concept is equivalent, broader, or narrower than the source concept

Sort order:
This file is sorted alphabetically by LOINC number.

*Note: This file does not include any deprecated LOINC terms.