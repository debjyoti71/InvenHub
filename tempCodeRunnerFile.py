# # Wrap the logic inside the application context
# with app.app_context():
#     for item in transactions_data:
#         date = item["date"]
#         quantity = item["quantity"]
#         sell_price = item["sell_price"]
#         cost_price = item["cost_price"]
#         product = item["product"]

#         # Define the cart as needed (e.g., a single product with its details)
#         cart = [
#             {
#                 "product_name": product,
#                 "quantity": quantity,
#             }
#         ]

#         # Create the transaction object
#         transaction = Transaction(
#             store_id=store_id,
#             transaction_date=date,
#             updated_date=date,
#             customer_name="System",
#             bill_number=f"ORD{store_id}{str(uuid.uuid4())[:7]}",
#             transaction_type='order',
#             payment_method='cash',
#             total_selling_price=sell_price * quantity,
#             total_cost_price=cost_price * quantity,
#             cart=cart,
#             success='yes',
#             type='checkout'
#         )

#         # Add the transaction to the session
#         db.session.add(transaction)

#     # Commit all the transactions to the database
#     db.session.commit()

        