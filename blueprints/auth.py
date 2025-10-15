"""
Authentication blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from models import User
from services.auth import authenticate_user, create_user, log_audit
from services.security import SecurityUtils
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))
        
        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('auth/login.html')
        
        user = authenticate_user(email, password)
        
        if user:
            login_user(user, remember=remember_me)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('public.index')
            
            flash(f'Welcome back, {user.email}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """User logout"""
    user_email = current_user.email
    logout_user()
    
    log_audit('logout', 'user', None, {'email': user_email})
    flash('You have been logged out.', 'info')
    
    return redirect(url_for('public.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (optional feature)"""
    # Check if registration is enabled
    if not current_app.config.get('ALLOW_REGISTRATION', False):
        flash('Registration is currently disabled.', 'error')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not email or not password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('auth/register.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already registered.', 'error')
            return render_template('auth/register.html')
        
        try:
            user = create_user(email, password, 'user')
            login_user(user)
            
            flash('Registration successful! Welcome to Notu!', 'success')
            return redirect(url_for('public.index'))
        
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    from services.auth import get_user_stats
    
    stats = get_user_stats(current_user.id)
    
    return render_template('auth/profile.html', stats=stats)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            flash('Please fill in all fields.', 'error')
            return render_template('auth/change_password.html')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'error')
            return render_template('auth/change_password.html')
        
        try:
            current_user.set_password(new_password)
            
            from app import db
            db.session.commit()
            
            log_audit('password_changed', 'user', current_user.id)
            flash('Password changed successfully.', 'success')
            return redirect(url_for('auth.profile'))
        
        except Exception as e:
            logger.error(f"Password change error: {e}")
            flash('Failed to change password. Please try again.', 'error')
    
    return render_template('auth/change_password.html')
