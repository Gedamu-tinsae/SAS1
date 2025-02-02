document.addEventListener('DOMContentLoaded', function() {
    var loginForm = document.getElementById('loginForm');
    var loginBtn = document.getElementById('loginBtn');

    loginForm.addEventListener('submit', function(event) {
        // Prevent default form submission
        event.preventDefault();
        loginBtn.innerHTML = 'Logging in...';

        var emailInput = document.querySelector('input[name="email"]');
        var passwordInput = document.querySelector('input[name="password"]');

        if (!emailInput.value || !passwordInput.value) {
            alert('Please fill in all fields.');
            loginBtn.innerHTML = 'Login';
            return;
        }

        // Simulate form submission for debugging
        setTimeout(function() {
            console.log('Simulating form submission...');
            loginForm.submit();
        }, 1000); // Delay for 1 second to observe the behavior
    });
});
