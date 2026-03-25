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
// Quantity selector on product detail page
function changeQty(amount) {
    const input = document.getElementById('quantity');
    if (input) {
        const newVal = parseInt(input.value) + amount;
        const max = parseInt(input.max);
        if (newVal >= 1 && newVal <= max) {
            input.value = newVal;
        }
    }
}

// Cookie consent — shows banner on first visit, hides it once accepted
document.addEventListener('DOMContentLoaded', function() {
    if (!localStorage.getItem('cookiesAccepted')) {
        document.getElementById('cookie-banner').style.display = 'flex';
    }
});

function acceptCookies() {
    localStorage.setItem('cookiesAccepted', 'true');
    document.getElementById('cookie-banner').style.display = 'none';
}

// Accessibility — high contrast mode
function toggleContrast() {
    document.body.classList.toggle('high-contrast');
    localStorage.setItem('highContrast', document.body.classList.contains('high-contrast'));
}

// Accessibility — font size controls
function increaseFontSize() {
    const current = parseFloat(getComputedStyle(document.body).fontSize);
    document.body.style.fontSize = (current + 2) + 'px';
}

function decreaseFontSize() {
    const current = parseFloat(getComputedStyle(document.body).fontSize);
    if (current > 12) {
        document.body.style.fontSize = (current - 2) + 'px';
    }
}

// Remember accessibility preferences on page load
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('highContrast') === 'true') {
        document.body.classList.add('high-contrast');
    }
});