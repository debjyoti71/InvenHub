from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid  # To generate unique store codes

# Initialize the SQLAlchemy instance
db = SQLAlchemy()

# Association table to link Users and Stores with an additional role field
user_store = db.Table('user_store',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('store_id', db.Integer, db.ForeignKey('store.id'), primary_key=True),
    db.Column('role', db.String(20), nullable=False,default='Owner')  # Role can be 'Owner' or 'Employee'
)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    stores = db.relationship('Store', secondary=user_store, backref=db.backref('users', lazy=True))  # Many-to-many relationship with Store

# Store model
class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(50), nullable=False)
    store_address = db.Column(db.String(100), nullable=False)
    owner_name = db.Column(db.String(50), nullable=False)
    business_email = db.Column(db.String(50), nullable=False)
    gstNumber = db.Column(db.Integer, nullable=False)
    store_type = db.Column(db.String(100), nullable=False, default='Retail')
    profit = db.Column(db.Integer, nullable=False, default=0)
    unique_code = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))  # Unique store code
    categories = db.relationship('Category', backref='store', lazy=True, cascade='all, delete-orphan')  # Cascade delete

# Category model
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)  # Foreign key to link Category to a Store
    products = db.relationship('Product', backref='category', lazy=True, cascade='all, delete-orphan')  # Cascade delete

# Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(50), nullable=False)
    manufacture_date = db.Column(db.Date, nullable=True)  # Optional Manufacture Date
    expire_date = db.Column(db.Date, nullable=True)  # Optional Expire Date
    cost_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)  # Foreign key to link Product to a Category
    temperature = db.Column(db.Float, nullable=True)  # Optional Temperature
    sale_date = db.Column(db.Date, nullable=True, default=datetime.utcnow)  # Optional Sale Date
    month_year = db.Column(db.String(10), nullable=True)  # Optional Month and Year
    monthly_sale = db.Column(db.Integer, nullable=True)  # Optional Monthly Sale
    product_profit = db.Column(db.Float, nullable=True)  # Optional Profit

    def calculate_profit(self):
        # Method to calculate profit based on cost and selling prices
        if self.selling_price and self.cost_price:
            self.profit = (self.selling_price - self.cost_price) * self.stock
        else:
            self.profit = 0
