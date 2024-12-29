from flask_sqlalchemy import SQLAlchemy
from datetime import datetime,timedelta
import uuid  # To generate unique store codes

# Initialize the SQLAlchemy instance
db = SQLAlchemy()

def get_india_time():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

# User model (website access role)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    age = db.Column(db.String(15), nullable=False, default='--')
    gender = db.Column(db.String(15), nullable=False, default='--')
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Password should be hashed
    profile_picture = db.Column(db.LargeBinary, nullable=True)
    mimetype = db.Column(db.Text, nullable=True)
    role_name = db.Column(db.String(20), nullable=False, default='User')

    # Relationships
    stores = db.relationship(
        'Store',
        secondary='user_store',
        backref='users',
        overlaps='user_store,user_relation'
    )
    user_store = db.relationship(
        'UserStore',
        backref='user_relation',
        lazy=True,
        overlaps='stores,users'
    )


# UserStore model (store-specific roles: Store Manager, Employee)
class UserStore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    role_name = db.Column(db.String(50), nullable=False)

    # Relationships
    user = db.relationship(
        'User',
        backref='user_store_relation',
        overlaps='stores,users,user_store'
    )
    store = db.relationship(
        'Store',
        backref='user_store_relation',
        overlaps='stores,users'
    )


class Store(db.Model):
    __tablename__ = 'store'
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(255), nullable=False)
    store_address = db.Column(db.String(255), nullable=False)
    owner_name = db.Column(db.String(255), nullable=False)
    business_email = db.Column(db.String(255), nullable=False)
    gstNumber = db.Column(db.String(255), nullable=False)
    store_type = db.Column(db.String(255), nullable=False, default='Retail')
    profit = db.Column(db.Float, nullable=False, default=0.0)
    unique_code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    # Relationships
    categories = db.relationship('Category', backref='store', lazy=True, cascade='all, delete-orphan')
    user_store = db.relationship(
        'UserStore',
        backref='store_relation',
        overlaps='users,stores'
    )


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
    low_stock = db.Column(db.Integer, nullable=True, default=5)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, index=True)
    P_unique_id = db.Column(db.String(20), unique=True, index=True, nullable=False)
    want_barcode = db.Column(db.String(20),nullable = True, default = "false")
    barcode_quantity = db.Column(db.Integer,nullable = True, default =0)
    transaction_items = db.relationship('TransactionItem', backref=db.backref('products_in_transaction', lazy=True))

class Temp_product(db.Model):
    __tablename__ = 'temp_product'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    manufacture_date = db.Column(db.Date, nullable=True)
    expire_date = db.Column(db.Date, nullable=True)
    cost_price = db.Column(db.Integer, nullable=False)
    selling_price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, index=True)
    P_unique_id = db.Column(db.String(20), index=True, nullable=False)
    delete_date = db.Column(db.DateTime, nullable=True, default=get_india_time)
    
class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=True, default=get_india_time)
    customer_name = db.Column(db.String(100), nullable=True, default="system")
    bill_number = db.Column(db.String(50), unique=True, nullable=False)  # This acts as the order/bill ID
    transaction_type = db.Column(db.String(50), nullable=True , default = "due")  # Or use Python Enum
    payment_method = db.Column(db.String(50), nullable=True, default="cash")
    total_cost_price = db.Column(db.Integer, nullable=True, default=0)  # cost_price * quantity
    total_selling_price = db.Column(db.Integer, nullable=True, default=0)
    success = db.Column(db.String(50), nullable=True, default="yes")  # yes or no
    cart = db.Column(db.JSON, nullable=True, default={})  # To store cart data as JSON
    type = db.Column(db.String(50), nullable=True)  # Additional type field
    last_updated = db.Column(db.DateTime, nullable=True, default=get_india_time, onupdate=get_india_time)

    transaction_items = db.relationship('TransactionItem', backref='transaction', lazy=True, cascade='all, delete-orphan')


class TransactionItem(db.Model):
    __tablename__ = 'transaction_item'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)  # Use 'id' instead of 'bill_number'
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=True)  # Ensure quantity > 0 in application logic
    selling_price = db.Column(db.Integer, nullable=True)
    cost_price = db.Column(db.Integer, nullable=True)
    total_price = db.Column(db.Integer, nullable=True)  # selling_price * quantity
    total_cost_price = db.Column(db.Integer, nullable=True)  # cost_price * quantity


