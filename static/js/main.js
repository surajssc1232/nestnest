// Custom JavaScript for NestCircle

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Theme toggle functionality
    const themeSwitch = document.getElementById('theme-switch');
    const themeSwitchContainer = document.querySelector('.theme-switch-container');
    
    if (themeSwitch) {
        // Check for saved user preference
        const currentTheme = localStorage.getItem('theme') || 'light';
        
        // Apply saved theme on page load
        if (currentTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeSwitch.checked = true;
        }
        
        // Listen for theme toggle
        themeSwitch.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        });
    }

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

    // Load YouTube API if we're on a page with a YouTube player
    if (document.querySelector('#youtube-player')) {
        loadYouTubeAPI();
    }
    
    // Fix YouTube buttons to ensure they correctly redirect
    const youtubeButtons = document.querySelectorAll('.btn-outline-danger[href*="youtube"]');
    youtubeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            console.log('Opening YouTube URL:', url);
            
            // Only proceed if we have a valid URL
            if (url && (url.includes('youtube.com') || url.includes('youtu.be'))) {
                // First try to open in new tab
                const newWindow = window.open(url, '_blank');
                
                // If popup blocker prevents it, redirect in the same tab
                if (!newWindow || newWindow.closed || typeof newWindow.closed=='undefined') {
                    window.location.href = url;
                }
            } else {
                console.error('Invalid YouTube URL:', url);
            }
        });
    });
    
    // YouTube URL validation and preview
    const youtubeInput = document.querySelector('#youtube_input input');
    if (youtubeInput) {
        const previewContainer = document.createElement('div');
        previewContainer.className = 'mt-3';
        youtubeInput.parentNode.appendChild(previewContainer);

        youtubeInput.addEventListener('input', function() {
            const url = this.value;
            const validation = validateYouTubeUrl(url);
            
            if (validation.isValid) {
                let embedUrl;
                if (validation.playlistId) {
                    embedUrl = `https://www.youtube.com/embed/videoseries?list=${validation.playlistId}`;
                    previewContainer.innerHTML = `
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i> Valid YouTube playlist
                        </div>
                        <div class="ratio ratio-16x9">
                            <iframe src="${embedUrl}" allowfullscreen></iframe>
                        </div>
                    `;
                } else if (validation.videoId) {
                    embedUrl = `https://www.youtube.com/embed/${validation.videoId}`;
                    previewContainer.innerHTML = `
                        <div class="alert alert-success">
                            <i class="fas fa-check-circle me-2"></i> Valid YouTube video
                        </div>
                        <div class="ratio ratio-16x9">
                            <iframe src="${embedUrl}" allowfullscreen></iframe>
                        </div>
                    `;
                }
            } else if (url) {
                previewContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-circle me-2"></i> Invalid YouTube URL
                    </div>
                `;
            } else {
                previewContainer.innerHTML = '';
            }
        });
    }
});

// Function to confirm resource deletion
function confirmDelete(event, resourceId) {
    // No confirmation prompt as requested
    return true;
}

// Load YouTube IFrame API
function loadYouTubeAPI() {
    const tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
}

let player;
function onYouTubeIframeAPIReady() {
    const iframe = document.querySelector('#youtube-player');
    if (!iframe) return;

    player = new YT.Player('youtube-player', {
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
    });
}

function onPlayerReady(event) {
    // Player is ready
    console.log('YouTube player is ready');
}

function onPlayerStateChange(event) {
    // Handle player state changes
    console.log('Player state changed:', event.data);
}

// YouTube video timestamp handling
function toggleVideoTimestamp(button) {
    if (!player) return;
    
    try {
        const timestamp = Math.floor(player.getCurrentTime());
        const videoId = player.getVideoData().video_id;
        const timestampedUrl = `https://www.youtube.com/watch?v=${videoId}&t=${timestamp}s`;
        
        // Copy to clipboard
        navigator.clipboard.writeText(timestampedUrl).then(() => {
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-check me-1"></i> Copied!';
            button.classList.add('btn-success');
            button.classList.remove('btn-outline-secondary');
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 2000);
        });
    } catch (error) {
        console.error('Error getting video timestamp:', error);
    }
}

// YouTube URL validation and preview
function validateYouTubeUrl(url) {
    if (!url) return { isValid: false };
    
    // Modified regex to better handle different YouTube URL formats including URLs with dashes
    const videoIdMatch = url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
    const playlistMatch = url.match(/[?&]list=([^#\&\?]+)/);
    
    console.log("URL validation:", url, videoIdMatch ? videoIdMatch[1] : "No match");
    
    // Additional check for short URLs in case regex fails
    let videoId = null;
    if (videoIdMatch) {
        videoId = videoIdMatch[1];
    } else if (url.includes('youtu.be/')) {
        videoId = url.split('youtu.be/')[1].split('?')[0];
        console.log("Extracted video ID manually:", videoId);
    }
    
    return {
        isValid: !!(videoId || playlistMatch),
        videoId: videoId,
        playlistId: playlistMatch ? playlistMatch[1] : null
    };
}

// Function to open YouTube link
function openYouTubeLink(url) {
    console.log('Opening YouTube URL:', url);
    
    // Make sure URL is a string
    if (typeof url !== 'string') {
        console.error('URL is not a string:', url);
        alert('Invalid URL format');
        return false;
    }
    
    // Make sure we have a YouTube URL (very permissive check)
    if (!url || (!url.includes('youtube') && !url.includes('youtu.be'))) {
        console.error('Not a YouTube URL:', url);
        alert('Not a valid YouTube URL: ' + url);
        return false;
    }
    
    // Try direct window.open first
    const newWindow = window.open(url, '_blank');
    
    // If blocked by popup blocker, try location.href
    if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
        console.log('Popup blocked, trying location.href');
        
        // Confirm with user before changing location
        if (confirm('Open YouTube in the current tab?')) {
            window.location.href = url;
        }
    }
    
    return true;
}
