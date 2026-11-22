const API_BASE_URL = 'http://localhost:8000';

/**
 * Aplicación de Segmentación de Prendas con Autenticación
 * Ubicación: /Frontend/script.js
 */

class SegmentationApp {
    constructor() {
        this.token = localStorage.getItem('token');
        this.userRole = localStorage.getItem('userRole');
        this.username = localStorage.getItem('username');

        this.video = null;
        this.canvas = null;
        this.processedCanvas = null;
        this.stream = null;
        this.isRunning = false;

        this.fps = 0;
        this.latency = 0;
        this.frameCount = 0;
        this.lastTime = performance.now();

        this.init();
    }

    /**
     * Inicializa la aplicación
     */
    init() {
        if (!this.token) {
            this.showLoginScreen();
        } else {
            this.verifyToken();
        }
    }

    /**
     * Muestra la pantalla de login
     */
    showLoginScreen() {
        document.body.innerHTML = `
            <div id="login-container" class="login-screen">
                <div class="login-modal">
                    <h1>🎨 Fashion Segmentation</h1>
                    <p class="subtitle">Sistema de Análisis de Prendas de Vestir</p>

                    <form id="login-form" class="login-form">
                        <div class="form-group">
                            <label for="username">Usuario</label>
                            <input type="text" id="username" name="username" placeholder="Ingresa tu usuario" required>
                        </div>

                        <div class="form-group">
                            <label for="password">Contraseña</label>
                            <input type="password" id="password" name="password" placeholder="Ingresa tu contraseña" required>
                        </div>

                        <button type="submit" class="btn btn-primary btn-large">Ingresar</button>

                        <div id="login-error" class="error-message"></div>
                    </form>
                </div>
            </div>
        `;

        this.addLoginStyles();
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
    }

    /**
     * Agrega estilos para login
     */
    addLoginStyles() {
        const style = document.createElement('style');
        style.textContent = `
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .login-screen { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
            .login-modal {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                width: 100%;
                max-width: 400px;
            }
            .login-modal h1 {
                text-align: center;
                margin-bottom: 10px;
                color: #333;
                font-size: 32px;
            }
            .subtitle {
                text-align: center;
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }
            .login-form { display: flex; flex-direction: column; gap: 20px; }
            .form-group { display: flex; flex-direction: column; gap: 8px; }
            .form-group label { font-weight: 600; color: #333; font-size: 14px; }
            .form-group input {
                padding: 12px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
            .form-group input:focus { outline: none; border-color: #667eea; background: #f8f9ff; }
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3); }
            .btn-large { padding: 14px 28px; font-size: 16px; width: 100%; }
            .error-message { color: #dc3545; font-size: 14px; text-align: center; display: none; }
            .error-message.show { display: block; }
        `;
        document.head.appendChild(style);
    }

    /**
     * Maneja el login
     */
    async handleLogin(event) {
        event.preventDefault();

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('login-error');

        try {
            const response = await fetch(`${API_BASE_URL}/api/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error en login');
            }

            const data = await response.json();

            console.log('✅ Login exitoso:', data);

            // Guardar en localStorage
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('userRole', data.role);
            localStorage.setItem('username', data.username);

            // Verificar que se guardó
            console.log('Token guardado:', localStorage.getItem('token') ? '✅' : '❌');
            console.log('Role guardado:', localStorage.getItem('userRole'));

            // Asignar a instancia
            this.token = data.access_token;
            this.userRole = data.role;
            this.username = data.username;

            console.log('this.token asignado:', this.token ? '✅' : '❌');

            this.renderApp();

        } catch (error) {
            console.error('❌ Error en login:', error);
            errorDiv.textContent = '❌ ' + error.message;
            errorDiv.classList.add('show');
        }
    }

    /**
     * Verifica validez del token
     */
    async verifyToken() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/me`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (!response.ok) {
                this.logout();
                return;
            }

            this.renderApp();

        } catch (error) {
            this.logout();
        }
    }

    /**
     * Renderiza la interfaz principal
     */
    renderApp() {
        const isAdmin = this.userRole === 'admin';

        document.body.innerHTML = `
            <div id="app-container" class="app-container">
                <header class="header">
                    <div class="header-content">
                        <h1>🎨 Fashion Segmentation</h1>
                        <div class="header-right">
                            <span class="user-info">
                                👤 ${this.username}
                                <span class="role-badge ${isAdmin ? 'admin' : 'user'}">
                                    ${isAdmin ? 'Admin' : 'User'}
                                </span>
                            </span>
                            <button class="btn btn-logout" id="logout-btn">Cerrar sesión</button>
                        </div>
                    </div>
                </header>

                <main class="main-content">
                    ${isAdmin ? this.renderAdminLayout() : this.renderUserLayout()}
                </main>
            </div>
        `;

        this.addMainStyles();

        document.getElementById('logout-btn').addEventListener('click', () => this.logout());

        if (isAdmin) {
            this.setupAdminPanel();
        } else {
            this.setupUserPanel();
        }
    }

    /**
     * Layout para usuario normal
     */
    renderUserLayout() {
        return `
            <div class="user-layout">
                <section class="section camera-section">
                    <h2>📸 Captura de Cámara</h2>
                    <div class="camera-container">
                        <video id="video" autoplay playsinline muted></video>
                        <canvas id="canvas" style="display: none;"></canvas>
                    </div>

                    <div class="camera-controls">
                        <button class="btn btn-primary" id="start-camera-btn">▶️ Iniciar Cámara</button>
                        <button class="btn btn-secondary" id="stop-camera-btn" disabled>⏹️ Detener</button>
                        <button class="btn btn-success" id="extract-btn" disabled>✂️ Separar Prendas</button>
                        <button class="btn btn-info" id="download-btn" disabled>⬇️ Descargar</button>
                    </div>

                    <div class="metrics">
                        <span id="fps-display">FPS: --</span>
                        <span id="latency-display">Latencia: -- ms</span>
                    </div>
                </section>

                <section class="section processed-section">
                    <h2>🔍 Imagen Procesada</h2>
                    <div class="processed-container">
                        <canvas id="processed-canvas" class="processed-canvas"></canvas>
                    </div>
                </section>

                <section class="section garments-section">
                    <h2>👕 Prendas Extraídas</h2>
                    <div id="garments-grid" class="garments-grid">
                        <p class="placeholder">Haz clic en "Separar Prendas" para extraer...</p>
                    </div>
                </section>
            </div>
        `;
    }

    /**
     * Layout para admin
     */
    renderAdminLayout() {
        return `
            <div class="admin-layout">
                <div class="admin-sidebar">
                    <nav class="admin-nav">
                        <button class="nav-item active" data-tab="capture">📸 Captura</button>
                        <button class="nav-item" data-tab="history">📋 Historial</button>
                        <button class="nav-item" data-tab="analytics">📊 Estadísticas</button>
                        <button class="nav-item" data-tab="users">👥 Usuarios</button>
                    </nav>
                </div>

                <div class="admin-content">
                    <div id="tab-capture" class="tab-panel active">
                        <h2>📸 Captura de Cámara</h2>
                        <div class="camera-container">
                            <video id="video" autoplay playsinline muted></video>
                            <canvas id="canvas" style="display: none;"></canvas>
                        </div>

                        <div class="camera-controls">
                            <button class="btn btn-primary" id="start-camera-btn">▶️ Iniciar</button>
                            <button class="btn btn-secondary" id="stop-camera-btn" disabled>⏹️ Detener</button>
                            <button class="btn btn-success" id="extract-btn" disabled>✂️ Separar</button>
                            <button class="btn btn-info" id="download-btn" disabled>⬇️ Descargar</button>
                        </div>

                        <div class="metrics">
                            <span id="fps-display">FPS: --</span>
                            <span id="latency-display">Latencia: -- ms</span>
                        </div>

                        <div class="processed-container">
                            <canvas id="processed-canvas" class="processed-canvas"></canvas>
                        </div>

                        <div id="garments-grid" class="garments-grid">
                            <p class="placeholder">Prendas extraídas aparecerán aquí...</p>
                        </div>
                    </div>

                    <div id="tab-history" class="tab-panel">
                        <h2>📋 Historial de Extracciones</h2>
                        <div id="history-container" class="history-container">
                            <p class="placeholder">Cargando...</p>
                        </div>
                    </div>

                    <div id="tab-analytics" class="tab-panel">
                        <h2>📊 Estadísticas</h2>
                        <div id="analytics-container" class="analytics-container">
                            <p class="placeholder">Estadísticas aparecerán aquí...</p>
                        </div>
                    </div>

                    <div id="tab-users" class="tab-panel">
                        <h2>👥 Gestión de Usuarios</h2>
                        <div class="users-container">
                            <div class="register-form">
                                <h3>Crear Nuevo Usuario</h3>
                                <form id="register-form">
                                    <input type="text" id="new-username" placeholder="Usuario" required>
                                    <input type="password" id="new-password" placeholder="Contraseña (mín. 6 caracteres)" required>
                                    <button type="submit" class="btn btn-primary">➕ Crear Usuario</button>
                                </form>
                            </div>

                            <div class="users-list">
                                <h3>Usuarios Existentes</h3>
                                <div id="users-list-container" class="users-table">
                                    <p class="placeholder">Cargando usuarios...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Agrega estilos principales
     */
    addMainStyles() {
        const style = document.createElement('style');
        style.textContent = `
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
            .app-container { display: flex; flex-direction: column; height: 100vh; }

            /* HEADER */
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 16px 0;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
            .header-content {
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { font-size: 24px; }
            .header-right { display: flex; gap: 20px; align-items: center; }
            .user-info { display: flex; gap: 10px; align-items: center; font-size: 14px; }
            .role-badge {
                padding: 4px 12px;
                border-radius: 20px;
                background: rgba(255, 255, 255, 0.2);
                font-size: 12px;
                font-weight: 600;
            }
            .role-badge.admin { background: #ff6b6b; }
            .btn-logout {
                padding: 8px 16px;
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.4);
                color: white;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s;
            }
            .btn-logout:hover { background: rgba(255, 255, 255, 0.3); }

            /* MAIN CONTENT */
            .main-content { flex: 1; overflow-y: auto; }

            /* USER LAYOUT */
            .user-layout {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            .user-layout .camera-section { grid-column: 1; }
            .user-layout .processed-section { grid-column: 2; }
            .user-layout .garments-section { grid-column: 1 / -1; }

            /* ADMIN LAYOUT */
            .admin-layout { display: flex; height: 100%; }
            .admin-sidebar {
                width: 200px;
                background: white;
                border-right: 1px solid #e0e0e0;
                padding: 20px 0;
            }
            .admin-nav { display: flex; flex-direction: column; gap: 0; }
            .nav-item {
                padding: 12px 20px;
                border: none;
                background: transparent;
                cursor: pointer;
                text-align: left;
                color: #666;
                border-left: 3px solid transparent;
                transition: all 0.3s;
                font-size: 14px;
            }
            .nav-item:hover { background: #f5f5f5; color: #333; }
            .nav-item.active { background: #f5f5f5; border-left-color: #667eea; color: #667eea; font-weight: 600; }

            .admin-content { flex: 1; padding: 20px; overflow-y: auto; }
            .tab-panel { display: none; }
            .tab-panel.active { display: block; }

            /* SECTIONS */
            .section {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .section h2 { margin-bottom: 16px; font-size: 18px; }

            /* CAMERA */
            .camera-container, .processed-container {
                width: 100%;
                height: 60vh;
                min-height: 450px;
                background: #000;
                border-radius: 8px;
                overflow: hidden;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #video, #processed-canvas {
                width: 100%;
                height: 100%;
                max-height: none;
                object-fit: contain;
                flex: 1;
                display: block;
            }

            .camera-controls { display: flex; gap: 10px; margin-bottom: 16px; }
            .metrics { display: flex; gap: 20px; font-size: 14px; color: #666; }

            /* BUTTONS */
            .btn {
                padding: 10px 16px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            .btn:disabled { opacity: 0.5; cursor: not-allowed; }

            .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
            .btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3); }

            .btn-secondary { background: #e0e0e0; color: #333; }
            .btn-secondary:hover:not(:disabled) { background: #d0d0d0; }

            .btn-success { background: #27ae60; color: white; }
            .btn-success:hover:not(:disabled) { background: #229954; }
            .btn-info { background: #3498db; color: white; }
            .btn-info:hover:not(:disabled) { background: #2980b9; }

            /* GARMENTS GRID */
            .garments-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
                gap: 18px;
            }

            .garment-card {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                overflow: hidden;
                transition: all 0.3s;
                display: flex;
                flex-direction: column;
            }
            .garment-card:hover { box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1); }

            .garment-image {
                width: 100%;
                height: 260px;
                background: #f5f5f5;
                object-fit: contain;
                display: block;
            }

            .garment-info { padding: 12px; text-align: center; }
            .garment-name { font-size: 15px; font-weight: 700; margin-bottom: 8px; }

            .color-swatch { width: 100%; height: 32px; border-radius: 4px; border: 1px solid #ddd; }

            .placeholder { text-align: center; color: #999; padding: 20px; grid-column: 1 / -1; }

            .users-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .register-form, .users-list { background: white; padding: 20px; border-radius: 8px; }
            .register-form h3, .users-list h3 { margin-bottom: 16px; }

            #register-form { display: flex; flex-direction: column; gap: 10px; }
            #register-form input { padding: 10px; border: 1px solid #e0e0e0; border-radius: 6px; }

            .users-table {
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }

            table {
                width: 100%;
                border-collapse: collapse;
            }

            table th {
                background: #f5f5f5;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 1px solid #e0e0e0;
            }

            table td {
                padding: 12px;
                border-bottom: 1px solid #e0e0e0;
            }

            .btn-delete { padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
            .btn-delete:hover { background: #c82333; }

            /* HISTORIAL */
            .history-container { display: flex; flex-direction: column; gap: 16px; }
            .history-card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .history-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #f0f0f0;
            }
            .history-header h3 { margin: 0; font-size: 18px; }
            .history-date { color: #666; font-size: 14px; }
            .history-garments { display: flex; flex-direction: column; gap: 8px; }
            .history-garment-item {
                padding: 8px 12px;
                background: #f8f9fa;
                border-radius: 4px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .color-badge {
                width: 24px;
                height: 24px;
                border-radius: 4px;
                border: 1px solid #ddd;
                display: inline-block;
            }

            /* ESTADÍSTICAS */
            .analytics-container { padding: 20px; }
            .analytics-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 40px;
            }
            .stat-card {
                background: white;
                border-radius: 8px;
                padding: 24px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-card.large .stat-number {
                font-size: 48px;
                font-weight: 700;
                color: #667eea;
                margin-bottom: 8px;
            }
            .stat-label {
                font-size: 16px;
                color: #666;
                font-weight: 500;
            }
            .analytics-section {
                background: white;
                border-radius: 8px;
                padding: 24px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .analytics-section h3 {
                margin-top: 0;
                margin-bottom: 20px;
                font-size: 18px;
                color: #333;
            }
            .stats-list { display: flex; flex-direction: column; gap: 16px; }
            .stat-item {
                display: grid;
                grid-template-columns: 30px 120px 1fr 50px;
                gap: 12px;
                align-items: center;
            }
            .rank {
                font-weight: 700;
                color: #667eea;
                font-size: 16px;
            }
            .stat-name {
                font-weight: 500;
                color: #333;
            }
            .stat-bar {
                height: 24px;
                background: #f0f0f0;
                border-radius: 4px;
                overflow: hidden;
            }
            .bar-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                transition: width 0.3s ease;
            }
            .stat-count {
                text-align: right;
                font-weight: 600;
                color: #667eea;
            }
            .colors-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 16px;
            }
            .color-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
            }
            .color-box {
                width: 60px;
                height: 60px;
                border-radius: 8px;
                border: 2px solid #ddd;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .color-box:hover { transform: scale(1.05); }
            .color-info { text-align: center; }
            .color-hex {
                font-weight: 600;
                font-family: monospace;
                color: #333;
            }
            .color-count {
                font-size: 12px;
                color: #666;
            }
            .distribution-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
            }
            .distribution-item {
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .distribution-label {
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
                font-weight: 500;
            }
            .distribution-number {
                font-size: 36px;
                font-weight: 700;
                color: #667eea;
            }

            /* HORAS DE USO */
            .hours-chart {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .hour-bar {
                display: grid;
                grid-template-columns: 60px 1fr 40px;
                gap: 12px;
                align-items: center;
            }
            .hour-label {
                font-weight: 600;
                color: #667eea;
                text-align: center;
                font-family: monospace;
            }
            .hour-fill-container {
                height: 30px;
                background: #f0f0f0;
                border-radius: 4px;
                overflow: hidden;
            }
            .hour-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                transition: width 0.3s ease;
            }
            .hour-count {
                text-align: right;
                font-weight: 600;
                color: #333;
                min-width: 40px;
            }

            @media (max-width: 1024px) {
                .user-layout { grid-template-columns: 1fr; }
                .user-layout .processed-section { grid-column: 1; }
                .users-container { grid-template-columns: 1fr; }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Configura panel de usuario
     */
    setupUserPanel() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.processedCanvas = document.getElementById('processed-canvas');

        document.getElementById('start-camera-btn').addEventListener('click', () => this.startCamera());
        document.getElementById('stop-camera-btn').addEventListener('click', () => this.stopCamera());
        document.getElementById('extract-btn').addEventListener('click', () => this.extractGarments());
        document.getElementById('download-btn').addEventListener('click', () => this.downloadGarments());
    }

    /**
     * Configura panel de admin
     */
    setupAdminPanel() {
        document.querySelectorAll('.nav-item').forEach(button => {
            button.addEventListener('click', (e) => {
                document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(tab => tab.classList.remove('active'));

                e.target.classList.add('active');
                const tabId = `tab-${e.target.dataset.tab}`;
                document.getElementById(tabId).classList.add('active');

                if (e.target.dataset.tab === 'users') {
                    this.loadUsers();
                } else if (e.target.dataset.tab === 'history') {
                    this.loadHistory();
                } else if (e.target.dataset.tab === 'analytics') {
                    this.loadAnalytics();
                }
            });
        });

        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.processedCanvas = document.getElementById('processed-canvas');

        document.getElementById('start-camera-btn').addEventListener('click', () => this.startCamera());
        document.getElementById('stop-camera-btn').addEventListener('click', () => this.stopCamera());
        document.getElementById('extract-btn').addEventListener('click', () => this.extractGarments());
        document.getElementById('download-btn').addEventListener('click', () => this.downloadGarments());

        document.getElementById('register-form').addEventListener('submit', (e) => this.handleRegister(e));
    }

    /**
     * Inicia la cámara
     */
    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });

            this.video.srcObject = this.stream;
            this.isRunning = true;

            document.getElementById('start-camera-btn').disabled = true;
            document.getElementById('stop-camera-btn').disabled = false;
            document.getElementById('extract-btn').disabled = false;

            this.processFrame();

        } catch (error) {
            alert('Error accediendo a la cámara: ' + error.message);
        }
    }

    /**
     * Detiene la cámara
     */
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }

        this.isRunning = false;

        document.getElementById('start-camera-btn').disabled = false;
        document.getElementById('stop-camera-btn').disabled = true;
        document.getElementById('extract-btn').disabled = true;
        // Mantener el botón de descarga habilitado si hay prendas guardadas
    }

    /**
     * Procesa frame del video
     */
    async processFrame() {
        if (!this.isRunning) return;

        // Verificar que el token esté disponible (puede haber sido limpiado)
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            console.error('❌ Token no disponible');
            return;
        }

        // Verificar que el video esté listo
        if (this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
            console.warn('⏳ Video no está listo aún');
            requestAnimationFrame(() => this.processFrame());
            return;
        }

        // Verificar dimensiones del video
        if (this.video.videoWidth === 0 || this.video.videoHeight === 0) {
            console.warn('⏳ Dimensiones del video aún no están disponibles');
            requestAnimationFrame(() => this.processFrame());
            return;
        }

        const startTime = performance.now();

        try {
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            const ctx = this.canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);

            // Crear blob de forma correcta
            const blob = await new Promise((resolve, reject) => {
                this.canvas.toBlob((blob) => {
                    if (blob) {
                        resolve(blob);
                    } else {
                        reject(new Error('canvas.toBlob devolvió null'));
                    }
                }, 'image/jpeg', 0.85);
            });

            const formData = new FormData();
            formData.append('file', blob, 'frame.jpg');

            console.log('✅ Enviando frame con token:', this.token.substring(0, 20) + '...');

            const response = await fetch(`${API_BASE_URL}/api/v1/procesar_frame`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Accept': 'application/json'
                },
                body: formData
            });

            console.log(`📨 Respuesta HTTP: ${response.status} ${response.statusText}`);

            if (!response.ok) {
                const errorData = await response.text();
                console.error(`❌ Error HTTP: ${errorData}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('📦 Datos recibidos:', {
                success: data.success,
                hasImage: !!data.image,
                persons_count: data.persons_count,
                imageLength: data.image ? data.image.substring(0, 50) + '...' : 'null'
            });

            if (data.image) {
                const img = new Image();
                img.onerror = () => console.error('❌ Error cargando imagen');
                img.onload = () => {
                    console.log(`✨ Imagen cargada: ${img.width}x${img.height}`);
                    this.processedCanvas.width = img.width;
                    this.processedCanvas.height = img.height;
                    const ctx = this.processedCanvas.getContext('2d');
                    ctx.drawImage(img, 0, 0);
                };
                // Backend ya envía el prefijo data:image/jpeg;base64, completo
                img.src = data.image;
            } else {
                console.warn('⚠️ No hay imagen en la respuesta');
            }

            const endTime = performance.now();
            this.latency = Math.round(endTime - startTime);
            this.frameCount++;

            if (performance.now() - this.lastTime >= 1000) {
                this.fps = this.frameCount;
                this.frameCount = 0;
                this.lastTime = performance.now();
                this.updateMetrics();
            }

        } catch (error) {
            console.error('❌ Error procesando frame:', error.message);
        }

        requestAnimationFrame(() => this.processFrame());
    }

    /**
     * Actualiza métricas
     */
    updateMetrics() {
        const fpsEl = document.getElementById('fps-display');
        const latencyEl = document.getElementById('latency-display');

        if (fpsEl) fpsEl.textContent = `FPS: ${this.fps}`;
        if (latencyEl) latencyEl.textContent = `Latencia: ${this.latency} ms`;
    }

    /**
     * Extrae prendas
     */
    async extractGarments() {
        // Verificar que el token esté disponible
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            alert('❌ Token no disponible. Por favor, vuelve a iniciar sesión');
            return;
        }

        try {
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            const ctx = this.canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);

            // Crear blob de forma correcta
            const blob = await new Promise((resolve, reject) => {
                this.canvas.toBlob(resolve, 'image/jpeg', 0.85);
            });

            if (!blob) {
                throw new Error('No se pudo crear blob del canvas');
            }

            const formData = new FormData();
            formData.append('file', blob, 'frame.jpg');

            const response = await fetch(`${API_BASE_URL}/api/v1/extraer_prendas`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.token}` },
                body: formData
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();

            this.renderGarments(data.persons || []);

            // ✅ Habilitar botón de descarga después de extraer prendas
            const downloadBtn = document.getElementById('download-btn');
            if (downloadBtn) {
                downloadBtn.disabled = false;
            }

        } catch (error) {
            console.error('Error extrayendo prendas:', error);
            alert('Error extrayendo prendas: ' + error.message);
        }
    }

    /**
     * Descarga las prendas extraídas en ZIP
     */
    async downloadGarments() {
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            alert('❌ Token no disponible. Por favor, vuelve a iniciar sesión');
            return;
        }

        try {
            const downloadBtn = document.getElementById('download-btn');
            downloadBtn.disabled = true;
            downloadBtn.textContent = '⏳ Descargando...';

            const response = await fetch(`${API_BASE_URL}/api/v1/descargar_prendas`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error descargando prendas');
            }

            // Obtener el blob del ZIP
            const blob = await response.blob();

            // Crear URL descargable
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `prendas_extraidas_${new Date().toISOString().split('T')[0]}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            console.log('✅ Descarga completada');

        } catch (error) {
            console.error('Error descargando:', error);
            alert('Error descargando prendas: ' + error.message);
        } finally {
            const downloadBtn = document.getElementById('download-btn');
            downloadBtn.disabled = false;
            downloadBtn.textContent = '⬇️ Descargar';
        }
    }

    /**
     * Renderiza prendas extraídas
     */
    renderGarments(persons) {
        const grid = document.getElementById('garments-grid');
        grid.innerHTML = '';

        if (!persons || persons.length === 0) {
            grid.innerHTML = '<p class="placeholder">No se detectaron personas</p>';
            return;
        }

        persons.forEach((person) => {
            if (!person.prendas) return;

            Object.entries(person.prendas).forEach(([garmentName, base64Data]) => {
                // El backend retorna el base64 directamente, no en un objeto
                // Saltar si es null o undefined
                if (!base64Data) return;

                const card = document.createElement('div');
                card.className = 'garment-card';

                card.innerHTML = `
                    <img src="data:image/png;base64,${base64Data}"
                         alt="${garmentName}"
                         class="garment-image"
                    >
                    <div class="garment-info">
                        <div class="garment-name">${garmentName}</div>
                    </div>
                `;

                grid.appendChild(card);
            });
        });
    }

    /**
     * Carga historial de extracciones (admin)
     */
    async loadHistory() {
        const container = document.getElementById('history-container');
        container.innerHTML = '<p class="placeholder">Cargando historial...</p>';

        // Verificar token
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            container.innerHTML = '<p class="placeholder">❌ Error: Token no disponible</p>';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/historial`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (!response.ok) throw new Error('Error cargando historial');

            const result = await response.json();
            const history = result.data || [];

            if (history.length === 0) {
                container.innerHTML = '<p class="placeholder">No hay extracciones en el historial</p>';
                return;
            }

            // Renderizar historial en formato de cards con imágenes y detalles
            container.innerHTML = history.map((item, idx) => {
                const fecha = new Date(item.timestamp).toLocaleString('es-ES');
                const prendas = item.prendas || {};
                const personaFolder = item.imagen_entrada_path ?
                    item.imagen_entrada_path.substring(0, item.imagen_entrada_path.lastIndexOf('/')) :
                    `extracted_garments/persona_${item.persona_id}`;

                return `
                    <div class="history-card">
                        <div class="history-header">
                            <div class="header-info">
                                <h3>👤 PersonaID: ${item.persona_id}</h3>
                                <p class="folder-path">📁 ${personaFolder}</p>
                                <span class="history-date">📅 ${fecha}</span>
                            </div>
                        </div>

                        ${item.imagen_entrada_path ? `
                            <div class="history-segmented-section">
                                <h4>📷 Imagen de entrada</h4>
                                <div class="segmented-image-wrapper">
                                    <img id="seg-img-${item.persona_id}" class="history-image" alt="Imagen de entrada" />
                                </div>
                                <div class="segmented-controls">
                                    <p><strong>Ruta:</strong> <code>${item.imagen_entrada_path}</code></p>
                                    <button class="copy-btn" data-path="${item.imagen_entrada_path}">📋 Copiar Ruta</button>
                                </div>
                            </div>
                        ` : ''}

                        <div class="history-garments-section">
                            <h4>👕 Prendas Detectadas</h4>
                            <div class="garments-grid">
                                ${Object.entries(prendas).map(([name, data], gidx) => {
                                    if (!data || !data.imagen_path) return '';
                                    const uniqueId = `garment-${item.persona_id}-${gidx}`;
                                    return `
                                        <div class="garment-card">
                                            <div class="garment-header">
                                                <h5>${name.charAt(0).toUpperCase() + name.slice(1)}</h5>
                                                ${data.color_hex ? `
                                                    <span class="color-badge" style="background: ${data.color_hex}" title="Color: ${data.color_hex}"></span>
                                                ` : ''}
                                            </div>
                                            <div class="garment-details">
                                                <p><strong>Color:</strong> ${data.color_hex || 'N/A'}</p>
                                                <p><strong>Archivo:</strong> <code>${data.imagen_path.split('/').pop()}</code></p>
                                                <p><strong>Ruta:</strong> <code>${data.imagen_path}</code></p>
                                                <button class="copy-btn" data-path="${data.imagen_path}">📋 Copiar Ruta</button>
                                            </div>
                                            <div class="garment-image-wrapper">
                                                <img id="${uniqueId}" class="garment-image" alt="${name}" />
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // Cargar imágenes de entrada
            for (const item of history) {
                if (item.imagen_entrada_path) {
                    this.loadHistoryImage(`seg-img-${item.persona_id}`, item.imagen_entrada_path);
                }
            }

            // Cargar imágenes de prendas
            for (const item of history) {
                const prendas = item.prendas || {};
                Object.entries(prendas).forEach(([name, data], gidx) => {
                    if (data && data.imagen_path) {
                        const uniqueId = `garment-${item.persona_id}-${gidx}`;
                        this.loadHistoryImage(`${uniqueId}`, data.imagen_path);
                    }
                });
            }

            // Inicializar botones de copiar ruta
            const copyButtons = container.querySelectorAll('.copy-btn');
            copyButtons.forEach(btn => {
                btn.addEventListener('click', async () => {
                    const path = btn.dataset.path;
                    try {
                        await navigator.clipboard.writeText(path);
                        const prev = btn.textContent;
                        btn.textContent = '✅ Copiado';
                        setTimeout(() => btn.textContent = prev, 1500);
                    } catch (e) {
                        console.error('Error copiando ruta:', e);
                        btn.textContent = '❌ Error';
                        setTimeout(() => btn.textContent = '📋 Copiar Ruta', 1500);
                    }
                });
            });

        } catch (error) {
            console.error('Error cargando historial:', error);
            container.innerHTML = '<p class="placeholder">❌ Error cargando historial</p>';
        }
    }

    async loadHistoryImage(elementId, imagePath) {
        const imgElement = document.getElementById(elementId);
        if (!imgElement || !this.token) {
            console.warn(`loadHistoryImage: No se encontró elemento ${elementId} o token no disponible`);
            return;
        }

        console.log(`📥 Cargando imagen: ${elementId} desde ${imagePath}`);

        try {
            const response = await fetch(
                `${API_BASE_URL}/api/v1/imagen-guardada?archivo=${encodeURIComponent(imagePath)}`,
                { headers: { 'Authorization': `Bearer ${this.token}` } }
            );

            if (response.ok) {
                const result = await response.json();
                imgElement.src = result.image;
                imgElement.style.display = 'block';
                imgElement.style.visibility = 'visible';
                imgElement.style.opacity = '1';
                console.log(`✅ Imagen cargada: ${elementId}`);
            } else {
                const errorText = await response.text();
                console.error(`❌ Error ${response.status} cargando ${elementId}: ${errorText}`);
                console.error(`   Ruta solicitada: ${imagePath}`);
                imgElement.alt = '❌ Imagen no encontrada';
                imgElement.style.display = 'none';

                // Solo remover sección si es imagen segmentada/entrada
                if (elementId.startsWith('seg-img-')) {
                    const section = imgElement.closest('.history-segmented-section');
                    if (section) section.remove();
                }
            }
        } catch (error) {
            console.error(`❌ Excepción cargando imagen ${elementId}:`, error);
            console.error(`   Ruta: ${imagePath}`);
            imgElement.alt = '❌ Error cargando imagen';
            imgElement.style.display = 'none';

            // Solo remover sección si es imagen segmentada/entrada
            if (elementId.startsWith('seg-img-')) {
                const section = imgElement.closest('.history-segmented-section');
                if (section) section.remove();
            }
        }
    }

    /**
     * Carga estadísticas (admin)
     */
    async loadAnalytics() {
        const container = document.getElementById('analytics-container');
        container.innerHTML = '<p class="placeholder">Cargando estadísticas...</p>';

        // Verificar token
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            container.innerHTML = '<p class="placeholder">❌ Error: Token no disponible</p>';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/estadisticas`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (!response.ok) throw new Error('Error cargando estadísticas');

            const result = await response.json();
            const stats = result.data || {};

            const {
                total_extracciones = 0,
                personas_unicas = 0,
                prendas_frecuentes = [],
                colores_frecuentes = [],
                horas_uso = []
            } = stats;

            // Renderizar estadísticas
            const html = `
                <div class="analytics-grid">
                    <div class="stat-card large">
                        <div class="stat-number">${total_extracciones}</div>
                        <div class="stat-label">Total de Extracciones</div>
                    </div>

                    <div class="stat-card large">
                        <div class="stat-number">${personas_unicas}</div>
                        <div class="stat-label">Personas Únicas</div>
                    </div>
                </div>

                <div class="analytics-section">
                    <h3>👕 Prendas Más Detectadas</h3>
                    <div class="stats-list">
                        ${prendas_frecuentes.length === 0
                            ? '<p class="placeholder">Sin datos</p>'
                            : prendas_frecuentes.map((prenda, idx) => `
                                <div class="stat-item">
                                    <div class="rank">${idx + 1}.</div>
                                    <div class="stat-name">${prenda.name}</div>
                                    <div class="stat-bar">
                                        <div class="bar-fill" style="width: ${(prenda.count / Math.max(...prendas_frecuentes.map(p => p.count), 1)) * 100}%"></div>
                                    </div>
                                    <div class="stat-count">${prenda.count}</div>
                                </div>
                            `).join('')
                        }
                    </div>
                </div>

                <div class="analytics-section">
                    <h3>🎨 Colores Más Frecuentes</h3>
                    <div class="colors-grid">
                        ${colores_frecuentes.length === 0
                            ? '<p class="placeholder">Sin datos</p>'
                            : colores_frecuentes.map(color => `
                                <div class="color-item">
                                    <div class="color-box" style="background-color: ${color.color};" title="${color.color}"></div>
                                    <div class="color-info">
                                        <div class="color-hex">${color.color}</div>
                                        <div class="color-count">${color.count} veces</div>
                                    </div>
                                </div>
                            `).join('')
                        }
                    </div>
                </div>

                <div class="analytics-section">
                    <h3>⏰ Horas de Máximo Uso del Sistema</h3>
                    <div class="hours-chart">
                        ${horas_uso.length === 0
                            ? '<p class="placeholder">Sin datos</p>'
                            : horas_uso.map(hour => {
                                const maxCount = Math.max(...horas_uso.map(h => h.count), 1);
                                const percentage = (hour.count / maxCount) * 100;
                                return `
                                    <div class="hour-bar">
                                        <div class="hour-label">${hour.hora}</div>
                                        <div class="hour-fill-container">
                                            <div class="hour-fill" style="width: ${percentage}%"></div>
                                        </div>
                                        <div class="hour-count">${hour.count}</div>
                                    </div>
                                `;
                            }).join('')
                        }
                    </div>
                </div>
            `;

            container.innerHTML = html;

        } catch (error) {
            console.error('Error cargando estadísticas:', error);
            container.innerHTML = '<p class="placeholder">❌ Error cargando estadísticas</p>';
        }
    }

    /**
     * Carga lista de usuarios (admin)
     */
    async loadUsers() {
        const container = document.getElementById('users-list-container');
        container.innerHTML = '<p class="placeholder">Cargando usuarios...</p>';

        // Verificar token
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            container.innerHTML = '<p class="placeholder">❌ Error: Token no disponible</p>';
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/api/users`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (!response.ok) throw new Error('Error cargando usuarios');

            const users = await response.json();

            if (users.length === 0) {
                container.innerHTML = '<p class="placeholder">No hay usuarios</p>';
                return;
            }

            let html = `
                <table>
                    <thead>
                        <tr>
                            <th>Usuario</th>
                            <th>Rol</th>
                            <th>Creado</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            users.forEach(user => {
                const createdDate = new Date(user.created_at).toLocaleDateString();
                html += `
                    <tr>
                        <td>${user.username}</td>
                        <td><span class="role-badge ${user.role}">${user.role}</span></td>
                        <td>${createdDate}</td>
                        <td>
                            ${user.username !== this.username ?
                                `<button class="btn-delete" data-username="${user.username}">🗑️</button>`
                                : ''}
                        </td>
                    </tr>
                `;
            });

            html += `</tbody></table>`;
            container.innerHTML = html;

            document.querySelectorAll('.btn-delete').forEach(btn => {
                btn.addEventListener('click', (e) => this.deleteUser(e.target.dataset.username));
            });

        } catch (error) {
            container.innerHTML = `<p class="placeholder">Error: ${error.message}</p>`;
        }
    }

    /**
     * Maneja registro de nuevos usuarios (admin)
     */
    async handleRegister(event) {
        event.preventDefault();

        const username = document.getElementById('new-username').value;
        const password = document.getElementById('new-password').value;

        // Verificar token
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            alert('❌ Token no disponible. Por favor, vuelve a iniciar sesión');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error creando usuario');
            }

            alert('✅ Usuario creado exitosamente');
            document.getElementById('register-form').reset();
            this.loadUsers();

        } catch (error) {
            alert('❌ Error: ' + error.message);
        }
    }

    /**
     * Elimina un usuario (admin)
     */
    async deleteUser(username) {
        if (!confirm(`¿Eliminar usuario "${username}"?`)) return;

        // Verificar token
        if (!this.token) {
            this.token = localStorage.getItem('token');
        }

        if (!this.token) {
            alert('❌ Token no disponible');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/users/${username}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error eliminando usuario');
            }

            alert('✅ Usuario eliminado');
            this.loadUsers();

        } catch (error) {
            alert('❌ Error: ' + error.message);
        }
    }

    /**
     * Cierra sesión
     */
    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('userRole');
        localStorage.removeItem('username');

        this.token = null;
        this.userRole = null;
        this.username = null;

        this.init();
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new SegmentationApp();
});
