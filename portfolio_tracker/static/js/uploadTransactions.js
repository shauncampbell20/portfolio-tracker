const form = document.getElementById('uploadForm');

form.addEventListener('submit', async(event) => {
  event.preventDefault(); // Prevent default form submission

  const formData = new FormData(form);

  const uploadButton = document.getElementById('uploadButton');
  const uploadSpinner = document.getElementById('uploadSpinner');
  const uploadFlash = document.getElementById('upload-flash');

  // Show spinner 
  uploadSpinner.classList.remove('d-none');
  uploadButton.disabled = true; // Disable button to prevent multiple clicks

  try {
    const response = await fetch('/transactions/upload', {
      method: 'POST',
      body: formData, // FormData object is automatically handled as 'multipart/form-data'
    })
    .then(response => {
        if (response.redirected){
            window.location.href = response.url;
        } else if (!response.ok) {
            uploadFlash.classList.remove('alert-success');
            uploadFlash.classList.add('alert-danger');
            return response.json();
        } else {
            uploadFlash.classList.remove('alert-danger');
            uploadFlash.classList.add('alert-success');
            form.reset();
            return response.json();
        }
    })
    .then(data => {
        uploadFlash.classList.remove('d-none');
        uploadFlash.innerHTML = data.message;
        
    })
    uploadSpinner.classList.add('d-none');
    uploadButton.disabled = false;

  } catch (error) {
    console.error('Error:', error);
    // Handle error, display messages, etc.
  }


});