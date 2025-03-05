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