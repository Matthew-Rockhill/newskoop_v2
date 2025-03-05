// main.js - Modern UI interactions for Newskoop

document.addEventListener('DOMContentLoaded', function() {
    initAlertDismissals();
    initDropdowns();
    initMobileMenu();
  });
  
  // Dismiss alerts
  function initAlertDismissals() {
    document.querySelectorAll('.alert-close').forEach(button => {
      button.addEventListener('click', function() {
        const alert = this.closest('.alert');
        alert.style.opacity = '0';
        setTimeout(() => { alert.style.display = 'none'; }, 300);
      });
    });
  }
  
  // Dropdown menus
  function initDropdowns() {
    const triggers = document.querySelectorAll('.dropdown-trigger');
    triggers.forEach(trigger => {
      trigger.addEventListener('click', function(e) {
        e.preventDefault();
        const menu = this.nextElementSibling;
        menu.classList.toggle('active');
      });
    });
    document.addEventListener('click', function(e) {
      document.querySelectorAll('.dropdown-menu.active').forEach(menu => {
        if (!menu.contains(e.target)) {
          menu.classList.remove('active');
        }
      });
    });
  }
  
  // Mobile sidebar toggle
  function initMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    const toggle = document.createElement('button');
    toggle.className = 'mobile-menu-toggle';
    toggle.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M3 12h18M3 6h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;
    const topNav = document.querySelector('.top-nav');
    if (topNav) topNav.insertBefore(toggle, topNav.firstChild);
    toggle.addEventListener('click', function() {
      sidebar.classList.toggle('show-mobile');
      this.classList.toggle('active');
    });
    const style = document.createElement('style');
    style.textContent = `
      .mobile-menu-toggle { display: none; background: none; border: none; }
      @media (max-width:768px) {
        .mobile-menu-toggle { display: block; }
        .sidebar { display: none; }
        .sidebar.show-mobile { display: block; }
      }
    `;
    document.head.appendChild(style);
  }
  