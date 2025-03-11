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