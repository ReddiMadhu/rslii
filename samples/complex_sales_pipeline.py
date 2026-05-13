import pandas as pd
import numpy as np

def load_sources():
    """Load all necessary data sources."""
    sales = pd.read_csv("data/sales_2023.csv")
    customers = pd.read_excel("data/customers.xlsx")
    products = pd.read_parquet("data/products.parquet")
    return sales, customers, products

def enrich_sales(sales_df, customers_df, products_df):
    """Join sales with customer and product details."""
    # Add customer information
    enriched = sales_df.merge(
        customers_df, 
        on="customer_id", 
        how="left"
    )
    
    # Add product information
    enriched = enriched.merge(
        products_df, 
        on="product_id", 
        how="left"
    )
    return enriched

def calculate_metrics(df):
    """Calculate regional sales metrics."""
    # Filter for completed transactions
    completed = df[df["status"] == "COMPLETED"]
    
    # Apply discount logic
    completed["final_price"] = np.where(
        completed["customer_tier"] == "VIP",
        completed["price"] * 0.9,
        completed["price"]
    )
    
    # Group by region and product category
    metrics = (
        completed
        .groupby(["region", "category"])
        .agg({
            "final_price": "sum",
            "quantity": "sum",
            "transaction_id": "count"
        })
        .rename(columns={"transaction_id": "order_count"})
        .reset_index()
    )
    
    # Sort by highest revenue
    metrics = metrics.sort_values("final_price", ascending=False)
    
    return metrics

def build_pipeline():
    # 1. Extract
    sales, customers, products = load_sources()
    
    # 2. Transform: Enrichment
    enriched_data = enrich_sales(sales, customers, products)
    
    # 3. Transform: Aggregation
    final_metrics = calculate_metrics(enriched_data)
    
    # 4. Load
    final_metrics.to_csv("output/regional_sales_report.csv", index=False)
    
    # Bonus: Generate a separate summary for high-value regions
    high_value = final_metrics[final_metrics["final_price"] > 100000]
    high_value.to_json("output/high_value_regions.json")

if __name__ == "__main__":
    build_pipeline()
