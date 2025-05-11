// Custom JavaScript for NestCircle

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Animate cards on page load
    var cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        setTimeout(function() {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });

    // Validate file uploads
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                if (!file.name.endsWith('.pdf')) {
                    alert('Please upload a PDF file only.');
                    this.value = '';
                } else if (file.size > 16 * 1024 * 1024) { // 16MB
                    alert('File size exceeds 16MB. Please upload a smaller file.');
                    this.value = '';
                }
            }
        });
    }

    // Handle resource type selection
    const resourceTypeSelect = document.getElementById('resource_type');
    if (resourceTypeSelect) {
        resourceTypeSelect.addEventListener('change', function() {
            toggleResourceInput();
        });
    }

    // YouTube embed preview
    const youtubeInput = document.querySelector('#youtube_input input');
    if (youtubeInput) {
        youtubeInput.addEventListener('blur', function() {
            const youtubeUrl = this.value;
            if (youtubeUrl && (youtubeUrl.includes('youtube.com') || youtubeUrl.includes('youtu.be'))) {
                // Here you could add code to show a preview of the video
                console.log('Valid YouTube URL:', youtubeUrl);
            }
        });
    }
});

// Function to confirm resource deletion
function confirmDelete(event, resourceId) {
    if (!confirm('Are you sure you want to delete this resource? This action cannot be undone.')) {
        event.preventDefault();
    }
}
