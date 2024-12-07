from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid  # To generate unique store codes

# Initialize the SQLAlchemy instance
db = SQLAlchemy()

# User model (website access role)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    age = db.Column(db.String(15), nullable=False , default = '--')
    gender = db.Column(db.String(15), nullable=False , default = '--')
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Password should be hashed
    role_name = db.Column(db.String(20), nullable=False, default='User')  # Website role (Admin, User)

    # Relationship to UserStore (linking to stores)
    stores = db.relationship('Store', secondary='user_store', backref='users')
    user_store = db.relationship('UserStore', backref='user_relation', lazy=True)

# UserStore model (store-specific roles: Store Manager, Employee)
class UserStore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    role_name = db.Column(db.String(50), nullable=False)  # Store-specific role (e.g., Store Manager, Employee) # pore role name ta change kore debo
    
    # Relationships
    user = db.relationship('User', backref='user_store_relation', overlaps='stores,users',lazy=True)  # Change 'user' to 'user_store_back'
    store = db.relationship('Store', backref='user_store', overlaps='stores,users',lazy=True)


class Store(db.Model):
    __tablename__ = 'store'
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(255), nullable=False)
    store_address = db.Column(db.String(255), nullable=False)
    owner_name = db.Column(db.String(255), nullable=False)
    business_email = db.Column(db.String(255), nullable=False)
    gstNumber = db.Column(db.String(255), nullable=False)
    store_type = db.Column(db.String(255), nullable=False,default='Retail')
    profit = db.Column(db.Float, nullable=False, default=0.0)
    unique_code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    categories = db.relationship('Category', backref='store', lazy=True, cascade='all, delete-orphan')

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    C_unique_id = db.Column(db.String(20), unique=True, nullable=False)
    products = db.relationship('Product', backref='category', lazy=True, cascade='all, delete-orphan')

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    manufacture_date = db.Column(db.Date, nullable=True)
    expire_date = db.Column(db.Date, nullable=True)
    cost_price = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, index=True)
    P_unique_id = db.Column(db.String(20), unique=True, index=True, nullable=False)
    transaction_items = db.relationship('TransactionItem', backref=db.backref('products_in_transaction', lazy=True))

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    customer_name = db.Column(db.String(100), nullable=False)
    bill_number = db.Column(db.String(50), unique=True, nullable=False)  # This acts as the order/bill ID
    transaction_type = db.Column(db.String(50), nullable=False)  # Or use Python Enum
    payment_method = db.Column(db.String(50), nullable=True, default="cash")
    sucess = db.Column(db.String(50), nullable=True, default="yes") #yes or no

    transaction_items = db.relationship('TransactionItem', backref='transaction', lazy=True, cascade='all, delete-orphan')


class TransactionItem(db.Model):
    __tablename__ = 'transaction_item'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)  # Use 'id' instead of 'bill_number'
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # Ensure quantity > 0 in application logic
    selling_price = db.Column(db.Integer, nullable=False)
    cost_price = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)  # selling_price * quantity
    total_cost_price = db.Column(db.Integer, nullable=False)  # cost_price * quantity


