***This is an Alpha release***

The ConsumerName directory contains the following files:

 - ConsumerName.csv
 - ConsumerNameReadMe.txt

The first row in the comma separated file contains column headings. All other rows contain data as described below. 

-----------------------------------
ConsumerName.csv

Overview: 
This file contains LOINC term Consumer Names. Its present scope covers all Laboratory LOINC terms and a subset of Clinical terms. The Consumer Names are created algorithmically, based on manually crafted labels (names) for each Part. These names do not represent each of the defining Parts of a given term, are not unique, and do not include an indicator that a term is deprecated.

The primary rules used to create the Part labels and generate the Consumer Names include:

1. Component: The text may represent a more general concept and uses a more common label if one exists; abbreviations are generally not used, except in select cases such as HIV. However, for cross-reference and to facilitate consumer-provider communication, we do include some common abbreviations in parentheses behind the expanded form of the term.
2. System: The specimen is placed at the end of the name and is prefixed by a comma; almost all intravascular specimens are labeled Blood, with a few exceptions such as Dried Blood Spot.
3. Property, Scale, and Method: These attributes are mostly excluded. As a result, many Consumer Names for different LOINC terms are identical. This approach assumes that the result value and/or the units of measure will provide additional context for the name.
4. Method: When Method is included, it is at the end of the name prefixed by a comma or prefixed with "by".

Columns:

 - LoincNumber - The LOINC term identifier, which is a unique numeric identifier with a check digit
 - ConsumerName - The ConsumerName generated for this LOINC term
	
Sort order:
This file is sorted alphabetically by ConsumerName



