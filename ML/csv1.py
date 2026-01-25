import pandas as pd

# Load Excel
excel_file = "D:/RVCE/3rd sem/internship COE/parlorpal_main/ML/social_media_engagement_data.xlsx"
df_excel = pd.read_excel(excel_file)

# Show first 5 rows
print("First 5 rows:")
print(df_excel.head())

# Show last 5 rows
print("\nLast 5 rows:")
print(df_excel.tail())

# Show columns
print("\nColumns:")
print(df_excel.columns)

# Excel info
print("Excel Info:")
print(df_excel.info())