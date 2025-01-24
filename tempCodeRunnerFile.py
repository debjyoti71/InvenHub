# Convert 'Order Date' to datetime (keep as datetime, not string)
# df['Order Date'] = pd.to_datetime(df['Order Date'], errors='coerce', dayfirst=True)

# # Ensure Flask application context is active
# with app.app_context():
#     # Step 1: Create all categories and products
#     products = []
#     product_lookup = {}  # For faster lookups
#     for index, row in df.iterrows():
#         product_name = row['Product']
#         quantity_ordered = row['Quantity Ordered']
#         price_each = row['Price Each']

#         # Skip invalid rows
#         if pd.isna(quantity_ordered) or pd.isna(price_each) or quantity_ordered <= 0 or price_each <= 0:
#             print(f"Skipping row {index} due to invalid data.")
#             continue

#         # Dynamically derive category
#         category_name = derive_category(product_name)

#         # Handle category creation
#         category = handle_category(category_name, store_id)

#         # Handle product creation
#         product = handle_product(product_name, category, price_each, quantity_ordered)
#         products.append(product)
#         product_lookup[product_name] = product  # Add to lookup dictionary

#     # Commit all categories and products
#     db.session.commit()
#     print("Categories and products successfully created.")

#     # Step 2: Create transactions and transaction items
#     transactions = []
#     transaction_items = []
#     for index, row in df.iterrows():
#         product_name = row['Product']
#         quantity_ordered = row['Quantity Ordered']
#         price_each = row['Price Each']
#         order_date = row['Order Date']

#         # Skip invalid rows
#         if pd.isna(quantity_ordered) or pd.isna(price_each) or pd.isna(order_date):
#             print(f"Skipping row {index} due to invalid or missing data.")
#             continue

#         # Get product from lookup
#         product = product_lookup.get(product_name)
#         if not product:
#             print(f"Product {product_name} not found. Skipping row {index}.")
#             continue

#         # Create transaction
#         bill_number = f"SALE{store_id}{str(uuid.uuid4())[:6]}"
#         total_selling_price = round(quantity_ordered * price_each, 2)
#         new_transaction = Transaction(
#             store_id=store_id,
#             transaction_date=order_date,
#             customer_name="None",  # Default customer
#             bill_number=bill_number,
#             transaction_type="Sale",
#             type="checkout",
#             total_selling_price=total_selling_price,
#             payment_method="cash",
#             success="yes",
#         )
#         transactions.append(new_transaction)

#         # Create transaction item
#         cost_price = round(price_each * 0.7, 2)
#         transaction_item = TransactionItem(
#             transaction_id=None,  # Will be set automatically
#             product_id=product.id,
#             quantity=quantity_ordered,
#             cost_price=cost_price,
#             selling_price=price_each,
#             total_price=total_selling_price,
#             total_cost_price=round(quantity_ordered * cost_price, 2),
#         )
#         transaction_items.append(transaction_item)

#     # Bulk insert transactions and transaction items
#     db.session.bulk_save_objects(transactions)
#     db.session.commit()  # Commit transactions first to get their IDs

#     # Assign correct transaction IDs to transaction items
#     for i, item in enumerate(transaction_items):
#         item.transaction_id = transactions[i].id

#     db.session.bulk_save_objects(transaction_items)
#     db.session.commit()
#     print("Transactions and transaction items successfully created.")