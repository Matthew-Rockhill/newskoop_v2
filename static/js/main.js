/**
 * Modified version of main.js with improved Quill editor interaction
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
    userMenuButton.addEventListener('click', function(e) {
      e.stopPropagation();
      const isExpanded = userMenuButton.getAttribute('aria-expanded') === 'true';
      userMenuButton.setAttribute('aria-expanded', !isExpanded);
      userDropdownMenu.classList.toggle('hidden');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(event) {
      if (!userMenuButton.contains(event.target) && !userDropdownMenu.contains(event.target)) {
        userDropdownMenu.classList.add('hidden');
        userMenuButton.setAttribute('aria-expanded', 'false');
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
  
  // Initialize category toggles
  initCategoryToggles();
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
 * Initialize all category toggles on the category list page
 */
function initCategoryToggles() {
  // Function to update an icon with new SVG content
  function updateIcon(icon, isExpanded) {
    if (!icon) return;
    
    // We'll generate the correct SVG based on the expanded state
    // This avoids relying on Django template tags in JavaScript
    const iconSVG = isExpanded 
      ? '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><polyline points="6 9 12 15 18 9"></polyline></svg>'
      : '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4"><polyline points="9 18 15 12 9 6"></polyline></svg>';
      
    icon.innerHTML = iconSVG;
  }
  
  // Function to handle toggle clicks for any type of toggle
  function setupToggle(toggleSelector, iconSelector) {
    const toggles = document.querySelectorAll(toggleSelector);
    
    toggles.forEach(toggle => {
      // Check if we already added an event listener to this element
      if (toggle.getAttribute('data-toggle-initialized') === 'true') {
        return;
      }
      
      toggle.addEventListener('click', function(e) {
        e.stopPropagation(); // Prevent parent handlers from firing
        
        const targetId = this.getAttribute('data-target');
        const targetElement = document.getElementById(targetId);
        const icon = this.querySelector(iconSelector);
        const textSpan = this.querySelector('span');
        
        if (!targetElement) {
          console.error(`Target element with ID "${targetId}" not found`);
          return;
        }
        
        const isCurrentlyHidden = targetElement.classList.contains('hidden');
        
        // Toggle visibility
        if (isCurrentlyHidden) {
          targetElement.classList.remove('hidden');
          updateIcon(icon, true);
          
          if (textSpan) {
            const countText = textSpan.textContent.split(' ')[0];
            textSpan.textContent = `${countText} subcategories (hide)`;
          }
        } else {
          targetElement.classList.add('hidden');
          updateIcon(icon, false);
          
          if (textSpan) {
            const countText = textSpan.textContent.split(' ')[0];
            textSpan.textContent = `${countText} subcategories`;
          }
        }
      });
      
      // Mark as initialized to prevent duplicate event listeners
      toggle.setAttribute('data-toggle-initialized', 'true');
    });
  }
  
  // Initialize section toggles (content type accordions)
  const sectionHeaders = document.querySelectorAll('.section-header');
  sectionHeaders.forEach(header => {
    if (header.getAttribute('data-toggle-initialized') === 'true') {
      return;
    }
    
    const targetId = header.getAttribute('data-target');
    const targetElement = document.getElementById(targetId);
    const icon = header.querySelector('.toggle-icon');
    
    // Set initial state: expanded
    if (targetElement && icon) {
      targetElement.classList.remove('hidden');
      updateIcon(icon, true);
    }
    
    header.addEventListener('click', function() {
      if (targetElement && icon) {
        const isCurrentlyHidden = targetElement.classList.contains('hidden');
        
        if (isCurrentlyHidden) {
          targetElement.classList.remove('hidden');
          updateIcon(icon, true);
        } else {
          targetElement.classList.add('hidden');
          updateIcon(icon, false);
        }
      }
    });
    
    header.setAttribute('data-toggle-initialized', 'true');
  });
  
  // Initialize parent category toggles
  setupToggle('.children-toggle', '.children-icon');
  
  // Initialize subcategory toggles
  setupToggle('.subcategories-toggle', '.subcategories-icon');
  
  console.log('Category toggles initialized');
}

/**
 * Initialize Quill editor for story content
 * UPDATED to handle form submission properly
 */
function initStoryEditor() {
  const editorContainer = document.getElementById('content-editor');
  const contentInput = document.getElementById('id_content');
  
  // Find the appropriate form - either story-form or translation-form
  const storyForm = document.getElementById('story-form');
  const translationForm = document.getElementById('translation-form');
  
  // Check if Quill is already initialized
  if (window.quillInstance) {
    return;
  }
  
  if (editorContainer && contentInput) {
    // Register custom sizes
    var Size = Quill.import('attributors/style/size');
    Size.whitelist = ['12px', '14px', '16px', '18px', '1rem'];
    Quill.register(Size, true);

    // Configure Quill toolbar options
    const toolbarOptions = [
      ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
      ['blockquote', 'code-block'],
      [{ 'header': 1 }, { 'header': 2 }],               // custom button values
      [{ 'list': 'ordered'}, { 'list': 'bullet' }],
      [{ 'script': 'sub'}, { 'script': 'super' }],      // superscript/subscript
      [{ 'indent': '-1'}, { 'indent': '+1' }],          // outdent/indent
      [{ 'direction': 'rtl' }],                         // text direction
      [{ 'size': ['12px', '14px', '16px', '18px', '1rem', false] }],  // custom dropdown
      [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
      [{ 'color': [] }, { 'background': [] }],          // dropdown with defaults
      [{ 'font': [] }],
      [{ 'align': [] }],
      ['clean'],                                         // remove formatting button
      ['link', 'image']                                  // link and image
    ];

    // Initialize Quill
    window.quillInstance = new Quill('#content-editor', {
      modules: {
        toolbar: toolbarOptions
      },
      theme: 'snow'
    });

    // Set default font size to 1rem
    window.quillInstance.format('size', '1rem');

    // Load existing content if any
    if (contentInput.value) {
      window.quillInstance.root.innerHTML = contentInput.value;
    }

    // NEW CODE: The key problem is that we need to ensure Quill updates the hidden input
    // before the form submits. We'll attach to all potential form submit events.
    
    // 1. Find all submit buttons with form attribute that target our form
    document.querySelectorAll(`button[form="story-form"], input[type="submit"][form="story-form"]`).forEach(button => {
      button.addEventListener('click', function() {
        // Update the hidden input with the Quill content
        contentInput.value = window.quillInstance.root.innerHTML;
        console.log('Submit button clicked, Quill content saved to hidden input');
      });
    });
    
    // 2. Also handle direct form submission events
    if (storyForm) {
      storyForm.addEventListener('submit', function() {
        contentInput.value = window.quillInstance.root.innerHTML;
        console.log('Story form submitted, Quill content saved to hidden input');
      });
    }
    
    // 3. And translation form if present
    if (translationForm) {
      translationForm.addEventListener('submit', function() {
        contentInput.value = window.quillInstance.root.innerHTML;
        console.log('Translation form submitted, Quill content saved to hidden input');
      });
    }

    // Handle "Submit for Review" button (keep this part if it's needed)
    const submitReviewBtn = document.querySelector('button[form="submit-review-form"]');
    const submitReviewForm = document.getElementById('submit-review-form');

    if (submitReviewBtn && submitReviewForm && window.quillInstance) {
      submitReviewBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Update the content input in the submit-review-form with the current Quill content
        const contentInput = submitReviewForm.querySelector('input[name="content"]');
        if (contentInput) {
          contentInput.value = window.quillInstance.root.innerHTML;
        } else {
          // If the content input doesn't exist, create it
          const newContentInput = document.createElement('input');
          newContentInput.type = 'hidden';
          newContentInput.name = 'content';
          newContentInput.value = window.quillInstance.root.innerHTML;
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
    
    // Log successful initialization
    console.log('Quill editor initialized and form submission handlers attached');
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
          container.className = 'flex flex-col p-3 bg-gray-50 rounded-lg mb-2';
          
          // Info section
          const infoDiv = document.createElement('div');
          infoDiv.className = 'flex items-center justify-between mb-2';
          
          const infoLeft = document.createElement('div');
          infoLeft.className = 'flex items-center space-x-3';
          
          // Icon
          const iconDiv = document.createElement('div');
          iconDiv.className = 'flex-shrink-0';
          iconDiv.innerHTML = '<svg class="h-5 w-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>';
          
          // File info
          const textInfo = document.createElement('div');
          textInfo.innerHTML = `
            <h4 class="text-sm font-medium text-gray-900">${file.name}</h4>
            <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
          `;
          
          infoLeft.appendChild(iconDiv);
          infoLeft.appendChild(textInfo);
          infoDiv.appendChild(infoLeft);
          
          // Audio player
          const audio = document.createElement('audio');
          audio.controls = true;
          audio.className = 'w-full';
          
          const source = document.createElement('source');
          source.src = URL.createObjectURL(file);
          source.type = file.type;
          
          audio.appendChild(source);
          
          // Add components to container
          container.appendChild(infoDiv);
          container.appendChild(audio);
          
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

// Make sure category forms submit properly
document.addEventListener('DOMContentLoaded', function() {
  const categoryForm = document.getElementById('category-form');
  if (categoryForm) {
    // Remove any existing event listeners that might interfere
    const clonedForm = categoryForm.cloneNode(true);
    categoryForm.parentNode.replaceChild(clonedForm, categoryForm);
    
    // Add a simple submit handler for logging
    clonedForm.addEventListener('submit', function(e) {
      console.log('Category form submitted');
    });
  }
});

/**
 * Initialize select2 for tag selection
 */
function initTagSelect() {
  // Initialize select2 for tag selection
  $('.select2-tags').select2({
    placeholder: 'Select or search for tags',
    allowClear: true,
    tags: false,  // Don't allow creating new tags inline
    width: '100%'
  });
  
  // Make sure the tags are properly saved on form submission
  $('#story-form').on('submit', function() {
    // Ensure all select2 changes are committed before form submission
    $('.select2-tags').trigger('change');
  });
}

// Call the function on document ready
$(document).ready(function() {
  if ($('.select2-tags').length) {
    initTagSelect();
  }
});

function initTagsMultiSelect() {
  const tagsSelects = document.querySelectorAll('select[multiple].tags-select');
  
  tagsSelects.forEach(select => {
    // Create a container for our custom dropdown
    const container = document.createElement('div');
    container.className = 'relative';
    
    // Create the input for searching
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary-100 focus:ring-opacity-50';
    searchInput.placeholder = 'Search and select tags...';
    
    // Create dropdown for options
    const dropdown = document.createElement('div');
    dropdown.className = 'absolute w-full bg-white mt-1 border border-gray-300 rounded-md shadow-lg z-10 max-h-60 overflow-y-auto hidden';
    
    // Create selected items container
    const selectedContainer = document.createElement('div');
    selectedContainer.className = 'flex flex-wrap gap-2 mt-2';
    
    // Add the components to the container
    container.appendChild(searchInput);
    container.appendChild(dropdown);
    select.parentNode.insertBefore(container, select);
    container.appendChild(select);
    container.appendChild(selectedContainer);
    
    // Hide the original select
    select.style.display = 'none';
    
    // Populate the dropdown with options
    const options = Array.from(select.options);
    options.forEach(option => {
      const optionElement = document.createElement('div');
      optionElement.className = 'p-2 hover:bg-gray-100 cursor-pointer flex items-center';
      optionElement.dataset.value = option.value;
      
      // Add checkbox
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'mr-2 rounded border-gray-300 text-primary focus:ring-primary';
      checkbox.checked = option.selected;
      optionElement.appendChild(checkbox);
      
      // Add label
      const label = document.createElement('span');
      label.textContent = option.textContent;
      optionElement.appendChild(label);
      
      // If the option is selected, add it to the selected container
      if (option.selected) {
        addSelectedTag(option.value, option.textContent);
      }
      
      // Add click event to select/deselect
      optionElement.addEventListener('click', (e) => {
        if (e.target !== checkbox) {
          checkbox.checked = !checkbox.checked;
        }
        
        const optIndex = Array.from(select.options).findIndex(opt => opt.value === option.value);
        select.options[optIndex].selected = checkbox.checked;
        
        if (checkbox.checked) {
          addSelectedTag(option.value, option.textContent);
        } else {
          removeSelectedTag(option.value);
        }
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        select.dispatchEvent(event);
      });
      
      dropdown.appendChild(optionElement);
    });
    
    // Function to add a tag to the selected container
    function addSelectedTag(value, text) {
      const tag = document.createElement('span');
      tag.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800';
      tag.textContent = text;
      
      const removeBtn = document.createElement('button');
      removeBtn.className = 'ml-1 text-primary-600 hover:text-primary-800 focus:outline-none';
      removeBtn.innerHTML = '×';
      removeBtn.type = 'button';
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        removeSelectedTag(value);
        
        // Update the original select
        const optIndex = Array.from(select.options).findIndex(opt => opt.value === value);
        select.options[optIndex].selected = false;
        
        // Update checkbox
        const checkbox = dropdown.querySelector(`[data-value="${value}"] input[type="checkbox"]`);
        if (checkbox) {
          checkbox.checked = false;
        }
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        select.dispatchEvent(event);
      });
      
      tag.appendChild(removeBtn);
      selectedContainer.appendChild(tag);
    }
    
    // Function to remove a tag from the selected container
    function removeSelectedTag(value) {
      const tag = selectedContainer.querySelector(`[data-value="${value}"]`);
      if (tag) {
        tag.remove();
      }
    }
    
    // Toggle dropdown on input focus/click
    searchInput.addEventListener('focus', () => {
      dropdown.classList.remove('hidden');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!container.contains(e.target)) {
        dropdown.classList.add('hidden');
      }
    });
    
    // Filter options based on search input
    searchInput.addEventListener('input', (e) => {
      const searchTerm = e.target.value.toLowerCase();
      const options = dropdown.querySelectorAll('[data-value]');
      
      options.forEach(option => {
        const text = option.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          option.style.display = '';
        } else {
          option.style.display = 'none';
        }
      });
    });
  });
}

// Call the function when the document is ready
document.addEventListener('DOMContentLoaded', function() {
  // Your existing code...
  
  // Initialize multiselect for tags
  initTagsMultiSelect();
});