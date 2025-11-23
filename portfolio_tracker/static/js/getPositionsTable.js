function getPositionsTable() {
// Function to get positions table with fetch and render HTML
    setTimeout(() => {
        Url = window.tableUrl+'?excluded='+window.excluded.join(',');
        console.log(Url);
        fetch(Url)
        .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.text(); 
            })
        .then(htmlContent => {
            const targetElement = document.getElementById('positions-table');
            if (targetElement) {
                targetElement.innerHTML = htmlContent; 
            }
        })
        .catch(error => {
            console.error('Error fetching HTML:', error);
        });
    }, 10);

};
// document.addEventListener('DOMContentLoaded', getPositionsTable);

