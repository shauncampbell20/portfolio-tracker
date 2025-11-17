const form = document.getElementById('loginForm');

form.addEventListener('submit', async(event) => {
  event.preventDefault(); // Prevent default form submission
  const formData = new FormData(form);

  const loginButton = document.getElementById('loginButton');
  const loginSpinner = document.getElementById('loginSpinner');

  // Show spinner 
  loginSpinner.classList.remove('d-none');
  loginButton.disabled = true; // Disable button to prevent multiple clicks

  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: formData, // FormData object is automatically handled as 'multipart/form-data'
    })
    .then(response => {
        if (response.redirected){
            window.location.href = response.url
        } else if (!response.ok) {
            return response.json();
        }
    })
    .then(data => {
        console.log(data.message);
        window.location.href = data.url
    })

  } catch (error) {
    console.error('Error:', error);
    // Handle error, display messages, etc.
  }


});