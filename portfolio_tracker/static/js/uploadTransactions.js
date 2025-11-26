const form = document.getElementById('uploadForm');

form.addEventListener('submit', async(event) => {
  // Function to handle file upload
  
  event.preventDefault(); 

  const formData = new FormData(form);

  const uploadButton = document.getElementById('uploadButton');
  const uploadSpinner = document.getElementById('uploadSpinner');
  const uploadFlash = document.getElementById('upload-flash');

  // Show spinner 
  uploadSpinner.classList.remove('d-none');
  uploadButton.disabled = true; 

  try {
    const response = await fetch('/transactions/upload', {
      method: 'POST',
      body: formData, 
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
  }
});