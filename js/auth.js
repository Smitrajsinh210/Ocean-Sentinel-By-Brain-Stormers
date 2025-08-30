// Authentication Functions
async function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const spinner = document.getElementById('loginSpinner');

    spinner.classList.remove('hidden');

    try {
        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email: email,
            password: password
        });

        if (error) throw error;

        // Manually trigger dashboard initialization
        if (data.user) {
            window.oceanSentinel.user = data.user;
            await window.oceanSentinel.initDashboard();
        }

    } catch (error) {
        console.error('Login error:', error);
        alert('Login failed: ' + error.message);
    } finally {
        spinner.classList.add('hidden');
    }
}

async function handleRegister(event) {
    event.preventDefault();

    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const org = document.getElementById('registerOrg').value;
    const password = document.getElementById('registerPassword').value;
    const spinner = document.getElementById('registerSpinner');

    spinner.classList.remove('hidden');

    try {
        const { data, error } = await supabaseClient.auth.signUp({
            email: email,
            password: password,
            options: {
                data: {
                    full_name: name,
                    organization: org
                }
            }
        });

        if (error) throw error;

        alert('Registration successful! Please check your email to verify your account.');
        showLogin();

    } catch (error) {
        console.error('Registration error:', error);
        alert('Registration failed: ' + error.message);
    } finally {
        spinner.classList.add('hidden');
    }
}

async function handleLogout() {
    try {
        const { error } = await supabaseClient.auth.signOut();
        if (error) throw error;
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function showLogin() {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
}

function showRegister() {
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.remove('hidden');
}