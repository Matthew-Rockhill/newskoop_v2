document.addEventListener('DOMContentLoaded', function() {
  // When submit-review-form is submitted, copy values from main form
  const reviewForm = document.getElementById('submit-review-form');
  const mainForm = document.getElementById('story-form');
  
  if (reviewForm && mainForm) {
    reviewForm.addEventListener('submit', function(e) {
      // The content copying is handled by the initStoryEditor function in main.js
      
      // Copy title value
      const titleInput = document.createElement('input');
      titleInput.type = 'hidden';
      titleInput.name = 'title';
      titleInput.value = document.getElementById('id_title').value;
      reviewForm.appendChild(titleInput);
      
      // Copy category value if it exists
      const categoryInput = document.getElementById('id_category');
      if (categoryInput) {
        const categoryHiddenInput = document.createElement('input');
        categoryHiddenInput.type = 'hidden';
        categoryHiddenInput.name = 'category';
        categoryHiddenInput.value = categoryInput.value;
        reviewForm.appendChild(categoryHiddenInput);
      }
      
      // Copy religion classification if it exists
      const religionInput = document.getElementById('id_religion_classification');
      if (religionInput) {
        const religionHiddenInput = document.createElement('input');
        religionHiddenInput.type = 'hidden';
        religionHiddenInput.name = 'religion_classification';
        religionHiddenInput.value = religionInput.value;
        reviewForm.appendChild(religionHiddenInput);
      }
      
      // Copy language value
      const languageInput = document.createElement('input');
      languageInput.type = 'hidden';
      languageInput.name = 'language';
      languageInput.value = document.getElementById('id_language').value;
      reviewForm.appendChild(languageInput);
    });
  }
}); 