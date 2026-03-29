const BASE_URL = 'http://127.0.0.1:8000/api';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.role = localStorage.getItem('user_role');
    }

    async login(email, password) {
        try {
            const response = await fetch(`${BASE_URL}/auth/token/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            if (!response.ok) throw new Error('Échec de la connexion');
            
            const data = await response.json();
            this.token = data.access;
            this.role = data.role;
            
            // Stockage persistant pour la session
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('user_role', data.role);
            localStorage.setItem('full_name', data.full_name);
            
            return data;
        } catch (e) {
            console.error('Erreur login:', e);
            throw e;
        }
    }

    logout() {
        this.token = null;
        this.role = null;
        localStorage.clear();
        window.location.href = 'index.html';
    }

    async fetchWithAuth(endpoint, options = {}) {
        if (!this.token) {
            console.warn('Pas de token. Tentative de redirection ou auto-login...');
            // AUTO LOGIN POUR DEMO (si nécessaire)
            if (window.location.pathname.includes('doctor')) {
                await this.login('dr.lydia.khelifi0@test.com', 'testpass123');
            } else {
                await this.login('patient0@test.com', 'testpass123');
            }
        }

        const headers = {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json',
            ...options.headers
        };

        let response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });
        
        if (response.status === 401 && !options.isRetry) {
            console.warn('Token expiré, déconnexion...');
            this.logout();
        }
        
        return response;
    }

    // --- Endpoints PATIENTS ---
    async searchDoctors(params = {}) {
        const query = new URLSearchParams(params).toString();
        // Modification URL : /doctors/list/
        const res = await this.fetchWithAuth(`/doctors/list/?${query}`);
        if (!res.ok) throw new Error('Échec de la recherche');
        return res.json();
    }

    async getDoctorDetails(id) {
        const res = await this.fetchWithAuth(`/doctors/${id}/`);
        if (!res.ok) throw new Error('Impossible de charger le docteur');
        return res.json();
    }

    async getDoctorSlots(id) {
        const res = await this.fetchWithAuth(`/doctors/${id}/slots/`);
        if (!res.ok) throw new Error('Impossible de charger les créneaux');
        return res.json();
    }

    async bookAppointment(slotId, motif="Consultation") {
        const res = await this.fetchWithAuth('/appointments/', {
            method: 'POST',
            body: JSON.stringify({ slot: slotId, motif })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(JSON.stringify(err));
        }
        return res.json();
    }

    async getPatientAppointments() {
        const res = await this.fetchWithAuth('/appointments/');
        if (!res.ok) throw new Error('Erreur récupération RDV');
        return res.json();
    }

    // --- Endpoints DOCTEURS ---
    async getDoctorProfile() {
        const res = await this.fetchWithAuth('/doctors/profile/');
        return res.json();
    }

    async getPendingRequests() {
        // Modification URL : filtrage status=pending
        const res = await this.fetchWithAuth('/doctor/appointments/pending/');
        return res.json();
    }

    async confirmAppointment(id) {
        // Modification URL : /confirm/ en POST
        const res = await this.fetchWithAuth(`/doctor/appointments/${id}/confirm/`, { method: 'POST' });
        return res.json();
    }

    async refuseAppointment(id, reason="Indisponible") {
        const res = await this.fetchWithAuth(`/doctor/appointments/${id}/refuse/`, { 
            method: 'POST',
            body: JSON.stringify({ reason })
        });
        return res.json();
    }

    async getDoctorAppointments() {
        const res = await this.fetchWithAuth('/doctor/appointments/');
        return res.json();
    }
}

const api = new ApiClient();

// Utilitaires UI
function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function getInitials(name) {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
}
