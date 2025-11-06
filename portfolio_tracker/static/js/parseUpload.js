document.getElementById('formFile').addEventListener('change', function(event) {
    const file = event.target.files[0]; // Get the selected file

    if (file) {
        const reader = new FileReader();

        reader.onload = function(e) {
            const fileContent = e.target.result; // Get the file content as a string
            const tranDropdown = document.getElementById('tran_date_select');
            const symbolDropdown = document.getElementById('symbol_select');
            const quantityDropdown = document.getElementById('quantity_select');
            const priceDropdown = document.getElementById('price_select');
            
            const baseOption1 = document.createElement('option');
            const baseOption2 = document.createElement('option');
            const baseOption3 = document.createElement('option');
            const baseOption4 = document.createElement('option');
            baseOption1.value = 'Select column'; // Set value
            baseOption1.textContent = 'Select column'; // Set display text
            baseOption2.value = 'Select column'; // Set value
            baseOption2.textContent = 'Select column'; // Set display text
            baseOption3.value = 'Select column'; // Set value
            baseOption3.textContent = 'Select column'; // Set display text
            baseOption4.value = 'Select column'; // Set value
            baseOption4.textContent = 'Select column'; // Set display text
                 
            
            // Clear existing options (optional, if you want to replace them)
            tranDropdown.innerHTML = ''; 
            symbolDropdown.innerHTML = ''; 
            quantityDropdown.innerHTML = ''; 
            priceDropdown.innerHTML = ''; 
            tranDropdown.appendChild(baseOption1);
            symbolDropdown.appendChild(baseOption2);
            quantityDropdown.appendChild(baseOption3);
            priceDropdown.appendChild(baseOption4);
            
            // Assuming the file content is a comma-separated list of values
            let headers = fileContent.split(/\r?\n|\r/)[0]; 
            let items = headers.replace(/['"]/g, '').split(',');
            console.log(items)


            items.forEach(itemText => {
                const option1 = document.createElement('option');
                const option2 = document.createElement('option');
                const option3 = document.createElement('option');
                const option4 = document.createElement('option');
                option1.value = itemText.trim(); // Set value
                option1.textContent = itemText.trim(); // Set display text
                option2.value = itemText.trim(); // Set value
                option2.textContent = itemText.trim(); // Set display text
                option3.value = itemText.trim(); // Set value
                option3.textContent = itemText.trim(); // Set display text
                option4.value = itemText.trim(); // Set value
                option4.textContent = itemText.trim(); // Set display text
                tranDropdown.appendChild(option1);
                symbolDropdown.appendChild(option2);
                quantityDropdown.appendChild(option3);
                priceDropdown.appendChild(option4);
            });
        };

        reader.readAsText(file); // Read the file as text
    }
});