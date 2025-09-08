import os
import logging
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from app import app, db
import models
from gemini_service import analyze_emergency_report, analyze_emergency_image, generate_emergency_summary
from sms_service import send_emergency_sms, send_bulk_emergency_alerts
from translation_service import translate_emergency_text, get_multilingual_emergency_message, detect_and_translate_user_input
from analytics_service import analyze_emergency_trends, predict_emergency_risk, generate_emergency_insights_dashboard
try:
    from slack_integration import send_emergency_to_slack, get_slack_integration_status
except Exception:
    # Fallbacks when Slack not configured
    def send_emergency_to_slack(_):
        return False
    def get_slack_integration_status():
        return {"enabled": False, "status": "Not configured"}
from local_notifications import notify_emergency_locally
from crisis_monitoring import create_automatic_alerts_from_monitoring, generate_crisis_monitoring_report
from datetime import datetime

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        location = request.form['location']
        password = request.form['password']
        
        # Check if user already exists
        if models.User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if models.User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user = models.User()
        user.username = username
        user.email = email
        user.phone = phone
        user.location = location
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            flash('Registration successful!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = models.User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    user = models.User.query.get(session['user_id'])
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('login'))
    
    # Get user's reports
    user_reports = models.EmergencyReport.query.filter_by(user_id=user.id).order_by(models.EmergencyReport.created_at.desc()).limit(10).all()
    
    # Get recent alerts
    recent_alerts = models.Alert.query.filter_by(active=True).order_by(models.Alert.created_at.desc()).limit(5).all()
    
    # Generate AI summary if there are reports
    ai_summary = generate_emergency_summary(user_reports) if user_reports else "No recent reports to summarize."
    
    return render_template('dashboard.html', 
                         user=user, 
                         reports=user_reports, 
                         alerts=recent_alerts,
                         ai_summary=ai_summary)

@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        flash('Please log in to submit a report', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        # Convert coordinates to float if provided
        try:
            latitude = float(latitude) if latitude else None
            longitude = float(longitude) if longitude else None
        except ValueError:
            latitude = longitude = None
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_path = file_path
        
        # Analyze the report with Gemini AI
        try:
            analysis = analyze_emergency_report(description, location)
            ai_analysis = f"Severity: {analysis.severity.upper()}\n"
            ai_analysis += f"Category: {analysis.category.title()}\n"
            ai_analysis += f"Urgency: {analysis.urgency.title()}\n"
            ai_analysis += f"Recommendations: {', '.join(analysis.recommendations)}\n"
            ai_analysis += f"Estimated Response Time: {analysis.estimated_response_time}"
            
            # Analyze image if provided
            if image_path:
                image_analysis = analyze_emergency_image(image_path, description)
                ai_analysis += f"\n\nImage Analysis: {image_analysis}"
            
        except Exception as e:
            logging.error(f"AI analysis failed: {e}")
            ai_analysis = "AI analysis unavailable. Report submitted successfully."
            class DefaultAnalysis:
                severity = 'medium'
                category = 'other'
            analysis = DefaultAnalysis()
        
        # Create emergency report
        report = models.EmergencyReport()
        report.user_id = session['user_id']
        report.title = title
        report.description = description
        report.location = location
        report.latitude = latitude
        report.longitude = longitude
        report.image_path = image_path
        report.severity = analysis.severity
        report.ai_analysis = ai_analysis
        
        try:
            db.session.add(report)
            db.session.commit()
            
            # Send SMS alerts for critical/high severity emergencies
            if analysis.severity in ['critical', 'high']:
                user = models.User.query.get(session['user_id'])
                if user and user.phone:
                    send_emergency_sms(user.phone, report)
                    
                # Send bulk alerts for critical emergencies
                if analysis.severity == 'critical':
                    alert_count = send_bulk_emergency_alerts(report)
                    logging.info(f"Sent {alert_count} emergency SMS alerts")
            
            # Notify team: Slack if available else local log
            if not send_emergency_to_slack(report):
                notify_emergency_locally(report)
            
            flash('Emergency report submitted successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to save report: {e}")
            flash('Failed to submit report. Please try again.', 'error')
    
    return render_template('report.html')

@app.route('/map')
def map_view():
    if 'user_id' not in session:
        flash('Please log in to view the map', 'error')
        return redirect(url_for('login'))
    
    return render_template('map.html')

@app.route('/api/reports')
def api_reports():
    """API endpoint to get reports for map display"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    reports = models.EmergencyReport.query.filter(
        models.EmergencyReport.latitude.isnot(None),
        models.EmergencyReport.longitude.isnot(None)
    ).all()
    
    reports_data = []
    for report in reports:
        reports_data.append({
            'id': report.id,
            'title': report.title,
            'description': report.description[:100] + '...' if len(report.description) > 100 else report.description,
            'location': report.location,
            'latitude': report.latitude,
            'longitude': report.longitude,
            'severity': report.severity,
            'status': report.status,
            'created_at': report.created_at.isoformat()
        })
    
    return jsonify(reports_data)

@app.route('/api/shelters')
def api_shelters():
    """API endpoint to get shelters for map display"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    shelters = models.Shelter.query.filter_by(active=True).all()
    
    shelters_data = []
    for shelter in shelters:
        shelters_data.append({
            'id': shelter.id,
            'name': shelter.name,
            'address': shelter.address,
            'latitude': shelter.latitude,
            'longitude': shelter.longitude,
            'capacity': shelter.capacity,
            'current_occupancy': shelter.current_occupancy,
            'shelter_type': shelter.shelter_type,
            'contact_phone': shelter.contact_phone,
            'facilities': shelter.facilities
        })
    
    return jsonify(shelters_data)

@app.route('/api/alerts')
def api_alerts():
    """API endpoint to get active alerts for map display"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    alerts = models.Alert.query.filter_by(active=True).all()
    
    alerts_data = []
    for alert in alerts:
        alerts_data.append({
            'id': alert.id,
            'title': alert.title,
            'description': alert.description,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'location': alert.location,
            'latitude': alert.latitude,
            'longitude': alert.longitude,
            'radius': alert.radius,
            'created_at': alert.created_at.isoformat(),
            'expires_at': alert.expires_at.isoformat() if alert.expires_at else None
        })
    
    return jsonify(alerts_data)

@app.route('/analytics')
def analytics_dashboard():
    """Advanced analytics dashboard"""
    if 'user_id' not in session:
        flash('Please log in to access analytics', 'error')
        return redirect(url_for('login'))
    
    try:
        insights = generate_emergency_insights_dashboard()
        return render_template('analytics.html', insights=insights)
    except Exception as e:
        logging.error(f"Analytics dashboard error: {e}")
        flash('Analytics temporarily unavailable', 'warning')
        return redirect(url_for('dashboard'))

@app.route('/api/translate', methods=['POST'])
def api_translate():
    """API endpoint for real-time translation"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        text = data.get('text', '')
        target_language = data.get('target_language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        translation = translate_emergency_text(text, target_language)
        return jsonify({
            'translated_text': translation.translated_text,
            'detected_language': translation.detected_language,
            'confidence': translation.confidence
        })
        
    except Exception as e:
        logging.error(f"Translation API error: {e}")
        return jsonify({'error': 'Translation failed'}), 500

@app.route('/api/risk-prediction')
def api_risk_prediction():
    """API endpoint for emergency risk prediction"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        location = request.args.get('location')
        hours = int(request.args.get('hours', 24))
        
        prediction = predict_emergency_risk(location, hours)
        return jsonify(prediction.dict())
        
    except Exception as e:
        logging.error(f"Risk prediction API error: {e}")
        return jsonify({'error': 'Prediction unavailable'}), 500

@app.route('/api/emergency-trends')
def api_emergency_trends():
    """API endpoint for emergency trend analysis"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        days = int(request.args.get('days', 30))
        trends = analyze_emergency_trends(days)
        return jsonify(trends.dict())
        
    except Exception as e:
        logging.error(f"Trends API error: {e}")
        return jsonify({'error': 'Trends analysis unavailable'}), 500

@app.route('/voice-report')
def voice_report():
    """Voice-to-text emergency reporting interface"""
    if 'user_id' not in session:
        flash('Please log in to submit voice reports', 'error')
        return redirect(url_for('login'))
    
    return render_template('voice_report.html')

@app.route('/api/crisis-monitoring')
def api_crisis_monitoring():
    """API endpoint for crisis monitoring dashboard"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        monitoring_report = generate_crisis_monitoring_report()
        return jsonify(monitoring_report)
    except Exception as e:
        logging.error(f"Crisis monitoring API error: {e}")
        return jsonify({'error': 'Monitoring unavailable'}), 500
