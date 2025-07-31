The LinguisticVariants file contains the following files:

 - LinguisticVariants.csv
 - deAT24LinguisticVariant.csv
 - deDE15LinguisticVariant.csv
 - elGR17LinguisticVariant.csv
 - esAR7LinguisticVariant.csv
 - esES12LinguisticVariant.csv
 - esMX28LinguisticVariant.csv
 - etEE10LinguisticVariant.csv
 - frBE23LinguisticVariant.csv
 - frCA8LinguisticVariant.csv
 - frFR18LinguisticVariant.csv
 - itIT16LinguisticVariant.csv
 - koKR13LinguisticVariant.csv
 - nlNL22LinguisticVariant.csv
 - plPL29LinguisticVariant.csv
 - ptBR11LinguisticVariant.csv
 - ruRU20LinguisticVariant.csv
 - trTR19LinguisticVariant.csv
 - ukUA30LinguisticVariant.csv 
 - zhCN5LinguisticVariant.csv
 - LinguisticVariantsReadMe.txt


The first row in each comma separated file contains column headings. All other rows contain data. The details for each table are provided below.

-----------------------------------
LinguisticVariants.csv

Overview:
This file contains a list of all of the LOINC Linguistic Variant(s) that are available and their producers (translators). LOINC Linguistic Variant(s) are provided by an international community of volunteer translators.

Columns:
 - ID - the unique identifier for a particular language variant within the LOINC database. This identifier does not have any meaning outside of LOINC.
 - ISO_LANGUAGE - the ISO language code
 - ISO_COUNTRY - the ISO country code
 - LANGUAGE_NAME - a combination of the name of the language and the country in which that variant is used
 - PRODUCER - the person or organization that provided the translation

-----------------------------------
xxYY##LinguisticVariant.csv

Overview:
A separate file is provided for each LOINC linguistic variant. Each individual file is named as xxYY##LinguisticVariant.csv, where {xx} is the ISO language code, {YY} is the ISO country code, and {##} is the unique identifier assigned to a particular variant within the LOINC database, which corresponds to the value in the "ID" field described above. 

Each Linguistic Variant file is based on the translations provided by the LOINC translator. Translations may be provided for one or more of the major Parts of a LOINC name (Component, Property, Time, System, Scale, and Method), Long Common Name, Short Name, and Related Names, and/or a Linguistic Variant Display Name may be provided. The Linguistic Variant Display Name is a translation of the LOINC term as a whole that is somewhat analogous to the LONG_COMMON_NAME, except the style and format is left up to the translator and it is not a direct translation of any of the formal LOINC Parts or Names.

Each file contains the columns listed below, which may or may not be populated depending on the translations that were provided for that specific language variant. For descriptions of each column, except LinguisticVariantDisplayName, see Appendix A in the LOINC Users' Guide.

 - LOINC_NUM
 - COMPONENT
 - PROPERTY
 - TIME_ASPCT
 - SYSTEM
 - SCALE_TYP
 - METHOD_TYP
 - CLASS
 - SHORTNAME
 - LONG_COMMON_NAME
 - RELATEDNAMES2
 - LinguisticVariantDisplayName