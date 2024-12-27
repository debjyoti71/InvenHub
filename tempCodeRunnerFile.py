elif request.method == 'POST':
        try:
            # Parse the incoming JSON data
            data = request.get_json()
            print("Received data:", data)

            # Extract user details
            first_name, last_name = data['name'].split()
            age = int(data['age'])  # Ensure age is stored as an integer
            gender = data['gender']
            phone_number = data['contact_number']
            store_name = data.get('store_name')  # Use .get() to avoid KeyError if not present
            owner_name = data.get("owner's_name")

            # Update user details
            user = User.query.get(data['user_id'])  # Retrieve user by ID
            if not user:
                return jsonify({"error": "User not found"}), 404

            user.first_name = first_name
            user.last_name = last_name
            user.age = age
            user.gender = gender
            user.phone = phone_number

            # Update store details if provided
            if store_name:
                user_store = UserStore.query.filter_by(user_id=user.id).first()
                store = Store.query.filter_by(id=user_store.store_id).first()
                if store:
                    store.store_name = store_name
                    store.owner_name = owner_name
                else:
                    return jsonify({"error": "Store not found"}), 404

            # Commit changes to the database
            db.session.commit()

            print("Account details updated successfully!")
            return jsonify({"message": "Account details updated successfully!"}), 200

        except ValueError as e:
            print("Error while updating account:", e)
            return jsonify({"error": "Invalid input data"}), 400
        except KeyError as e:
            print("Missing data field:", e)
            return jsonify({"error": f"Missing field: {e}"}), 400
        except Exception as e:
            print("Unexpected error:", e)
            return jsonify({"error": "An unexpected error occurred"}), 500
