// Enhanced Crisis Navigator JavaScript - Complete Implementation
class CrisisNavigator {
    constructor() {
        this.map = null;
        this.layers = {
            reports: null,
            shelters: null,
            alerts: null,
            userLocation: null
        };
        this.markers = {
            reports: [],
            shelters: [],
            alerts: []
        };
        this.userLocation = null;
        this.isLoading = false;
        this.lastUpdate = null;
        this.refreshInterval = null;
        this.notifications = [];
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeMap();
        this.startAutoRefresh();
        this.setupNotificationSystem();
        this.animateOnLoad();
    }

    // Initialize map with enhanced styling
    initializeMap() {
        try {
            this.map = L.map('map', {
                center: [39.8283, -98.5795],
                zoom: 4,
                zoomControl: false,
                attributionControl: false,
                fadeAnimation: true,
                zoomAnimation: true
            });

            // Add custom zoom control
            L.control.zoom({
                position: 'topright'
            }).addTo(this.map);

            // Add dark theme tile layer
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '© OpenStreetMap contributors, © CARTO',
                maxZoom: 19,
                subdomains: 'abcd'
            }).addTo(this.map);

            // Initialize layer groups
            this.layers.reports = L.layerGroup().addTo(this.map);
            this.layers.shelters = L.layerGroup().addTo(this.map);
            this.layers.alerts = L.layerGroup().addTo(this.map);
            this.layers.userLocation = L.layerGroup().addTo(this.map);

            // Load initial data
            this.loadAllData();
            this.getUserLocation();

            this.showNotification('Map initialized successfully', 'success');
        } catch (error) {
            console.error('Map initialization failed:', error);
            this.showNotification('Failed to initialize map', 'error');
        }
    }

    // Setup event listeners
    setupEventListeners() {
        // Layer toggle controls
        document.getElementById('showReports')?.addEventListener('change', (e) => {
            this.toggleLayer('reports', e.target.checked);
        });

        document.getElementById('showShelters')?.addEventListener('change', (e) => {
            this.toggleLayer('shelters', e.target.checked);
        });

        document.getElementById('showAlerts')?.addEventListener('change', (e) => {
            this.toggleLayer('alerts', e.target.checked);
        });

        // Refresh button
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.refreshData();
        });

        // Emergency report form
        document.getElementById('emergencyForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitEmergencyReport();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'r') {
                e.preventDefault();
                this.refreshData();
            }
            if (e.key === 'l') {
                this.centerOnUser();
            }
        });
    }

    // Get user's current location
    getUserLocation() {
        if (!navigator.geolocation) {
            this.showNotification('Geolocation not supported', 'warning');
            return;
        }

        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000
        };

        navigator.geolocation.getCurrentPosition(
            (position) => this.onLocationSuccess(position),
            (error) => this.onLocationError(error),
            options
        );
    }

    onLocationSuccess(position) {
        const { latitude, longitude } = position.coords;
        this.userLocation = [latitude, longitude];

        this.layers.userLocation.clearLayers();

        const userMarker = L.marker([latitude, longitude], {
            icon: L.divIcon({
                className: 'user-location-marker',
                html: `
                    <div style="position: relative;">
                        <div style="
                            width: 20px; height: 20px; 
                            background: #00ADB5; 
                            border-radius: 50%; 
                            border: 3px solid white;
                            box-shadow: 0 2px 10px rgba(0,173,181,0.5);
                            animation: userPulse 2s infinite;
                        "></div>
                        <div style="
                            position: absolute; top: -5px; left: -5px;
                            width: 30px; height: 30px;
                            border: 2px solid #00ADB5;
                            border-radius: 50%;
                            animation: userRipple 2s infinite;
                            opacity: 0.6;
                        "></div>
                    </div>
                `,
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            }),
            zIndexOffset: 1000
        });

        const popupContent = `
            <div style="padding: 10px; text-align: center;">
                <h6 style="color: #00ADB5; margin-bottom: 10px;">
                    <i class="fas fa-map-marker-alt"></i> Your Location
                </h6>
                <p style="margin: 5px 0; font-size: 12px;">
                    ${latitude.toFixed(6)}, ${longitude.toFixed(6)}
                </p>
                <button onclick="crisisNav.centerOnUser()" 
                        style="
                            background: #00ADB5; color: white; border: none;
                            padding: 5px 10px; border-radius: 5px; cursor: pointer;
                            font-size: 12px; margin-top: 5px;
                        ">
                    <i class="fas fa-crosshairs"></i> Recenter
                </button>
            </div>
        `;

        userMarker.bindPopup(popupContent);
        this.layers.userLocation.addLayer(userMarker);

        this.map.flyTo([latitude, longitude], 12, {
            duration: 2,
            easeLinearity: 0.5
        });

        this.showNotification('Location found successfully', 'success');
        this.updateStatistics('userLocation', 'Found');
    }

    onLocationError(error) {
        let message = 'Location access denied';
        switch (error.code) {
            case error.PERMISSION_DENIED:
                message = 'Location permission denied';
                break;
            case error.POSITION_UNAVAILABLE:
                message = 'Location information unavailable';
                break;
            case error.TIMEOUT:
                message = 'Location request timed out';
                break;
        }
        
        this.showNotification(message, 'warning');
        this.updateStatistics('userLocation', 'Failed');
    }

    // Load all data with loading states
    async loadAllData() {
        if (this.isLoading) return;
        
        this.setLoadingState(true);
        
        try {
            await Promise.all([
                this.loadReports(),
                this.loadShelters(),
                this.loadAlerts()
            ]);
            
            this.lastUpdate = new Date();
            this.updateStatistics('lastUpdate', this.formatTime(this.lastUpdate));
        } catch (error) {
            console.error('Data loading failed:', error);
            this.showNotification('Failed to load data', 'error');
        } finally {
            this.setLoadingState(false);
        }
    }

    // Load emergency reports
    async loadReports() {
        try {
            // Simulate API call for demo
            const reports = await this.simulateApiCall('/api/reports', [
                {
                    id: 1,
                    title: 'Building Fire',
                    description: 'Large fire reported at downtown office building',
                    severity: 'critical',
                    latitude: 40.7128,
                    longitude: -74.0060,
                    location: 'Manhattan, NY',
                    created_at: new Date().toISOString()
                },
                {
                    id: 2,
                    title: 'Road Closure',
                    description: 'Highway 95 closed due to accident',
                    severity: 'medium',
                    latitude: 39.9526,
                    longitude: -75.1652,
                    location: 'Philadelphia, PA',
                    created_at: new Date().toISOString()
                }
            ]);
            
            this.layers.reports.clearLayers();
            this.markers.reports = [];
            
            reports.forEach(report => {
                if (report.latitude && report.longitude) {
                    const marker = this.createReportMarker(report);
                    this.layers.reports.addLayer(marker);
                    this.markers.reports.push(marker);
                }
            });
            
            this.updateStatistics('reportCount', reports.length);
            
        } catch (error) {
            console.error('Error loading reports:', error);
            this.updateStatistics('reportCount', 'Error');
        }
    }

    // Load emergency shelters
    async loadShelters() {
        try {
            const shelters = await this.simulateApiCall('/api/shelters', [
                {
                    id: 1,
                    name: 'Red Cross Emergency Shelter',
                    address: '123 Main St, Boston, MA',
                    latitude: 42.3601,
                    longitude: -71.0589,
                    capacity: 200,
                    current_occupancy: 85,
                    contact_phone: '(555) 123-4567',
                    shelter_type: 'emergency'
                },
                {
                    id: 2,
                    name: 'Community Center Shelter',
                    address: '456 Oak Ave, Seattle, WA',
                    latitude: 47.6062,
                    longitude: -122.3321,
                    capacity: 150,
                    current_occupancy: 45,
                    contact_phone: '(555) 987-6543',
                    shelter_type: 'temporary'
                }
            ]);
            
            this.layers.shelters.clearLayers();
            this.markers.shelters = [];
            
            shelters.forEach(shelter => {
                const marker = this.createShelterMarker(shelter);
                this.layers.shelters.addLayer(marker);
                this.markers.shelters.push(marker);
            });
            
            this.updateStatistics('shelterCount', shelters.length);
            
        } catch (error) {
            console.error('Error loading shelters:', error);
            this.updateStatistics('shelterCount', 'Error');
        }
    }

    // Load active alerts
    async loadAlerts() {
        try {
            const alerts = await this.simulateApiCall('/api/alerts', [
                {
                    id: 1,
                    title: 'Severe Weather Warning',
                    description: 'Tornado warning in effect until 8 PM',
                    severity: 'critical',
                    latitude: 35.2271,
                    longitude: -80.8431,
                    location: 'Charlotte, NC',
                    radius: 5,
                    alert_type: 'weather',
                    created_at: new Date().toISOString(),
                    expires_at: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString()
                }
            ]);
            
            this.layers.alerts.clearLayers();
            this.markers.alerts = [];
            
            alerts.forEach(alert => {
                if (alert.latitude && alert.longitude) {
                    const circle = this.createAlertCircle(alert);
                    this.layers.alerts.addLayer(circle);
                    this.markers.alerts.push(circle);
                }
            });
            
            this.updateStatistics('alertCount', alerts.length);
            
        } catch (error) {
            console.error('Error loading alerts:', error);
            this.updateStatistics('alertCount', 'Error');
        }
    }

    // Create enhanced report marker
    createReportMarker(report) {
        const color = this.getSeverityColor(report.severity);
        
        const marker = L.marker([report.latitude, report.longitude], {
            icon: L.divIcon({
                className: 'report-marker',
                html: `
                    <div style="position: relative;">
                        <div style="
                            width: 25px; height: 25px; 
                            background: ${color}; 
                            border-radius: 50%; 
                            display: flex; align-items: center; justify-content: center;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                            border: 2px solid white;
                            animation: ${report.severity === 'critical' ? 'criticalPulse 1s infinite' : 'none'};
                        ">
                            <i class="fas fa-exclamation-triangle" style="color: white; font-size: 12px;"></i>
                        </div>
                    </div>
                `,
                iconSize: [25, 25],
                iconAnchor: [12, 12]
            })
        });

        const popupContent = `
            <div style="padding: 15px; max-width: 250px;">
                <h6 style="color: ${color}; margin-bottom: 10px; font-weight: bold;">
                    ${report.title}
                </h6>
                <p style="margin-bottom: 10px; font-size: 14px; line-height: 1.4;">
                    ${report.description}
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="
                        background: ${color}; color: white; 
                        padding: 3px 8px; border-radius: 12px; 
                        font-size: 11px; font-weight: bold; text-transform: uppercase;
                    ">
                        ${report.severity}
                    </span>
                    <small style="color: #666;">
                        ${this.formatTime(new Date(report.created_at))}
                    </small>
                </div>
                <div style="font-size: 12px; color: #666;">
                    <i class="fas fa-map-marker-alt"></i> ${report.location || 'Location not specified'}
                </div>
            </div>
        `;
        
        marker.bindPopup(popupContent, { maxWidth: 300 });
        return marker;
    }

    // Create enhanced shelter marker
    createShelterMarker(shelter) {
        const occupancyPercent = shelter.capacity ? 
            Math.round((shelter.current_occupancy / shelter.capacity) * 100) : 0;
        const available = shelter.capacity - shelter.current_occupancy;
        const color = available > 50 ? '#198754' : available > 20 ? '#fd7e14' : '#dc3545';
        
        const marker = L.marker([shelter.latitude, shelter.longitude], {
            icon: L.divIcon({
                className: 'shelter-marker',
                html: `
                    <div style="
                        width: 25px; height: 25px; 
                        background: ${color}; 
                        border-radius: 50%; 
                        display: flex; align-items: center; justify-content: center;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                        border: 2px solid white;
                    ">
                        <i class="fas fa-home" style="color: white; font-size: 12px;"></i>
                    </div>
                `,
                iconSize: [25, 25],
                iconAnchor: [12, 12]
            })
        });

        const popupContent = `
            <div style="padding: 15px; max-width: 280px;">
                <h6 style="color: ${color}; margin-bottom: 10px; font-weight: bold;">
                    ${shelter.name}
                </h6>
                <p style="margin-bottom: 10px; font-size: 14px;">
                    ${shelter.address}
                </p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; text-align: center;">
                    <div style="background: #f8f9fa; padding: 8px; border-radius: 8px;">
                        <div style="font-size: 12px; color: #666;">Capacity</div>
                        <div style="font-weight: bold; color: #333;">${shelter.capacity || 'N/A'}</div>
                    </div>
                    <div style="background: #f8f9fa; padding: 8px; border-radius: 8px;">
                        <div style="font-size: 12px; color: #666;">Available</div>
                        <div style="font-weight: bold; color: ${color};">${available}</div>
                    </div>
                </div>
                ${shelter.contact_phone ? `
                    <div style="margin-bottom: 10px; font-size: 12px;">
                        <i class="fas fa-phone" style="margin-right: 5px;"></i>
                        <a href="tel:${shelter.contact_phone}" style="color: #00ADB5; text-decoration: none;">
                            ${shelter.contact_phone}
                        </a>
                    </div>
                ` : ''}
                <div>
                    <span style="
                        background: ${color}; color: white; 
                        padding: 3px 8px; border-radius: 12px; 
                        font-size: 11px; font-weight: bold; text-transform: uppercase;
                    ">
                        ${shelter.shelter_type || 'SHELTER'}
                    </span>
                </div>
            </div>
        `;
        
        marker.bindPopup(popupContent, { maxWidth: 300 });
        return marker;
    }

    // Create enhanced alert circle
    createAlertCircle(alert) {
        const color = this.getSeverityColor(alert.severity);
        const radius = (alert.radius || 1) * 1000;
        
        const circle = L.circle([alert.latitude, alert.longitude], {
            color: color,
            fillColor: color,
            fillOpacity: 0.2,
            radius: radius,
            weight: 3,
            opacity: 0.8
        });

        // Add pulsing animation for critical alerts
        if (alert.severity === 'critical') {
            setInterval(() => {
                circle.setStyle({ fillOpacity: circle.options.fillOpacity === 0.2 ? 0.4 : 0.2 });
            }, 1000);
        }
        
        const popupContent = `
            <div style="padding: 15px; max-width: 280px;">
                <h6 style="color: ${color}; margin-bottom: 10px; font-weight: bold;">
                    ${alert.title}
                </h6>
                <p style="margin-bottom: 10px; font-size: 14px; line-height: 1.4;">
                    ${alert.description}
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="
                        background: ${color}; color: white; 
                        padding: 3px 8px; border-radius: 12px; 
                        font-size: 11px; font-weight: bold; text-transform: uppercase;
                    ">
                        ${alert.severity}
                    </span>
                    <span style="
                        background: #6c757d; color: white; 
                        padding: 3px 8px; border-radius: 12px; 
                        font-size: 11px; font-weight: bold; text-transform: uppercase;
                    ">
                        ${alert.alert_type || 'ALERT'}
                    </span>
                </div>
                <div style="font-size: 12px; color: #666; line-height: 1.4;">
                    <div style="margin-bottom: 3px;">
                        <i class="fas fa-map-marker-alt"></i> ${alert.location || 'Area alert'}
                    </div>
                    <div style="margin-bottom: 3px;">
                        <i class="fas fa-clock"></i> Active since ${this.formatTime(new Date(alert.created_at))}
                    </div>
                    ${alert.expires_at ? `
                        <div>
                            <i class="fas fa-hourglass-end"></i> Expires ${this.formatTime(new Date(alert.expires_at))}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        circle.bindPopup(popupContent, { maxWidth: 300 });
        return circle;
    }

    // Utility methods
    getSeverityColor(severity) {
        switch (severity?.toLowerCase()) {
            case 'critical': return '#dc3545';
            case 'high': return '#fd7e14';
            case 'medium': return '#0dcaf0';
            case 'low': return '#198754';
            default: return '#6c757d';
        }
    }

    formatTime(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    // Toggle layer visibility
    toggleLayer(layerName, show) {
        const layer = this.layers[layerName];
        if (!layer) return;

        if (show) {
            if (!this.map.hasLayer(layer)) {
                this.map.addLayer(layer);
            }
        } else {
            if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        }
    }

    // Center map on user location
    centerOnUser() {
        if (this.userLocation) {
            this.map.flyTo(this.userLocation, 12, {
                duration: 1.5,
                easeLinearity: 0.3
            });
        } else {
            this.showNotification('User location not available', 'warning');
        }
    }

    // Refresh data
    refreshData() {
        this.loadAllData();
        this.showNotification('Data refreshed', 'success');
    }

    // Set loading state
    setLoadingState(loading) {
        this.isLoading = loading;
        const refreshBtn = document.getElementById('refreshBtn');
        
        if (refreshBtn) {
            if (loading) {
                refreshBtn.disabled = true;
                refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            } else {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
            }
        }
    }

    // Update statistics display
    updateStatistics(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    // Show notification
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} show`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; color: inherit; cursor: pointer; margin-left: auto;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'error': return 'exclamation-circle';
            case 'warning': return 'exclamation-triangle';
            default: return 'info-circle';
        }
    }

    // Start auto-refresh
    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadAllData();
        }, 30000); // 30 seconds
    }

    // Stop auto-refresh
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Simulate API call for demo
    async simulateApiCall(url, data) {
        return new Promise((resolve) => {
            setTimeout(() => resolve(data), Math.random() * 1000 + 500);
        });
    }

    // Animate elements on load
    animateOnLoad() {
        const elements = document.querySelectorAll('.status-card, .sidebar-section, .map-container');
        elements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                el.style.transition = 'all 0.6s ease-out';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }

    // Submit emergency report
    submitEmergencyReport() {
        const form = document.getElementById('emergencyForm');
        if (!form) return;

        const formData = new FormData(form);
        const report = {
            title: formData.get('title'),
            description: formData.get('description'),
            severity: formData.get('severity'),
            location: formData.get('location')
        };

        // Add user location if available
        if (this.userLocation) {
            report.latitude = this.userLocation[0];
            report.longitude = this.userLocation[1];
        }

        // Simulate submission
        this.setLoadingState(true);
        setTimeout(() => {
            this.setLoadingState(false);
            this.showNotification('Emergency report submitted successfully', 'success');
            form.reset();
        }, 2000);
    }
}

// Add required CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes userPulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.1); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }
    
    @keyframes userRipple {
        0% { transform: scale(1); opacity: 0.6; }
        100% { transform: scale(2); opacity: 0; }
    }
    
    @keyframes criticalPulse {
        0% { box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        50% { box-shadow: 0 2px 20px rgba(220,53,69,0.8); }
        100% { box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
    }
    
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(57, 62, 70, 0.95);
        backdrop-filter: blur(20px);
        color: #EEEEEE;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        transform: translateX(400px);
        transition: transform 0.3s ease-out;
        border-left: 4px solid #00ADB5;
        min-width: 300px;
    }
    
    .notification.show {
        transform: translateX(0);
    }
    
    .notification-success {
        border-left-color: #198754;
    }
    
    .notification-error {
        border-left-color: #dc3545;
    }
    
    .notification-warning {
        border-left-color: #fd7e14;
    }
`;
document.head.appendChild(style);

// Initialize the Crisis Navigator when DOM is loaded
let crisisNav;
document.addEventListener('DOMContentLoaded', function() {
    crisisNav = new CrisisNavigator();
});

// Global functions for button clicks
window.refreshMap = () => crisisNav?.refreshData();
window.centerOnUser = () => crisisNav?.centerOnUser();