/**
 * Main JavaScript for Newskoop
 */

document.addEventListener('DOMContentLoaded', function() {
  // Mobile menu toggle
  const mobileMenuButton = document.getElementById('mobile-menu-button');
  const mobileOverlay = document.getElementById('mobile-overlay');
  const sidebar = document.getElementById('sidebar');

  if (mobileMenuButton && mobileOverlay && sidebar) {
    mobileMenuButton.addEventListener('click', function() {
      sidebar.classList.toggle('-left-full');
      sidebar.classList.toggle('left-0');
      mobileOverlay.classList.toggle('hidden');
    });

    mobileOverlay.addEventListener('click', function() {
      sidebar.classList.add('-left-full');
      sidebar.classList.remove('left-0');
      mobileOverlay.classList.add('hidden');
    });
  }

  // User dropdown toggle
  const userMenuButton = document.getElementById('user-menu-button');
  const userDropdownMenu = document.getElementById('user-dropdown-menu');

  if (userMenuButton && userDropdownMenu) {
    userMenuButton.addEventListener('click', function() {
      userDropdownMenu.classList.toggle('hidden');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
      if (!userMenuButton.contains(event.target) && !userDropdownMenu.contains(event.target)) {
        userDropdownMenu.classList.add('hidden');
      }
    });
  }

  // Alert dismissal
  const alertCloseButtons = document.querySelectorAll('.alert-close');
  
  alertCloseButtons.forEach(function(button) {
    button.addEventListener('click', function() {
      const alert = button.closest('.alert');
      if (alert) {
        alert.remove();
      }
    });
  });

  // Toggle password visibility
  const passwordToggleButtons = document.querySelectorAll('.password-toggle');
  
  passwordToggleButtons.forEach(function(button) {
    button.addEventListener('click', function() {
      const input = document.getElementById(button.dataset.target);
      if (input) {
        if (input.type === 'password') {
          input.type = 'text';
          button.querySelector('.eye-open').classList.add('hidden');
          button.querySelector('.eye-closed').classList.remove('hidden');
        } else {
          input.type = 'password';
          button.querySelector('.eye-open').classList.remove('hidden');
          button.querySelector('.eye-closed').classList.add('hidden');
        }
      }
    });
  });
  
  // Initialize toggle switches
  initToggleSwitches();

  // Initialize Quill Editor for story create/edit
  initStoryEditor();

  // Initialize audio file upload preview
  initAudioUpload();
});

/**
 * Initialize toggle switches that use the modern design
 */
function initToggleSwitches() {
  // Get all toggle switches
  const toggleSwitches = document.querySelectorAll('[role="switch"]');
  
  // Add click event listeners to each toggle
  toggleSwitches.forEach(function(toggle) {
    toggle.addEventListener('click', function() {
      // Get the associated checkbox ID from the data attribute
      const checkboxId = toggle.getAttribute('data-checkbox-id');
      
      if (checkboxId) {
        const checkbox = document.getElementById(checkboxId);
        if (checkbox) {
          checkbox.checked = !checkbox.checked;
          updateToggleAppearance(toggle, checkbox.checked);
        }
      }
    });
  });
}

/**
 * Update toggle switch appearance based on checked state
 */
function updateToggleAppearance(toggle, isChecked) {
  if (isChecked) {
    toggle.classList.remove('bg-gray-200');
    toggle.classList.add('bg-primary');
    toggle.setAttribute('aria-checked', 'true');
    toggle.querySelector('span:not(.sr-only)').classList.remove('translate-x-0');
    toggle.querySelector('span:not(.sr-only)').classList.add('translate-x-5');
  } else {
    toggle.classList.remove('bg-primary');
    toggle.classList.add('bg-gray-200');
    toggle.setAttribute('aria-checked', 'false');
    toggle.querySelector('span:not(.sr-only)').classList.remove('translate-x-5');
    toggle.querySelector('span:not(.sr-only)').classList.add('translate-x-0');
  }
}

/**
 * Initialize Quill editor for story content
 */
function initStoryEditor() {
  const editorContainer = document.getElementById('content-editor');
  const contentInput = document.getElementById('id_content');
  const storyForm = document.getElementById('story-form');
  
  if (editorContainer && contentInput) {
    // Configure Quill toolbar options
    const toolbarOptions = [
      ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
      ['blockquote', 'code-block'],
      [{ 'header': 1 }, { 'header': 2 }],               // custom button values
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      [{ 'script': 'sub'}, { 'script': 'super' }],      // superscript/subscript
      [{ 'indent': '-1'}, { 'indent': '+1' }],          // outdent/indent
      [{ 'direction': 'rtl' }],                         // text direction
      [{ 'size': ['small', false, 'large', 'huge'] }],  // custom dropdown
      [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
      [{ 'color': [] }, { 'background': [] }],          // dropdown with defaults
      [{ 'font': [] }],
      [{ 'align': [] }],
      ['clean'],                                         // remove formatting button
      ['link', 'image']                                  // link and image
    ];

    // Initialize Quill
    const quill = new Quill('#content-editor', {
      modules: {
        toolbar: toolbarOptions
      },
      theme: 'snow'
    });

    // Load existing content if any
    if (contentInput.value) {
      quill.root.innerHTML = contentInput.value;
    }

    // When form is submitted, update the hidden input with Quill content
    if (storyForm) {
      storyForm.addEventListener('submit', function(e) {
        // For story-create page, enhance submission process
        if (window.location.pathname.includes('/stories/create/')) {
          e.preventDefault();
          
          // Update the hidden input with Quill content
          contentInput.value = quill.root.innerHTML;
          
          // Create FormData object
          const formData = new FormData(storyForm);
          
          // Handle audio files properly
          const audioInput = document.getElementById('audio_files');
          if (audioInput && audioInput.files && audioInput.files.length > 0) {
            // First, remove the standard audio_files field to prevent duplication
            formData.delete('audio_files');
            
            // Add each file with our custom naming pattern
            for (let i = 0; i < audioInput.files.length; i++) {
              formData.append(`audio_file_${i}`, audioInput.files[i]);
            }
          }          
     
          // Submit the form using fetch API
          fetch(storyForm.action, {
            method: 'POST',
            body: formData,
            headers: {
              'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
          })
          .then(response => {
            if (response.redirected) {
              // If redirected, go to the new URL (story detail page)
              window.location.href = response.url;
            } else {
              // Parse the response to check for errors
              return response.text();
            }
          })
          .then(html => {
            if (html) {
              // If we got HTML back, there might be form errors
              // Replace the current form with the new one containing error messages
              const tempDiv = document.createElement('div');
              tempDiv.innerHTML = html;
              const newForm = tempDiv.querySelector('#story-form');
              if (newForm) {
                storyForm.innerHTML = newForm.innerHTML;
                // Reinitialize Quill
                initStoryEditor();
              } else {
                console.error('Form submission error occurred');
              }
            }
          })
          .catch(error => {
            console.error('Error submitting form:', error);
          });
        } else {
          // For other pages, just update the hidden input
          contentInput.value = quill.root.innerHTML;
        }
      });
    }

    // Specifically handle the "Submit for Review" button click
    const submitReviewBtn = document.querySelector('button[form="submit-review-form"]');
    const submitReviewForm = document.getElementById('submit-review-form');

    if (submitReviewBtn && submitReviewForm && quill) {
      submitReviewBtn.addEventListener('click', function(e) {
        // Prevent the default form submission
        e.preventDefault();
        
        // Update the content input in the submit-review-form with the current Quill content
        const contentInput = submitReviewForm.querySelector('input[name="content"]');
        if (contentInput) {
          contentInput.value = quill.root.innerHTML;
        } else {
          // If the content input doesn't exist, create it
          const newContentInput = document.createElement('input');
          newContentInput.type = 'hidden';
          newContentInput.name = 'content';
          newContentInput.value = quill.root.innerHTML;
          submitReviewForm.appendChild(newContentInput);
        }
        
        // Make sure the title is also transferred
        const titleInput = submitReviewForm.querySelector('input[name="title"]');
        const mainTitleInput = document.querySelector('#story-form input[name="title"]');
        if (titleInput && mainTitleInput) {
          titleInput.value = mainTitleInput.value;
        }
        
        // Also transfer any other important fields
        const fieldsToTransfer = ['category', 'religion_classification', 'language'];
        fieldsToTransfer.forEach(field => {
          const mainInput = document.querySelector(`#story-form [name="${field}"]`);
          const reviewInput = submitReviewForm.querySelector(`input[name="${field}"]`);
          
          if (mainInput && reviewInput && mainInput.value) {
            reviewInput.value = mainInput.value;
          }
        });
        
        // Now submit the form
        submitReviewForm.submit();
      });
    }
  }
}

/**
 * Initialize audio file upload preview
 */
function initAudioUpload() {
  const audioInput = document.getElementById('audio_files');
  const audioPreview = document.getElementById('audio-preview');
  const addAudioBtn = document.getElementById('add-audio-btn');
  
  if (audioInput && audioPreview && addAudioBtn) {
    // Click the hidden file input when the button is clicked
    addAudioBtn.addEventListener('click', function() {
      audioInput.click();
    });
    
    // Handle file selection
    audioInput.addEventListener('change', function() {
      // Clear previous previews
      audioPreview.innerHTML = '';
      
      if (this.files && this.files.length > 0) {
        for (let i = 0; i < this.files.length; i++) {
          const file = this.files[i];
          
          // Create a preview container
          const container = document.createElement('div');
          container.className = 'border rounded-md p-3 mb-3 flex items-center justify-between';
          
          // Left side with icon and info
          const leftDiv = document.createElement('div');
          leftDiv.className = 'flex items-center';
          
          // Icon
          const iconDiv = document.createElement('div');
          iconDiv.className = 'flex-shrink-0 mr-3';
          iconDiv.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" /></svg>';
          
          // File info
          const infoDiv = document.createElement('div');
          infoDiv.className = 'flex-1';
          
          const fileName = document.createElement('div');
          fileName.className = 'font-medium';
          fileName.textContent = file.name;
          
          const fileSize = document.createElement('div');
          fileSize.className = 'text-xs text-gray-500';
          fileSize.textContent = formatFileSize(file.size);
          
          infoDiv.appendChild(fileName);
          infoDiv.appendChild(fileSize);
          
          leftDiv.appendChild(iconDiv);
          leftDiv.appendChild(infoDiv);
          
          // Right side with remove button
          const removeBtn = document.createElement('button');
          removeBtn.type = 'button';
          removeBtn.className = 'text-danger hover:text-danger-dark focus:outline-none';
          removeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>';
          
          // Add click event to remove this file
          removeBtn.addEventListener('click', function() {
            // Remove this file from the input
            // We need to create a new FileList since it's read-only
            const dt = new DataTransfer();
            const files = audioInput.files;
            
            for (let j = 0; j < files.length; j++) {
              // Skip the file we want to remove
              if (j !== i) {
                dt.items.add(files[j]);
              }
            }
            
            // Set the new FileList to the input
            audioInput.files = dt.files;
            
            // Remove the container from the preview
            container.remove();
            
            // If all files are removed, clear the preview
            if (audioInput.files.length === 0) {
              audioPreview.innerHTML = '';
            }
          });
          
          // Add components to container
          container.appendChild(leftDiv);
          container.appendChild(removeBtn);
          
          // Add container to preview area
          audioPreview.appendChild(container);
        }
      }
    });
  }
}

/**
 * Format file size in human-readable format
 */
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}