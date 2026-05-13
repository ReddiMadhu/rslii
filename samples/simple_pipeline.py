import pandas as pd

def clean_data(df):
    """Clean the raw input data."""
    # Drop rows with missing values
    df = df.dropna()
    # Ensure prices are positive
    df = df[df["price"] > 0]
    return df

def main():
    # Read raw inventory data
    inventory = pd.read_csv("inventory_raw.csv")
    
    # Apply cleaning function
    cleaned_inventory = clean_data(inventory)
    
    # Calculate total value
    cleaned_inventory["total_value"] = cleaned_inventory["quantity"] * cleaned_inventory["price"]
    
    # Save the cleaned data
    cleaned_inventory.to_parquet("inventory_clean.parquet")

if __name__ == "__main__":
    main()
