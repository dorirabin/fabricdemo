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

from pyspark.sql.functions import col, rand, when, lit, expr, round

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Configuration: Update these values after deployment
kusto_cluster = "https://trd-sketzz3a64smc48ffd.z1.kusto.fabric.microsoft.com"
kusto_db = "maritimeEH"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 1. CREATE CARGO MASTER (The "What" is being insured)
cargo_data = [
    ("C01", "Crude Oil", "Hazardous", 85000000), 
    ("C02", "LNG", "Hazardous", 120000000),     
    ("C03", "Refined Petroleum", "Hazardous", 95000000),
    ("C04", "General Containers", "Standard", 40000000),
    ("C05", "Automobiles", "Standard", 150000000)
]
df_cargo = spark.createDataFrame(cargo_data, ["CargoID", "CargoType", "HandlingClass", "InsuredValue"])
df_cargo.write.mode("overwrite").format("delta").saveAsTable("CargoMaster")

# 2. UPDATED POLICIES (Adding high deductibles for high-risk coverage)
policies_data = [
    ("POL-9901", "Hull & Machinery", 250000, 50000000),   # $250k Deductible
    ("POL-9902", "War Risk", 1000000, 100000000),      # $1M Deductible (High risk, high skin-in-the-game)
    ("POL-9903", "Cargo Protection", 100000, 25000000),
    ("POL-9904", "Total Loss Only", 5000000, 200000000) # Only pays for catastrophic loss
]
columns_policy = ["PolicyID", "PolicyType", "Deductible", "CoverageLimit"]
df_policies = spark.createDataFrame(policies_data, columns_policy)
df_policies.write.mode("overwrite").format("delta").saveAsTable("Policies")



# Create the Company/Owner Dimension Table
company_data = [
    ("C-FRO", "Frontline plc", "Limassol, Cyprus", 73, "High"),      # Large VLCC/Suezmax fleet
    ("C-STNG", "Scorpio Tankers", "Monaco", 110, "Medium"),          # Major product tanker fleet
    ("C-DHT", "DHT Holdings", "Hamilton, Bermuda", 24, "Medium"),    # Pure-play VLCC operator
    ("C-EURN", "Euronav", "Antwerp, Belgium", 50, "High"),           # Independent crude tanker giant
    ("C-TK", "Teekay Corp", "Vancouver, Canada", 34, "Medium"),      # Mid-sized crude tanker leader
    ("C-MOL", "Mitsui O.S.K.", "Tokyo, Japan", 935, "Low")           # Massive diversified group
]

columns_company = ["CompanyID", "CompanyName", "Headquarters", "TotalFleetSize", "RiskRating"]
df_companies = spark.createDataFrame(company_data, columns_company)
df_companies.write.mode("overwrite").format("delta").saveAsTable("Companies")

company_ids = [row['CompanyID'] for row in df_companies.select("CompanyID").collect()]

print("All dimension tables created with 2026 market data.")



# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql.functions import col, to_json

# 3. UPDATED MARITIME ZONES (Adding the Premium Multiplier)
# The multiplier represents the 'surcharge' for being in that zone

# 3. UPDATED MARITIME ZONES (Adding the Premium Multiplier)
# The multiplier represents the 'surcharge' for being in that zone
zones_data = [
    ("RedZone", "Iran High Risk Zone", "Critical", 5.5),  # 5.5x Premium surcharge
    ("YellowZone", "Western Transit", "Medium", 1.2),   # 1.2x Premium surcharge
    ("GreenZone", "Safe Open Water", "Low", 1.0)         # Baseline
]
columns_zone = ["ZoneID", "ZoneName", "RiskLevel", "PremiumMultiplier"]
df_zones = spark.createDataFrame(zones_data, columns_zone)
#df_zones.write.mode("overwrite").format("delta").saveAsTable("MaritimeZones")

# 1. Load your two files from the Lakehouse Files store
df1 = spark.read.option("multiLine", "true").format("json").load("Files/HormuzShippingCorridor.geojson")
exploded_df1 = df1.selectExpr("explode(features) as feature")

df2 = spark.read.option("multiLine", "true").format("json").load("Files/hormuz_risk_zone.geojson")
exploded_df2 = df2.selectExpr("explode(features) as feature")

# 2. Union the two files together raw
merged_raw_df = exploded_df1.union(exploded_df2)

# 3. Directly map properties straight out of the native GeoJSON structure
final_maritime_zones_df = merged_raw_df.select(
    col("feature.properties.ZoneID").alias("ZoneID"),
    col("feature.properties.ZoneName").alias("ZoneName"),
    col("feature.properties.RiskLevel").alias("RiskLevel"),
    col("feature.properties.PremiumMultiplier").cast("decimal(10,2)").alias("PremiumMultiplier"),
    # FIX: FORCING THE NAME AND CONVERTING COMPLEX STRUCT TO A STRING
    to_json(col("feature.geometry")).alias("ZonePolygonGeoJSON")
    #col("feature.geometry").alias("ZonePolygonGeoJSON")
)

# 4. Overwrite your clean, unified table back into your Lakehouse Tables section
final_maritime_zones_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("maritimezones")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


# 4. ENRICHED VESSEL MASTER (Linking Age to Hull Value)
# Pull unique vessels from the real-time 'maritimeAIS' table in your Eventhouse (Kusto)

kusto_query = "maritimeAIS | summarize arg_max(TransmittedUtc, *) by MMSI | project MMSI, ShipName, VesselType"

vessel_raw_df = (
    spark.read
    .format("com.microsoft.kusto.spark.datasource")
    .option("accessToken", mssparkutils.credentials.getToken(kusto_cluster)) \
    .option("kustoCluster", kusto_cluster) \
    .option("kustoDatabase", kusto_db) \
    .option("kustoQuery", kusto_query) \
    .load()
)



# Insurance Logic: Older ships (lower YearBuilt) have lower HullValue but higher risk
#enriched_vessels = vessel_raw_df.withColumn("YearBuilt", (rand() * 25 + 2000).cast("int")) \
#    .withColumn("HullValue", 
#        when(col("YearBuilt") < 2010, (rand() * 30000000 + 10000000).cast("int"))  # Older: $10M-$40M
#        .otherwise((rand() * 60000000 + 50000000).cast("int"))  # Newer: $50M-$110M
#    ).withColumn("PolicyID", 
#        expr("element_at(array('POL-9901', 'POL-9902', 'POL-9903', 'POL-9904'), cast(rand()*4 + 1 as int))")
#    ).withColumn("CargoID", 
#        expr("element_at(array('C01', 'C02', 'C03', 'C04', 'C05'), cast(rand()*5 + 1 as int))")
#    )


# 1. Define the random reference column first
vessel_with_rand = vessel_raw_df.withColumn("rand_skew", rand())

# 2. Run your enrichment pipeline using that reference
enriched_vessels = vessel_with_rand.withColumn("YearBuilt", (col("rand_skew") * 25 + 2000).cast("int")) \
    .withColumn("HullValue", 
        when(col("YearBuilt") < 2010, (rand() * 30000000 + 10000000).cast("int"))
        .otherwise((rand() * 60000000 + 50000000).cast("int"))
    ).withColumn("PolicyID", 
        expr("element_at(array('POL-9901', 'POL-9902', 'POL-9903', 'POL-9904'), cast(rand()*4 + 1 as int))")
    ).withColumn("CargoID", 
        when(col("rand_skew") < 0.50, "C01")      # 50% chance
        .when(col("rand_skew") < 0.80, "C05")     # 30% chance
        .when(col("rand_skew") < 0.90, "C03")     # 10% chance
        .when(col("rand_skew") < 0.95, "C04")     # 5% chance
        .otherwise("C02")                         # 5% chance
    ).drop("rand_skew")                           # Clean up the temporary column

# ATTENTION: AI-generated code can include errors or operations you didn't intend. Review the code in this cell carefully before running it.

# 1. Create a skewed list in Python
# Let's say we want the 1st company to appear 5x more, and the 2nd to appear 3x more
skewed_companies = []
for i, company in enumerate(company_ids):
    if i == 0:
        multiplier = 5  # First company gets 10x copies
    elif i == 1:
        multiplier = 3   # Second company gets 5x copies
    elif i == 2:
        multiplier = 2   # Second company gets 5x copies
    else:
        multiplier = 1   # All other companies get 1 copy (ensures they exist!)
        
    skewed_companies.extend([company] * multiplier)
    
# 2. Build the SQL array string from this guaranteed list
company_list_sql = ", ".join([f"'{c}'" for c in skewed_companies])
total_slots = len(skewed_companies)

# 3. Update the expression
expr_str = (
    f"element_at(array({company_list_sql}), cast(rand()*{total_slots} + 1 as int))"
)

enriched_vessels = enriched_vessels.withColumn("CompanyID", expr(expr_str))


# 3. JOIN WITH THE COMPANIES TABLE
# We use 'left' join so you don't lose any vessels if an ID match fails
final_vessel_df = enriched_vessels.join(
    df_companies.select("CompanyID", "CompanyName"), 
    on="CompanyID", 
    how="left"
)

final_count = final_vessel_df.count()
print(f"Final enriched dataframe size: {final_count} rows.")

final_vessel_df.write.mode("overwrite").format("delta").saveAsTable("Vessels")

print("All insurance entities (CargoMaster, Policies, MaritimeZones, Vessels, Companies) successfully created.")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 5. SOME UPDATES / FIXES for SIMULATED_TANKER_01 SHIPS 


from pyspark.sql.types import IntegerType
from delta.tables import DeltaTable

df = spark.sql("SELECT * FROM maritimeLH.dbo.vessels WHERE ShipName = 'SIMULATED_TANKER_01' ")
display(df)

# 1. Define the data with the replaced PolicyID
data = [{
    "CompanyID": "C-STNG",
    "MMSI": 999888777,
    "ShipName": "SIMULATED_TANKER_01",
    "VesselType": "80",
    "YearBuilt": 2022,
    "HullValue": 65,
    "PolicyID": "POL-9901",  # <-- Updated to 9901
    "CargoID": "C03",
    "CompanyName": "Scorpio Tankers"
}]

# 2. Create the PySpark DataFrame
df2 = spark.createDataFrame(data)

# 3. Cast the necessary columns to Integer based on your schema tags
# Import IntegerType to avoid NameError and cast numeric fields properly

df2 = df2.withColumn("MMSI", df2["MMSI"].cast(IntegerType())) \
       .withColumn("YearBuilt", df2["YearBuilt"].cast(IntegerType())) \
       .withColumn("HullValue", df2["HullValue"].cast(IntegerType()))

# Preview the row that will be appended
display(df2)

# 3. Access the target Delta table
# Use the exact table path/name where your data lives
target_table = DeltaTable.forName(spark, "maritimeLH.dbo.vessels")

# 4. Perform the Merge (Update) operation
target_table.alias("target") \
    .merge(
        df2.alias("updates"),
        "target.ShipName = updates.ShipName" # The matching key
    ) \
    .whenMatchedUpdateAll() \
    .whenNotMatchedInsertAll() \
    .execute()



# Append the new row into the existing vessels table in the default lakehouse
# Make sure the target table name matches how it was created earlier ('Vessels')#df2.write.mode("append").format("delta").saveAsTable("Vessels")





# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# 6. MORE UPDATES / FIXES for EAST_SIMULATED_TANKER_02 SHIPS 


from pyspark.sql.types import IntegerType
from delta.tables import DeltaTable


df = spark.sql("SELECT * FROM maritimeLH.dbo.vessels WHERE ShipName = 'EAST_SIMULATED_TANKER_02' ")
display(df)

# 1. Define the data with the replaced PolicyID
data = [{
    "CompanyID": "C-STNG",
    "MMSI": 999888778,
    "ShipName": "EAST_SIMULATED_TANKER_02",
    "VesselType": "80",
    "YearBuilt": 2020,
    "HullValue": 100,
    "PolicyID": "POL-9902",  # <-- Updated to 9902 (War Risk Policy)
    "CargoID": "C05", # Automobile
    "CompanyName": "Scorpio Tankers"
}]

# 2. Create the PySpark DataFrame
df3 = spark.createDataFrame(data)

# 3. Cast the necessary columns to Integer based on your schema tags
# Import IntegerType to avoid NameError and cast numeric fields properly

df3 = df3.withColumn("MMSI", df3["MMSI"].cast(IntegerType())) \
       .withColumn("YearBuilt", df3["YearBuilt"].cast(IntegerType())) \
       .withColumn("HullValue", df3["HullValue"].cast(IntegerType()))

# Preview the row that will be appended
display(df3)


# 4. Perform the Merge (Update) operation
target_table.alias("target") \
    .merge(
        df3.alias("updates"),
        "target.ShipName = updates.ShipName" # The matching key
    ) \
    .whenMatchedUpdateAll() \
    .whenNotMatchedInsertAll() \
    .execute()


# Append the new row into the existing vessels table in the default lakehouse
# Make sure the target table name matches how it was created earlier ('Vessels')
#df3.write.mode("append").format("delta").saveAsTable("Vessels")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
