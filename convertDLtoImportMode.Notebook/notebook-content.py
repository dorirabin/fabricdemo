# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "e840bf2c-5866-42e4-91c2-3e6aca5ede5e",
# META       "default_lakehouse_name": "maritimeLH",
# META       "default_lakehouse_workspace_id": "821daf86-9ecb-4d7f-a7d9-9cc3c0541028",
# META       "known_lakehouses": [
# META         {
# META           "id": "e840bf2c-5866-42e4-91c2-3e6aca5ede5e"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# Install sempy-labs package in this Spark session
#%pip install sempy-labs
%pip install semantic-link-labs==0.17.0  


# After this finishes, run the following in a separate cell once:
# notebookutils.session.restartPython()
# Then re-run the migration cell below.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!

# After installation, you typically need to restart the Python process for the package to be importable
# In Fabric notebooks, use notebookutils.session.restartPython() for that purpose.

from sempy_labs import migration

# Define your parameters correctly as strings
dataset = 'maritimeSM'  # Enter the name or ID of your semantic model
workspace = 'aitour2'   # Enter the name or ID of the workspace in which the semantic model resides

# Run the migration from Direct Lake to Import mode
migration.migrate_direct_lake_to_import(dataset=dataset, workspace=workspace)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
