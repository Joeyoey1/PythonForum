from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from ..models import User, Role
from werkzeug.security import generate_password_hash

auth = Blueprint('auth', __name__)

@auth.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.get_or_none(User.user_name == username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@auth.route('/create_user/', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('create_user.html')
        
        if User.get_or_none(User.user_name == username):
            flash('User already exists', 'danger')
            return render_template('create_user.html')
        
        # Ensure role exists
        user_role, _ = Role.get_or_create(name='User')
        
        user = User(user_name=username, role=user_role)
        user.set_password(password)
        user.save()
        flash('User created successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('create_user.html')

@auth.route('/logout/', methods=['GET', 'POST'])
@login_required
def logout():
    # Handle both GET and POST for logout to be user-friendly, though POST is safer
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
