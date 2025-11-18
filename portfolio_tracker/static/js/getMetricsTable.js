document.addEventListener('DOMContentLoaded', function() {
// Function to get positions table with fetch and render HTML
fetch(window.metricsUrl)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text(); 
        })
    .then(htmlContent => {
        const targetElement = document.getElementById('metrics-table');
        if (targetElement) {
            targetElement.innerHTML = htmlContent; 
        }
    })
    .catch(error => {
        console.error('Error fetching HTML:', error);
    });
});