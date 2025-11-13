document.addEventListener('DOMContentLoaded', function() {
// Function to get positions table with fetch and render HTML
fetch(window.summaryUrl)
    .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text(); 
        })
    .then(data => {
        const parsedData = JSON.parse(data);
        const currentElement = document.getElementById('current-value');
        if (currentElement) {
            currentElement.innerText = parsedData.curr_value_str; 
        }
        const dailyElement = document.getElementById('daily-change')
        if (dailyElement) {
            dailyElement.innerText = parsedData.daily_str;
            dailyElement.className = parsedData.dgl_col;
        }
        const totalElement = document.getElementById('total-change')
        if (totalElement) {
            totalElement.innerText = parsedData.tot_str;
            totalElement.className = parsedData.tot_col;
        }
    })
    .catch(error => {
        console.error('Error fetching HTML:', error);
    });
});