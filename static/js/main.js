/**
 * Newskoop - Main JavaScript
 * Modern UI interactions for Newskoop project
 */

document.addEventListener('DOMContentLoaded', function() {
  initDropdowns();
  initMobileSidebar();
  initAlertDismissals();
  initFormValidation();
  initDataTables();
  initConfirmDialogs();
  initStoryEditor(); // Add this line to initialize story editor
  initAudioUpload(); // Add this line to initialize audio uploads
});

/**
 * Initialize dropdown menus
 */
function initDropdowns() {
  // Generic dropdown toggle
  document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
    toggle.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      // Close all other dropdowns
      document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
        if (!toggle.parentNode.contains(menu)) {
          menu.classList.remove('show');
        }
      });
      
      // Toggle this dropdown
      this.nextElementSibling.classList.toggle('show');
      this.setAttribute('aria-expanded', this.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
    });
  });
  
  // Close dropdowns when clicking outside
  document.addEventListener('click', function(e) {
    document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
      const toggle = menu.previousElementSibling;
      if (!menu.contains(e.target) && !toggle.contains(e.target)) {
        menu.classList.remove('show');
        if (toggle.hasAttribute('aria-expanded')) {
          toggle.setAttribute('aria-expanded', 'false');
        }
      }
    });
  });
  
  // User dropdown specific handling
  const userMenuButton = document.getElementById('user-menu-button');
  const userDropdownMenu = document.getElementById('user-dropdown-menu');
  
  if (userMenuButton && userDropdownMenu) {
    userMenuButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      userDropdownMenu.classList.toggle('show');
      this.setAttribute('aria-expanded', this.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
    });
  }
}

/**
 * Initialize mobile sidebar
 */
function initMobileSidebar() {
  const mobileMenuButton = document.getElementById('mobile-menu-button');
  const sidebar = document.getElementById('sidebar');
  const mobileOverlay = document.getElementById('mobile-overlay');
  
  if (mobileMenuButton && sidebar && mobileOverlay) {
    mobileMenuButton.addEventListener('click', function() {
      sidebar.classList.toggle('show');
      mobileOverlay.classList.toggle('show');
      document.body.classList.toggle('sidebar-open');
    });
    
    mobileOverlay.addEventListener('click', function() {
      sidebar.classList.remove('show');
      mobileOverlay.classList.remove('show');
      document.body.classList.remove('sidebar-open');
    });
  }
}

/**
 * Initialize alert dismissals
 */
function initAlertDismissals() {
  document.querySelectorAll('.alert-dismissible .alert-close').forEach(button => {
    button.addEventListener('click', function() {
      const alert = this.closest('.alert');
      alert.style.opacity = '0';
      setTimeout(() => {
        alert.remove();
      }, 300);
    });
  });
  
  // Auto-dismiss success alerts after 5 seconds
  document.querySelectorAll('.alert-success').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      setTimeout(() => {
        alert.remove();
      }, 300);
    }, 5000);
  });
}

/**
 * Initialize client-side form validation
 */
function initFormValidation() {
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
        
        // Highlight the first invalid field
        const invalidField = form.querySelector(':invalid');
        if (invalidField) {
          invalidField.focus();
        }
      }
      
      form.classList.add('was-validated');
    });
  });
}

/**
 * Initialize data tables with search, sort, and pagination
 */
function initDataTables() {
  const tables = document.querySelectorAll('.data-table');
  if (tables.length === 0) return;
  
  tables.forEach(table => {
    // Add search functionality
    const searchInput = document.querySelector(`#${table.id}-search`);
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        const searchText = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(searchText) ? '' : 'none';
        });
      });
    }
    
    // Simple client-side sorting
    const headers = table.querySelectorAll('th[data-sort]');
    headers.forEach(header => {
      header.addEventListener('click', function() {
        const column = this.dataset.sort;
        const direction = this.classList.contains('asc') ? 'desc' : 'asc';
        
        // Remove sort classes from all headers
        headers.forEach(h => {
          h.classList.remove('asc', 'desc');
        });
        
        // Add sort class to this header
        this.classList.add(direction);
        
        // Sort the rows
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        rows.sort((a, b) => {
          const aValue = a.querySelector(`td[data-${column}]`).dataset[column];
          const bValue = b.querySelector(`td[data-${column}]`).dataset[column];
          
          if (direction === 'asc') {
            return aValue.localeCompare(bValue);
          } else {
            return bValue.localeCompare(aValue);
          }
        });
        
        // Reorder the rows
        const tbody = table.querySelector('tbody');
        rows.forEach(row => {
          tbody.appendChild(row);
        });
      });
    });
  });
}

/**
 * Initialize confirmation dialogs for destructive actions
 */
function initConfirmDialogs() {
  document.querySelectorAll('[data-confirm]').forEach(element => {
    element.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });
  
  // Handle delete confirmation inputs
  document.querySelectorAll('form[data-confirm-field]').forEach(form => {
    form.addEventListener('submit', function(e) {
      const confirmField = this.querySelector(`[name="${this.dataset.confirmField}"]`);
      const confirmValue = this.dataset.confirmValue;
      
      if (confirmField && confirmField.value !== confirmValue) {
        e.preventDefault();
        alert(`Please type "${confirmValue}" to confirm this action.`);
      }
    });
  });
}

/**
 * Utility function to format date strings
 * @param {string} dateString - The date string to format
 * @param {string} format - The format to use (default: 'medium')
 * @returns {string} - The formatted date string
 */
function formatDate(dateString, format = 'medium') {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  
  switch (format) {
    case 'short':
      return date.toLocaleDateString();
    case 'long':
      return date.toLocaleDateString(undefined, { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    case 'medium':
    default:
      return date.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
  }
}

/**
 * Utility function to format numbers
 * @param {number} number - The number to format
 * @param {string} format - The format to use (default: 'decimal')
 * @returns {string} - The formatted number
 */
function formatNumber(number, format = 'decimal') {
  if (number === null || number === undefined) return '';
  
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat(undefined, { 
        style: 'currency', 
        currency: 'USD' 
      }).format(number);
    case 'percent':
      return new Intl.NumberFormat(undefined, { 
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 2
      }).format(number / 100);
    case 'decimal':
    default:
      return new Intl.NumberFormat().format(number);
  }
}

/**
 * Initialize Quill editor for story content
 */
function initStoryEditor() {
  // Check if we're on a page with a content editor
  const editorContainer = document.getElementById('content-editor');
  const contentInput = document.getElementById('id_content');
  
  if (!editorContainer || !contentInput) return;
  
  // Load Quill if it's not already loaded
  if (typeof Quill === 'undefined') {
    console.log('Quill is not loaded. Loading Quill from CDN...');
    
    // Add Quill CSS to the head
    const quillCSS = document.createElement('link');
    quillCSS.rel = 'stylesheet';
    quillCSS.href = 'https://cdn.quilljs.com/1.3.6/quill.snow.css';
    document.head.appendChild(quillCSS);
    
    // Add Quill JS script
    const quillScript = document.createElement('script');
    quillScript.src = 'https://cdn.quilljs.com/1.3.6/quill.min.js';
    quillScript.onload = initQuillEditor;
    document.head.appendChild(quillScript);
  } else {
    // Quill is already loaded, initialize the editor
    initQuillEditor();
  }
  
  function initQuillEditor() {
    // Set up Quill with toolbar options
    const quill = new Quill(editorContainer, {
      theme: 'snow',
      modules: {
        toolbar: [
          [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
          ['bold', 'italic', 'underline', 'strike'],
          [{ 'list': 'ordered'}, { 'list': 'bullet' }],
          [{ 'indent': '-1'}, { 'indent': '+1' }],
          ['link', 'image'],
          ['clean']
        ]
      },
      placeholder: 'Write your story content here...',
    });
    
    // Populate editor with existing content if available
    if (contentInput.value) {
      quill.root.innerHTML = contentInput.value;
    }
    
    // Update hidden input on text change
    quill.on('text-change', function() {
      contentInput.value = quill.root.innerHTML;
    });
    
    // Ensure form submission includes the editor content
    const storyForm = document.getElementById('story-form');
    const reviewForm = document.getElementById('submit-review-form');
    
    if (storyForm) {
      storyForm.addEventListener('submit', function() {
        contentInput.value = quill.root.innerHTML;
      });
    }
    
    if (reviewForm) {
      reviewForm.addEventListener('submit', function() {
        // Create a hidden input for content in the review form
        const reviewContentInput = document.createElement('input');
        reviewContentInput.type = 'hidden';
        reviewContentInput.name = 'content';
        reviewContentInput.value = quill.root.innerHTML;
        reviewForm.appendChild(reviewContentInput);
      });
    }
  }
}

/**
 * Initialize audio file uploads for stories
 */
function initAudioUpload() {
  const audioFileInput = document.getElementById('audio_files');
  const audioPreview = document.getElementById('audio-preview');
  const addAudioBtn = document.getElementById('add-audio-btn');
  const audioList = document.createElement('div');
  audioList.className = 'space-y-3 mt-3';
  audioPreview.appendChild(audioList);
  
  // Array to keep track of files to be uploaded
  let filesToUpload = [];
  
  if (!audioFileInput || !audioPreview) return;
  
  // Create hidden inputs for each selected file
  function updateHiddenInputs() {
    // Remove existing hidden inputs
    document.querySelectorAll('input[name^="audio_file_"]').forEach(input => input.remove());
    
    // Create form data object to hold the files
    const form = document.getElementById('story-form');
    if (!form) return;
    
    filesToUpload.forEach((file, index) => {
      // Create a new hidden input for each file
      const input = document.createElement('input');
      input.type = 'file';
      input.name = `audio_file_${index}`;
      input.classList.add('hidden');
      
      // Create a DataTransfer object and append the file
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      input.files = dataTransfer.files;
      
      // Append to the form
      form.appendChild(input);
    });
  }
  
  // Truncate file name to fit container
  function truncateFileName(fileName, maxLength = 30) {
    if (fileName.length <= maxLength) return fileName;
    
    const extension = fileName.split('.').pop();
    const nameWithoutExt = fileName.substring(0, fileName.length - extension.length - 1);
    
    if (nameWithoutExt.length <= maxLength - 5) return fileName;
    
    return nameWithoutExt.substring(0, maxLength - 5) + '...' + '.' + extension;
  }
  
  // Render the file list
  function renderFileList() {
    audioList.innerHTML = "";
    
    if (filesToUpload.length === 0) {
      const emptyState = document.createElement('div');
      emptyState.className = 'text-sm text-gray-500 italic';
      emptyState.textContent = 'No audio files selected';
      audioList.appendChild(emptyState);
      return;
    }
    
    filesToUpload.forEach((file, index) => {
      const fileItem = document.createElement('div');
      fileItem.className = 'flex items-center p-3 bg-gray-50 border rounded';
      
      // Add audio icon
      const icon = document.createElement('span');
      icon.className = 'mr-3 text-gray-500 flex-shrink-0';
      icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>';
      
      // File details container
      const fileDetails = document.createElement('div');
      fileDetails.className = 'flex-1 min-w-0'; // min-width prevents overflow
      
      // Add file name (truncated)
      const fileName = document.createElement('div');
      fileName.className = 'font-medium text-gray-800 truncate';
      fileName.title = file.name; // Full name on hover
      fileName.textContent = truncateFileName(file.name);
      
      // Add file size
      const fileSize = document.createElement('div');
      fileSize.className = 'text-xs text-gray-500';
      fileSize.textContent = formatFileSize(file.size);
      
      fileDetails.appendChild(fileName);
      fileDetails.appendChild(fileSize);
      
      // Add remove button
      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'ml-3 text-red-500 hover:text-red-700 flex-shrink-0';
      removeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>';
      removeBtn.addEventListener('click', () => {
        filesToUpload.splice(index, 1);
        renderFileList();
        updateHiddenInputs();
      });
      
      fileItem.appendChild(icon);
      fileItem.appendChild(fileDetails);
      fileItem.appendChild(removeBtn);
      audioList.appendChild(fileItem);
    });
    
    // Add file count summary
    const summary = document.createElement('div');
    summary.className = 'text-sm mt-2 text-gray-600';
    summary.textContent = `${filesToUpload.length} file${filesToUpload.length !== 1 ? 's' : ''} selected`;
    audioList.appendChild(summary);
  }
  
  // Initialize file input change handler
  audioFileInput.addEventListener('change', function(e) {
    if (this.files.length > 0) {
      // Add newly selected files to our array
      Array.from(this.files).forEach(file => {
        filesToUpload.push(file);
      });
      
      // Reset file input so the same file can be selected again
      this.value = '';
      
      // Update the UI and hidden inputs
      renderFileList();
      updateHiddenInputs();
    }
  });
  
  // Set up button to trigger file input
  if (addAudioBtn) {
    addAudioBtn.addEventListener('click', function() {
      audioFileInput.click();
    });
  }
  
  // Initialize the view with empty state
  renderFileList();
  
  // Ensure form submission includes all files
  const storyForm = document.getElementById('story-form');
  if (storyForm) {
    storyForm.addEventListener('submit', function() {
      updateHiddenInputs();
    });
  }
  
  // Helper function to format file size
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}