let selectedProduct = null;
let productStock = 0;
const storeId = "{{store_id}}"; // Replace with your actual store ID
let cart = {};

document.getElementById('productName').addEventListener('input', function() {
    fetchProductSuggestions(this.value);
});

document.addEventListener('click', function(e) {
    if (!document.getElementById('productSuggestions').contains(e.target) && e.target.id !== 'productName') {
        hideSuggestions();
    }
});

function fetchProductSuggestions(query) {
    if (query.length < 2) {
        hideSuggestions();
        return;
    }

    fetch(`/suggest-products?query=${encodeURIComponent(query)}&store_id=${storeId}`)
        .then(response => response.json())
        .then(data => displayProductSuggestions(data.suggestions))
        .catch(error => {
            console.error('Error fetching product suggestions:', error);
        });
}

function displayProductSuggestions(suggestions) {
    const suggestionsList = document.getElementById('productSuggestions');
    suggestionsList.innerHTML = '';
    suggestionsList.style.display = 'block';

    if (suggestions.length > 0) {
        suggestions.forEach(product => {
            const item = document.createElement('li');
            item.className = 'suggestion-item';
            item.textContent = `${product.product_id} -${product.name} - ${product.selling_price}₹ (Stock: ${product.stock})`;
            item.onclick = () => selectProduct(product);
            suggestionsList.appendChild(item);
        });
    } else {
        const noResultsItem = document.createElement('li');
        noResultsItem.className = 'suggestion-item';
        noResultsItem.textContent = 'No products found';
        suggestionsList.appendChild(noResultsItem);
    }
}

function hideSuggestions() {
    document.getElementById('productSuggestions').style.display = 'none';
}

function selectProduct(product) {
    document.getElementById('productName').value = product.name;
    document.getElementById('productSellingPrice').value = product.selling_price.toFixed(2);
    selectedProduct = product;
    productStock = product.stock;
    
    const existingRow = document.querySelector(`tr[data-product-id="${product.product_id}"]`);
    if (existingRow) {
        const currentQuantity = cart[product.product_id] || 1;
        document.getElementById('productQuantity').value = currentQuantity;
    } else {
        document.getElementById('productQuantity').value = 1;
    }
    
    hideSuggestions();
}

function addToTable() {
    if (!selectedProduct) {
        alert('Please select a product first.');
        return;
    }

    validateQuantity();
    const quantity = parseInt(document.getElementById('productQuantity').value);
    updateTableRow(selectedProduct.product_id, selectedProduct.name, selectedProduct.selling_price, quantity);

    // Reset form
    document.getElementById('productName').value = '';
    document.getElementById('productSellingPrice').value = '';
    document.getElementById('productQuantity').value = '1';
    selectedProduct = null;
    productStock = 0;
}

function updateTableRow(productId, name, price, quantity) {
    const tableBody = document.getElementById('productTableBody');
    const existingRow = document.querySelector(`tr[data-product-id="${productId}"]`);
    const total = price * quantity;

    if (existingRow) {
        const quantityInput = existingRow.querySelector('.quantity-input');
        quantityInput.value = quantity;
        existingRow.querySelector('td:nth-child(4)').textContent = `${total.toFixed(2)}₹`;
    } else {
        const newRow = tableBody.insertRow();
        newRow.setAttribute('data-product-id', productId);
        newRow.innerHTML = `
            <td>${name}</td>
            <td>${price.toFixed(2)}₹</td>
            <td><input type="number" class="quantity-input" value="${quantity}" min="1" onchange="updateQuantity(this, '${productId}')"></td>
            <td>${total.toFixed(2)}₹</td>
        `;
    }

    // Update cart
    cart[productId] = quantity;
}

function updateQuantity(input, productId) {
    const quantity = parseInt(input.value);
    const productStock = productStocks[productId];
    if (isNaN(quantity) || quantity < 1) {
        alert('Please enter a valid quantity.');
        input.value = cart[productId];
        return;
    }
    if (!validateQuantity()) {
        input.value = cart[productId]; // Reset the quantity to the previous value if invalid
        return;
    }

    const row = input.closest('tr');
    const price = parseFloat(row.cells[1].textContent.substring(1));
    const total = price * quantity;

    row.cells[3].textContent = `${total.toFixed(2)}₹`;
    cart[productId] = quantity;
}

function fetchCartDetails() {
    const transactionId = document.getElementById('billSelect').value;
    if (!transactionId) return;

    fetch(`/get-cart-details?transaction_id=${transactionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.cart) {
                cart = data.cart;
                updateTableFromCart();
            }
        })
        .catch(error => {
            console.error('Error fetching cart details:', error);
        });
}

function updateTableFromCart() {
    const tableBody = document.getElementById('productTableBody');
    tableBody.innerHTML = '';

    for (const [productId, quantity] of Object.entries(cart)) {
        fetch(`/get-product-details?product_id=${productId}`)
            .then(response => response.json())
            .then(product => {
                updateTableRow(productId, product.name, product.selling_price, quantity);
                productStocks[productId] = product.stock;
            })
            .catch(error => {
                console.error('Error fetching product details:', error);
            });
    }
}

function completeSale() {
    if (Object.keys(cart).length === 0) {
        alert('Your cart is empty. Please add some products before completing the sale.');
        return;
    }

    const billNumber = document.getElementById('billSelect').value;
    if (!billNumber) {
        alert('Please select a bill number before completing the sale.');
        return;
    }
    
    const customer_name = document.getElementById('customer_name').value;

    fetch('/new_sale', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            store_id: storeId,
            bill_number: billNumber,
            cart: cart,
            customer_name: customer_name
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success || data.message === "Cart updated successfully") {
            // alert('Sale completed successfully!');
            // Clear the table and cart
            document.getElementById('productTableBody').innerHTML = '';
            cart = {};
            // Reset bill selection
            document.getElementById('billSelect').value = '';
            // Redirect to checkout page
            window.location.href = '/checkout';
        } else {
            alert('Error completing sale: ' + data.message);
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        alert('An error occurred while completing the sale. Please try again.');
    });
}

function validateQuantity() {
    const quantity = parseInt(document.getElementById('productQuantity').value);

    if (quantity > productStock) {
        alert(`You cannot order more than ${productStock} items. Please adjust the quantity.`);
        document.getElementById('productQuantity').value = productStock;
    }
}
document.getElementById('animatedButton').addEventListener('click', function() {
    this.classList.toggle('active');
  });