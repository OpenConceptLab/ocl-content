## **OCL Collection Cleaner/Modernizer**

This Python script, available as a [Colab Notebook](https://colab.research.google.com/drive/1h4arv7KE9bw_Cj5VdrijufeSX8nASP51), is designed to clean up and "modernize" OCL collection references.

### **The Problem** 🧐

As OCL collections grow, they can accumulate a large number of versioned concept references. This can lead to several issues:
* **Unresolved Concepts:** New concepts added to a collection may appear as "unresolved."
* **Versioning Failures:** Attempts to publish new versions of the collection may fail without a clear explanation.
* **Performance Degradation:** The collection becomes difficult to manage and may not perform as expected.

These problems often stem from having too many resolved source versions, which can bog down the system.

### **The Solution** ✨

This script provides a straightforward way to clean up your collection by removing outdated, versioned references and replacing them with clean, un-versioned ones. The script automates the creation of bulk import files for OCL, which simplifies the process significantly.

### **Key Features** 🚀
* **Automated Reference Cleaning:** Automatically identifies and processes versioned references.
* **Bulk Import File Generation:** Creates ready-to-use CSV files for OCL's bulk import interface.
* **Safe by Design:** Separates the deletion and addition of references into two distinct files, giving you more control over the process.

### **How it Works** ⚙️

The script performs the following high-level steps:
1.  **Reads a collection export:** It ingests a CSV export of your OCL collection.
2.  **Identifies versioned references:** It scans the references and isolates the ones that are tied to specific source or concept versions.
3.  **Generates bulk import files:** It creates two key files to manage the cleanup process.

### **Generated Files** 📂

The script will produce two primary output files:

1.  **`ocl_bulk_delete_references.csv`**
    * **Purpose:** This file contains a list of all the versioned references that should be removed from your collection.
    * **Format:** A CSV file formatted for OCL's bulk import tool with the `operation` column set to `DELETE`.

2.  **`ocl_bulk_add_references.csv`**
    * **Purpose:** This file contains the cleaned list of references to be added back to your collection. These references will not have version numbers.
    * **Format:** A CSV file formatted for OCL's bulk import tool with the `operation` column set to `ADD`.

### **Usage Instructions** 📝

Follow these steps carefully to clean up your collection.

**⚠️ Important:** This process involves making significant changes to your collection. **Always back up your collection data and take an inventory of your concepts and mappings before you begin.** This will allow you to verify that no data was lost during the cleanup process.

1.  **Export Your Collection:**
    * Navigate to your collection in OCL.
    * Go to the **"Concepts"** or **"Mappings"** tab.
    * Use the export feature to download a CSV file of your collection's references.

2.  **Open the Colab Notebook:**
    * Access the [OCL Modernizer Notebook](https://colab.research.google.com/drive/1h4arv7KE9bw_Cj5VdrijufeSX8nASP51).
    * Make a copy of the notebook in your own Google Drive or on your local machine so you can edit and run it.

3.  **Run the Script:**
    * Follow the instructions within the notebook.
    * You will be prompted to upload the export file you downloaded in Step 1.
    * The script will process the file and generate the `ocl_bulk_delete_references.csv` and `ocl_bulk_add_references.csv` files.

4.  **Perform the Bulk Import in OCL:**
    * First, use the OCL import tool to process the `ocl_bulk_delete_references.csv` file. This will remove the outdated references.
    * Next, import the `ocl_bulk_add_references.csv` file. This will add the clean, modernized references back into your collection.

5.  **Verify Your Collection:**
    * After the import process is complete, thoroughly check your collection.
    * Ensure that concepts are resolving correctly and that your concept/mapping counts match your pre-cleanup inventory.
    * Test adding a new concept and creating a new version of the collection to confirm that the underlying issues have been resolved.

### **Questions or Issues?**

If you encounter any problems or have questions, please open an issue in this repository or in the [OCL Issues tracker](https://github.com/OpenConceptLab/ocl_issues).
