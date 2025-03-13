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
    const storyForm = document.getElementById('story-form');
    if (storyForm) {
      storyForm.addEventListener('submit', function() {
        contentInput.value = quill.root.innerHTML;
      });
    }

    // If we have a "Submit for Review" form, also update content there
    const reviewForm = document.getElementById('submit-review-form');
    if (reviewForm) {
      reviewForm.addEventListener('submit', function() {
        // Create a hidden input for content if it doesn't exist
        let reviewContentInput = reviewForm.querySelector('input[name="content"]');
        if (!reviewContentInput) {
          reviewContentInput = document.createElement('input');
          reviewContentInput.type = 'hidden';
          reviewContentInput.name = 'content';
          reviewForm.appendChild(reviewContentInput);
        }
        
        // Set the value to the current Quill content
        reviewContentInput.value = quill.root.innerHTML;
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
          container.className = 'border rounded-md p-3 mb-3 flex items-center';
          
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
          
          // Add components to container
          container.appendChild(iconDiv);
          container.appendChild(infoDiv);
          
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