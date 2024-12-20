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
