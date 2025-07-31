***This is an Alpha release***

The DocumentOntologyOWL directory contains the following files:

 - DocumentOntology.owl
 - DocumentOntologyOwlReadMe.txt


-----------------------------------
DocumentOntology.owl

OWL Overview: 
OWL is a file format that stands for "Web Ontology Language". In general, knowledge expressed in OWL format is computer-readable and can represent rich knowledge about resources (such as LOINC parts and LOINC terms) and the relationships between them.  Since OWL is a standard format for representing complex knowledge, it is possible to query that knowledge, build visual representations and make inferences if you have the right tools.  For further information about OWL and ontology, users are referred to web resources (examples, http://owl.cs.manchester.ac.uk/ and https://www.w3.org/TR/owl-guide/).

The DocumentOntology OWL file:
The LOINC DocumentOntology.owl file can be viewed using an ontology editing and browsing tool such as Protege (http://protege.stanford.edu). Users who are familiar with such ontology tools should be able to run queries, and view inferences about the relationships between the individual LOINC document concepts. 

This is an Alpha release, meaning that it is part of a testing process, and the LOINC team welcomes comments regarding its usability and content.  The file in its current form is generated directly from the LOINC database using a Perl script that writes the data in OWL Functional Syntax. OWL Functional Syntax is one of the file formats available for saving OWL files directly from the Protege application but is only one of several possible formats. This file was developed by the LOINC team with the advice and input of Harold Solbrig and Chris Chute from Johns Hopkins University.

File content:
All the axis values within the 5 axes of the LOINC Document Ontology are represented hierarchically as classes with asserted subclass relationships. The individual LOINC documents are represented as 'equivalent' classes which are fully defined by their relationships to the axis value classes, allowing a reasoning engine (such as those available within Protege) to infer relationships between the LOINC documents.  
