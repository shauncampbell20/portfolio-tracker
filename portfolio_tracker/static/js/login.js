const form = document.getElementById('loginForm');

form.addEventListener('submit', async(event) => {
  // Function to handle login
  
  event.preventDefault(); 
  const formData = new FormData(form);

  const loginButton = document.getElementById('loginButton');
  const loginSpinner = document.getElementById('loginSpinner');

  // Show spinner 
  loginSpinner.classList.remove('d-none');
  loginButton.disabled = true; 

  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      body: formData, 
    })
    .then(response => {
        if (response.redirected){
            window.location.href = response.url
        } else if (!response.ok) {
            return response.json();
        }
    })
    .then(data => {
        window.location.href = data.url
    })

  } catch (error) {
    console.error('Error:', error);
    // Handle error, display messages, etc.
  }


});