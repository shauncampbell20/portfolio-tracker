document.getElementById('formFile').addEventListener('change', function(event) {
    // Function to parse uploaded file

    const file = event.target.files[0]; 

    if (file) {
        const reader = new FileReader();

        reader.onload = function(e) {
            const fileContent = e.target.result; 
            const tranDropdown = document.getElementById('tran_date_select');
            const symbolDropdown = document.getElementById('symbol_select');
            const quantityDropdown = document.getElementById('quantity_select');
            const priceDropdown = document.getElementById('price_select');
            const typeDropdown = document.getElementById('type_select');
            
            // Base options
            const baseOption1 = document.createElement('option');
            const baseOption2 = document.createElement('option');
            const baseOption3 = document.createElement('option');
            const baseOption4 = document.createElement('option');
            const baseOption5 = document.createElement('option');
            baseOption1.value = 'Select column'; 
            baseOption1.textContent = 'Select column'; 
            baseOption2.value = 'Select column'; 
            baseOption2.textContent = 'Select column'; 
            baseOption3.value = 'Select column'; 
            baseOption3.textContent = 'Select column'; 
            baseOption4.value = 'Select column'; 
            baseOption4.textContent = 'Select column'; 
            baseOption5.value = 'Select column'; 
            baseOption5.textContent = 'Select column'; 
            tranDropdown.innerHTML = ''; 
            symbolDropdown.innerHTML = ''; 
            quantityDropdown.innerHTML = ''; 
            priceDropdown.innerHTML = ''; 
            typeDropdown.innerHTML = ''; 
            tranDropdown.appendChild(baseOption1);
            symbolDropdown.appendChild(baseOption2);
            quantityDropdown.appendChild(baseOption3);
            priceDropdown.appendChild(baseOption4);
            typeDropdown.appendChild(baseOption5);
            
            let headers = fileContent.split(/\r?\n|\r/)[0]; 
            let items = headers.replace(/['"]/g, '').split(',');
            
            // Add column names to dropdowns
            items.forEach(itemText => {
                const option1 = document.createElement('option');
                const option2 = document.createElement('option');
                const option3 = document.createElement('option');
                const option4 = document.createElement('option');
                const option5 = document.createElement('option');
                option1.value = itemText.trim(); 
                option1.textContent = itemText.trim();
                option2.value = itemText.trim(); 
                option2.textContent = itemText.trim(); 
                option3.value = itemText.trim(); 
                option3.textContent = itemText.trim();
                option4.value = itemText.trim(); 
                option4.textContent = itemText.trim(); 
                option5.value = itemText.trim(); 
                option5.textContent = itemText.trim(); 
                tranDropdown.appendChild(option1);
                symbolDropdown.appendChild(option2);
                quantityDropdown.appendChild(option3);
                priceDropdown.appendChild(option4);
                typeDropdown.appendChild(option5);
            });
        };
        reader.readAsText(file);
    }
});