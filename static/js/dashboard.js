var mini = true;

function toggleSidebar(open) {
  if (open) {
    document.getElementById("mySidebar").style.width = "250px"; // Expanded width
    document.getElementById("main").style.marginLeft = "250px"; // Adjust main content margin
    mini = false;
  } else {
    document.getElementById("mySidebar").style.width = "85px"; // Collapsed width
    document.getElementById("main").style.marginLeft = "85px"; // Adjust main content margin
    mini = true;
  }
}
function updateTime() {
  const clockElement = document.getElementById('clock');
  const now = new Date();
  clockElement.textContent = now.toLocaleString();
}

// Update time every second
setInterval(updateTime, 1000);

// Initialize time immediately
updateTime();




function fetchSuggestions(query) {
  const storeId = document.getElementById('storeInput').value; // Fetch store ID dynamically

  if (query.length < 2) {
      hideSuggestions(); // Hide suggestions if query length is less than 2
      return;
  }

  // Fetch suggestions from the server
  fetch(`/suggest?query=${query}&store_id=${storeId}`)
      .then(response => response.json())
      .then(data => displaySuggestions(data.categories, data.products))
      .catch(error => console.error('Error fetching suggestions:', error));
}

// Display suggestions for categories and products
function displaySuggestions(categories, products) {
  const suggestionsList = document.getElementById('productSuggestions');
  suggestionsList.innerHTML = ''; // Clear previous suggestions
  suggestionsList.style.display = 'block'; // Show suggestions list

  // Display matching categories first
  if (categories.length > 0) {
      categories.forEach(category => {
          const categoryItem = document.createElement('li');
          categoryItem.className = 'list-group-item suggestion-item category-item';
          categoryItem.textContent = category.name; // Display category name
          categoryItem.onclick = () => redirectToCategory(category.category_id); // Redirect on click
          suggestionsList.appendChild(categoryItem);
      });
  }

  // Display matching products after categories
  if (products.length > 0) {
      products.forEach(product => {
          const productItem = document.createElement('li');
          productItem.className = 'list-group-item suggestion-item product-item';
          productItem.textContent = `${product.product_id} - ${product.category_name}-${product.name} - ${product.selling_price} (Stock: ${product.stock})`;
          productItem.onclick = () => redirectToProduct(product.category_id, product.product_id); // Redirect on click
          suggestionsList.appendChild(productItem);
      });
  }

  // If no results are found
  if (categories.length === 0 && products.length === 0) {
      const noResultsItem = document.createElement('li');
      noResultsItem.className = 'list-group-item';
      noResultsItem.textContent = 'No results found';
      suggestionsList.appendChild(noResultsItem);
  }
}

// Hide the suggestions list
function hideSuggestions() {
  const suggestionsList = document.getElementById('productSuggestions');
  suggestionsList.style.display = 'none';
}

// Redirect to category reports
function redirectToCategory(categoryId) {
  window.location.href = `/reports/category?category_id=${categoryId}`;
}

// Redirect to product reports
function redirectToProduct(categoryId, productId) {
  window.location.href = `/reports/category/product?category_id=${categoryId}&product_id=${productId}`;
}

// Listen for input events on the search input field
document.getElementById('searchInput').addEventListener('input', function () {
  const query = this.value.trim(); // Get the query from the input field
  fetchSuggestions(query); // Fetch suggestions based on the query
});