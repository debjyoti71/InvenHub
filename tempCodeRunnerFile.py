@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['email']
    user = User.query.filter_by(email=email).first()

    if user.role_name.lower() != 'user':
        user = User.query.get(user_id)
        if not user:
            flash("User not found.")
            return redirect(url_for('view_users'))

        try:
            # Step 1: Check the role of the user in each store before deleting
            for store in user.stores:
                # Query the user-store association to check the role of the user for this store
                association = db.session.query(UserStore).filter_by(user_id=user.id, store_id=store.id).first()
                
                if association and association.role == 'Owner':
                    # Remove the user from the store's user list
                    store.users.remove(user)

                    # Step 2: Delete related categories and products for stores owned by the user
                    for category in store.categories:
                        # Delete related products
                        for product in category.products:
                            db.session.delete(product)
                        # Then delete the category itself
                        db.session.delete(category)

                    # Delete the store only if the user is the owner
                    db.session.delete(store)

            # Step 3: Finally, delete the user
            db.session.delete(user)
            db.session.commit()
            flash("User and associated data deleted successfully.")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while deleting the user: {e}")

        return redirect(url_for('view_users'))
    else:
        return "You are not authorized to perform this action.", 403
