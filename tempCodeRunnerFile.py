# Extract unique products with cost and selling prices
# products = {}
# for product in df['product'].unique():
#     product_name = product
#     productPrice = df.loc[df['product'] == product, 'Cost_price'].iloc[0]
#     productSellingPrice = df.loc[df['product'] == product, 'sell_price'].iloc[0]
#     products[product_name] = {'Cost_price': productPrice, 'sell_price': productSellingPrice}

#     products_in_category = Product.query.filter_by(category_id=category.id).all()
#     P_unique_id = f"{category.C_unique_id}{len(products_in_category) + 1}"
#     product = Product(
#     name=product_name,
#     cost_price=float(productPrice),
#     stock=0,
#     selling_price=float(productSellingPrice),
#     category_id=category.id,
#     P_unique_id=P_unique_id
#     )
#     db.session.add(product)
# db.session.commit()    