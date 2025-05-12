// Handle dropdown menus in the dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Close all dropdowns when clicking outside
    document.addEventListener('click', function(event) {
        const dropdowns = document.querySelectorAll('[role="menu"]');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(event.target) && !event.target.matches('[aria-haspopup="true"]')) {
                dropdown.classList.add('hidden');
                const button = document.querySelector(`[aria-labelledby="${dropdown.id}"]`);
                if (button) {
                    button.setAttribute('aria-expanded', 'false');
                }
            }
        });
    });

    // Toggle dropdowns when clicking their buttons
    document.querySelectorAll('[aria-haspopup="true"]').forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
            const menuId = this.getAttribute('id').replace('-button', '');
            const menu = document.querySelector(`[aria-labelledby="${menuId}"]`);
            
            if (menu) {
                const isExpanded = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', !isExpanded);
                menu.classList.toggle('hidden');
            }
        });
    });
}); 