from app import app, db
from models import Product, Transaction, TransactionItem

store_id = 1

with app.app_context():
    # Fetch all transactions for the given store
    transactions = Transaction.query.filter_by(store_id=store_id).all()

    for t in transactions:
        # Fetch all transaction items for the current transaction
        transaction_items = TransactionItem.query.filter_by(transaction_id=t.id).all()

        # Build the cart as a dictionary
        cart = {}
        for item in transaction_items:
            product = Product.query.get(item.product_id)
            if product:
                # Add the product to the cart with its quantity
                cart[product.P_unique_id] = item.quantity

        # Assign the cart to the transaction (as JSON string)5
        t.cart = cart

    # Commit all changes to the database
    db.session.commit()

print("Cart field has been successfully updated for all transactions.")
