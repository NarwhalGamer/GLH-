// Auto-format expiry date as MM/YY when user types
document.addEventListener('DOMContentLoaded', function() {
    const expiryInput = document.getElementById('expiry');

    if (expiryInput) {
        expiryInput.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');
            if (value.length >= 2) {
                value = value.substring(0, 2) + '/' + value.substring(2, 4);
            }
            this.value = value;
        });
    }
});

// Tab switching for dashboards — shows selected section, hides others
function showTab(tabId) {
    // Hide all tab sections
    const sections = document.querySelectorAll('.tab-section');
    sections.forEach(section => section.style.display = 'none');

    // Show the selected tab
    document.getElementById(tabId).style.display = 'block';

    // Update active sidebar link
    const links = document.querySelectorAll('.sidebar-link');
    links.forEach(link => link.classList.remove('active'));
    event.target.classList.add('active');
}