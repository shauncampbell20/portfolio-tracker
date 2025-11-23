const refresh = document.getElementById('refreshButton');

refresh.addEventListener('click', async(event) => {
  event.preventDefault(); // Prevent default form submission

  const refreshSpinner = document.getElementById('refreshSpinner');

  // Show spinner 
  refreshSpinner.classList.remove('d-none');
  refresh.disabled = true; // Disable button to prevent multiple clicks

  try {
    const response = await fetch('/refresh', {
      method: 'POST'
    })
    .then(response => {
        if (response.redirected){
            window.location.href = response.url;
        }
    })

    refreshSpinner.classList.add('d-none');
    refresh.disabled = false;

  } catch (error) {
    console.error('Error:', error);
    // Handle error, display messages, etc.
  }


});