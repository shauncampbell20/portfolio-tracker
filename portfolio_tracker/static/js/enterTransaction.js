const form = document.getElementById('enterForm');
const currentUrl = window.location.href;
mode = "enter";

if (currentUrl.includes('edit')) {
    mode = "edit";
}

form.addEventListener('submit', async(event) => {
  // Handle submitting and editing transactions
  
  event.preventDefault(); 

  const formData = new FormData(form);

  const enterButton = document.getElementById('enterButton');
  const enterSpinner = document.getElementById('enterSpinner');
  const enterFlash = document.getElementById('enter-flash');
  const editFlash = document.getElementById('edit-flash');

  // Show spinner 
  enterSpinner.classList.remove('d-none');
  enterButton.disabled = true; 

  try {
    if (mode == "enter") {
        Url = '/transactions/enter';
    } else {
        Url = currentUrl
    }
    const response = await fetch(Url, {
      method: 'POST',
      body: formData, 
    })
    .then(response => {
        if (response.redirected){
            window.location.href = response.url;
            editFlash.classList.remove('d-none');
            editFlash.classList.add('alert-success');
            editFlash.innerHTML = 'Transaction Saved.';

        } else if (!response.ok) {
            enterFlash.classList.remove('alert-success');
            enterFlash.classList.add('alert-danger');
            return response.json();
        } else {
            enterFlash.classList.remove('alert-danger');
            enterFlash.classList.add('alert-success');
            form.reset();
            return response.json();
        }
    })
    .then(data => {
        enterFlash.classList.remove('d-none')
        enterFlash.innerHTML = data.message;
    })
    enterSpinner.classList.add('d-none');
    enterButton.disabled = false;

  } catch (error) {
    console.error('Error:', error);
  }


});