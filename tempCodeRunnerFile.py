from app import app, db
from models import Product, Category, Transaction, TransactionItem
import pandas as pd
import os
import uuid
from datetime import datetime

# Define the store ID
store_id = 1

# Read the CSV file
file_path = os.path.join('static', 'Yearly_Sales_Data.csv')
if not os.path.exists(file_path):
    raise FileNotFoundError(f"The file {file_path} does not exist.")

df = pd.read_csv(file_path)

# Convert 'Order Date' format from mm/dd/yy to dd/mm/yy
df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%y')

# Debug: Check the transformed data
print("Sample Data:")
print(df.head(20))
print(df.info())

# Helper Functions
def handle_category(category_name, store_id):
    """Check or create a category dynamically."""
    category = Category.query.filter_by(category_name=category_name, store_id=store_id).first()
    if not category:
        categories_in_store = Category.query.filter_by(store_id=store_id).count()
        C_unique_id = f"{store_id}{categories_in_store + 1}0"
        category = Category(category_name=category_name, store_id=store_id, C_unique_id=C_unique_id)
        db.session.add(category)
        print(f"New Category Created: {category_name}, Unique ID: {C_unique_id}")
    return category

def handle_product(product_name, category, price_each, quantity_ordered):
    """Always create a new product dynamically."""
    product = Product.query.filter_by(name=product_name).first()
    if not product:
        cost_price = round(price_each * 0.7, 2)  # Assuming cost price is 70% of selling price
        products_in_category = Product.query.filter_by(category_id=category.id).count()
        P_unique_id = f"{category.C_unique_id}{products_in_category + 1}"
        product = Product(
            name=product_name,
            cost_price=cost_price,
            selling_price=price_each,
            stock=quantity_ordered,
            category_id=category.id,
            P_unique_id=P_unique_id,
        )
        db.session.add(product)
        print(f"New Product Added: {product.name}, Unique ID: {P_unique_id}")
    return product

# Automatically derive categories from products
def derive_category(product_name):
    """Classify products dynamically based on their names."""
    categories = {
        "Monitor": "Electronics",
        "Batteries": "Accessories",
        "Headphones": "Accessories",
        "Cable": "Accessories",
        "Dryer": "Home Appliances",
        "Washing Machine": "Home Appliances",
        "Phone": "Phones",
        "Laptop": "Computers",
        "TV": "Electronics",
    }
    for keyword, category in categories.items():
        if keyword in product_name:
            return category
    return "Miscellaneous"  # Default category

df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce', dayfirst=True)

print(df.head())

# Ensure Flask application context is active
with app.app_context():
    # Step 1: Extract unique products
    unique_products = df[['Product', 'Price Each']].drop_duplicates()
    print(unique_products)
    print(len(unique_products))
    product_lookup = {}  # Dictionary for faster lookups

    # Step 2: Process unique products
    for index, row in unique_products.iterrows():
        product_name = row['Product']
        price_each = row['Price Each']

        # Skip invalid rows
        if pd.isna(price_each) or price_each <= 0:
            print(f"Skipping product {product_name} due to invalid price data.")
            continue

        # Dynamically derive category
        category_name = derive_category(product_name)

        # Handle category creation
        category = handle_category(category_name, store_id)

        # Handle product creation with initial stock as 0
        product = handle_product(product_name, category, price_each, quantity_ordered=0)  # No stock initially
        product_lookup[product_name] = product  # Add to lookup dictionary
    # print(product_lookup)

    # Commit all categories and products
    db.session.commit()
    print("All unique categories and products have been successfully created.")

    # Step 3: Create transactions and transaction items
    transactions = []
    transaction_items = []
    for index, row in df.iterrows():
        product_name = row['Product']
        quantity_ordered = row['Quantity Ordered']
        price_each = row['Price Each']
        order_date = row['Order Date']

        # Skip invalid rows
        if pd.isna(quantity_ordered) or pd.isna(price_each) or pd.isna(order_date):
            print(f"Skipping row {index} due to invalid or missing data.")
            continue

        # Get product from lookup
        product = product_lookup.get(product_name)
        if not product:
            print(f"Product {product_name} not found. Skipping row {index}.")
            continue

        # Create transaction
        bill_number = f"SALE{store_id}{str(uuid.uuid4())[:6]}"
        total_selling_price = round(quantity_ordered * price_each, 2)
        cart = {product.P_unique_id:quantity_ordered}
        new_transaction = Transaction(
            store_id=store_id,
            transaction_date=order_date,
            customer_name="None",  # Default customer
            bill_number=bill_number,
            transaction_type="Sale",
            type="checkout",
            total_selling_price=total_selling_price,
            payment_method="cash",
            cart = cart,
            success="yes",
        )
        transactions.append(new_transaction)

        # Create transaction item
        cost_price = round(price_each * 0.7, 2)
        transaction_item = TransactionItem(
            transaction_id=None,  # Will be set automatically
            product_id=product.id,
            quantity=quantity_ordered,
            cost_price=cost_price,
            selling_price=price_each,
            total_price=total_selling_price,
            total_cost_price=round(quantity_ordered * cost_price, 2),
        )
        transaction_items.append(transaction_item)

    # Bulk-insert transactions
    db.session.bulk_save_objects(transactions)
    db.session.flush()  # Ensures transactions are assigned IDs before commit

    # Assign transaction IDs to transaction items
    for i, item in enumerate(transaction_items):
        item.transaction_id = transactions[i].id

    # Bulk-insert transaction items
    db.session.bulk_save_objects(transaction_items)
    db.session.commit()
    print("Transactions and transaction items successfully created.")
