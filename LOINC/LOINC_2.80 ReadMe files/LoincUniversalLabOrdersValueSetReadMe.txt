The LoincUniversalLabOrdersValueSet directory contains the following files:

 - LoincUniversalLabOrdersValueSet.csv
 - LoincUniversalLabOrdersValueSetReadMe.txt

The first row in the comma separated file contains column headings. All other rows contain data. Details about the file contents are provided below.

Overview:
The LOINC Universal Lab Order Codes Value Set, also known as the "Common Lab Orders", is a collection of the most frequent lab orders. It was created for order entry system developers so that they could deliver them in HL7 messages to laboratories. On receipt, laboratories could understand and translate these universal codes into their internal processes for fulfillment.

This value set was developed iteratively through both empirical and consensus-driven approaches. The original version was developed by the NLM, Regenstrief Institute, and several organizations and contained an empirical list of the most commonly ordered tests. We often called that list the "Top 300", because it contained about 300 codes that accounted for the majority of the volume of five nationally representative data sources.

In 2014, S&I Framework Initiative called "aLOINC Order Code" launched with the goal of enhancing and expanding the original list to more comprehensively cover tests commonly ordered in ambulatory care settings and for tests ordered in public health settings. The initiative used a combination of empiric and consensus-based approaches to identify additional LOINC codes to be added to the original list.

Columns:
 - LOINC_NUM - the LOINC term identifier, which is a unique numeric identifier with a check digit
 - LONG_COMMON_NAME - the LOINC Long Common Name for the term
 - ORDER_OBS - whether the LOINC term can be used as an Order, an Observation, or Both. In this file, the only values contained in the ORDER_OBS column are "Both" and "Order".

Sort order:
This file is sorted alphabetically by LOINC Long Common Name.

*Note: This file does not include any deprecated terms.