from flask import Flask, render_template, flash, redirect, url_for, request, abort, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_mail import Mail, Message
from flask_session import Session  # Import Session
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from threading import Thread
import chatbot

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nestcircle_secure_key_do_not_share_in_production'  # Consistent secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 7  # 7 days
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
# Ensure the session directory exists
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Initialize Flask-Session
Session(app)

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # Update with your email
app.config['MAIL_PASSWORD'] = 'your-password'  # Update with your password or app password
app.config['MAIL_DEFAULT_SENDER'] = ('NestCircle', 'your-email@gmail.com')

# Initialize database
db = SQLAlchemy(app)

# Initialize mail
mail = Mail(app)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Define models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user', 'moderator', 'admin'
    email_verified = db.Column(db.Boolean, default=False)
    notification_preferences = db.Column(db.Text, default='{"new_resources": true, "comments_on_resources": true, "ratings_on_resources": false}')
    resources = db.relationship('Resource', backref='author', lazy=True)
    ratings = db.relationship('Rating', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    bookmarks = db.relationship('Bookmark', backref='user', lazy=True)

    def has_role(self, role):
        if role == 'user':
            return True
        elif role == 'moderator':
            return self.role in ['moderator', 'admin']
        elif role == 'admin':
            return self.role == 'admin'
        return False

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# Association table for Resource-Category many-to-many relationship
resource_categories = db.Table('resource_categories',
    db.Column('resource_id', db.Integer, db.ForeignKey('resource.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(150), nullable=True)
    resources = db.relationship('Resource', secondary=resource_categories, 
                              backref=db.backref('categories', lazy='dynamic'))
    
    def __repr__(self):
        return f"Category('{self.name}')"

class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resource_type = db.Column(db.String(20), nullable=False)  # "link", "pdf", "youtube", etc.
    content = db.Column(db.Text, nullable=False)  # URL or file path
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ratings = db.relationship('Rating', backref='resource', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='resource', lazy=True, cascade="all, delete-orphan", 
                              order_by="desc(Comment.date_posted)")
    bookmarks = db.relationship('Bookmark', backref='resource', lazy=True, cascade="all, delete-orphan")
    
    @property
    def avg_rating(self):
        if not self.ratings:
            return 0
        return sum(r.rating for r in self.ratings) / len(self.ratings)
    
    def __repr__(self):
        return f"Resource('{self.title}', '{self.date_posted}')"

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    
    # Make sure a user can only rate a resource once
    __table_args__ = (db.UniqueConstraint('user_id', 'resource_id', name='user_resource_uc'),)

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'verify_email', 'reset_password', etc.
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    
    def __repr__(self):
        return f"Comment('{self.content[:20]}...', '{self.date_posted}')"

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_bookmarked = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'), nullable=False)
    
    # Make sure a user can only bookmark a resource once
    __table_args__ = (db.UniqueConstraint('user_id', 'resource_id', name='bookmark_user_resource_uc'),)
    
    def __repr__(self):
        return f"Bookmark(user_id={self.user_id}, resource_id={self.resource_id})"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Role required decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_role(role):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Context processor to add variables to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.context_processor
def inject_user_roles():
    return {'is_admin': current_user.is_authenticated and current_user.has_role('admin'),
            'is_moderator': current_user.is_authenticated and current_user.has_role('moderator')}

# Custom template filters
@app.template_filter('tojson')
def to_json(value):
    import json
    return json.dumps(value)

@app.template_filter('fromjson')
def from_json(value):
    import json
    try:
        return json.loads(value)
    except:
        return {}

# Email Functions
def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body=None):
    """Helper function to send emails"""
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    # Send email asynchronously
    Thread(target=send_async_email, args=(app._get_current_object(), msg)).start()

def send_resource_notification(resource):
    """Send notification about new resource to users who opted in"""
    users = User.query.filter_by(email_verified=True).all()
    recipients = []
    
    # Get users who have new resource notifications enabled (exclude the author)
    import json
    for user in users:
        if user.id != resource.user_id:  # Don't notify the author
            try:
                preferences = json.loads(user.notification_preferences)
                if preferences.get('new_resources', True):
                    recipients.append(user.email)
            except:
                # If error parsing preferences, use default (True)
                recipients.append(user.email)
    
    if not recipients:
        return
    
    subject = f"New Resource on NestCircle: {resource.title}"
    
    text_body = f"""
    Hello from NestCircle!
    
    A new resource has been shared:
    
    Title: {resource.title}
    By: {resource.author.username}
    Type: {resource.resource_type.capitalize()}
    
    Description:
    {resource.description}
    
    View this resource at: {url_for('resource', resource_id=resource.id, _external=True)}
    
    ---
    To manage your email notifications, go to your profile settings.
    """
    
    html_body = f"""
    <h2>New Resource on NestCircle!</h2>
    <p>A new resource has been shared:</p>
    <div style="border-left: 3px solid #007bff; padding-left: 10px; margin: 10px 0;">
        <h3>{resource.title}</h3>
        <p><strong>By:</strong> {resource.author.username}</p>
        <p><strong>Type:</strong> {resource.resource_type.capitalize()}</p>
        <h4>Description:</h4>
        <p>{resource.description}</p>
    </div>
    <p><a href="{url_for('resource', resource_id=resource.id, _external=True)}" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px;">View Resource</a></p>
    <hr>
    <p><small>To manage your email notifications, go to your profile settings.</small></p>
    """
    
    send_email(subject, recipients, text_body, html_body)

def send_comment_notification(comment):
    """Send notification about new comment to resource author"""
    resource = Resource.query.get(comment.resource_id)
    # Don't notify if author is commenting on their own resource
    if comment.user_id == resource.user_id:
        return
    
    # Check if resource author has comment notifications enabled
    import json
    try:
        preferences = json.loads(resource.author.notification_preferences)
        if not preferences.get('comments_on_resources', True) or not resource.author.email_verified:
            return
    except:
        # If error parsing preferences, use default (True)
        pass
    
    subject = f"New Comment on Your Resource: {resource.title}"
    
    text_body = f"""
    Hello {resource.author.username},
    
    {comment.author.username} has commented on your resource "{resource.title}":
    
    "{comment.content}"
    
    View the comment at: {url_for('resource', resource_id=resource.id, _external=True)}
    
    ---
    To manage your email notifications, go to your profile settings.
    """
    
    html_body = f"""
    <h2>New Comment on Your Resource</h2>
    <p>Hello {resource.author.username},</p>
    <p><strong>{comment.author.username}</strong> has commented on your resource "<strong>{resource.title}</strong>":</p>
    <div style="border-left: 3px solid #007bff; padding-left: 10px; margin: 10px 0;">
        <p>"{comment.content}"</p>
    </div>
    <p><a href="{url_for('resource', resource_id=resource.id, _external=True)}" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px;">View Comment</a></p>
    <hr>
    <p><small>To manage your email notifications, go to your profile settings.</small></p>
    """
    
    send_email(subject, [resource.author.email], text_body, html_body)

# Routes
@app.route('/')
@app.route('/home')
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of resources per page
    
    # Get filter parameters
    category_id = request.args.get('category', type=int)
    resource_type = request.args.get('type')
    
    # Base query
    query = Resource.query
    
    # Apply filters if provided
    if category_id:
        category = Category.query.get_or_404(category_id)
        query = category.resources
    
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    
    # Apply pagination
    resources = query.order_by(Resource.date_posted.desc()).paginate(page=page, per_page=per_page)
    
    categories = Category.query.all()
    resource_types = ['link', 'pdf', 'youtube']
    
    return render_template('home.html', 
                          resources=resources, 
                          categories=categories,
                          resource_types=resource_types,
                          current_category=category_id,
                          current_type=resource_type)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if username or email already exists
        user_by_username = User.query.filter_by(username=username).first()
        user_by_email = User.query.filter_by(email=email).first()
        
        if user_by_username:
            flash('Username already taken. Please choose a different one.', 'danger')
        elif user_by_email:
            flash('Email already registered. Please use a different email or login.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            # Create new user
            hashed_password = generate_password_hash(password)
            user = User(username=username, email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            # Set session to permanent if remember is checked
            if remember:
                session.permanent = True
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Number of resources per page
    resources = Resource.query.filter_by(author=current_user).order_by(
        Resource.date_posted.desc()).paginate(page=page, per_page=per_page)
    return render_template('profile.html', resources=resources)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate username and email if they changed
        if username != current_user.username:
            user_by_username = User.query.filter_by(username=username).first()
            if user_by_username:
                flash('Username already taken. Please choose a different one.', 'danger')
                return redirect(url_for('edit_profile'))
                
        if email != current_user.email:
            user_by_email = User.query.filter_by(email=email).first()
            if user_by_email:
                flash('Email already registered. Please use a different email.', 'danger')
                return redirect(url_for('edit_profile'))
        
        # Update user info
        current_user.username = username
        current_user.email = email
        
        # Update notification preferences
        import json
        new_preferences = {
            'new_resources': 'new_resources' in request.form,
            'comments_on_resources': 'comments_on_resources' in request.form,
            'ratings_on_resources': 'ratings_on_resources' in request.form
        }
        current_user.notification_preferences = json.dumps(new_preferences)
        
        # Change password if provided
        if current_password and new_password:
            if not check_password_hash(current_user.password, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('edit_profile'))
                
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('edit_profile'))
                
            hashed_password = generate_password_hash(new_password)
            current_user.password = hashed_password
            flash('Your password has been updated!', 'success')
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))
        
    return render_template('edit_profile.html')

@app.route('/verify_email')
@login_required
def request_email_verification():
    # Generate a verification token
    import secrets
    from datetime import timedelta
    
    # Delete any existing tokens for this user
    Token.query.filter_by(user_id=current_user.id, type='verify_email').delete()
    
    token_string = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(days=1)
    
    token = Token(
        token=token_string,
        user_id=current_user.id,
        type='verify_email',
        expires_at=expires
    )
    
    db.session.add(token)
    db.session.commit()
    
    # Send verification email
    subject = "Verify Your Email - NestCircle"
    
    text_body = f"""
    Hello {current_user.username},
    
    Please verify your email address by clicking on the link below:
    
    {url_for('confirm_email', token=token_string, _external=True)}
    
    This link will expire in 24 hours.
    
    If you did not create an account on NestCircle, please ignore this email.
    """
    
    html_body = f"""
    <h2>Verify Your Email - NestCircle</h2>
    <p>Hello {current_user.username},</p>
    <p>Please verify your email address by clicking on the link below:</p>
    <p><a href="{url_for('confirm_email', token=token_string, _external=True)}" 
    style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px;">Verify Email</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>If you did not create an account on NestCircle, please ignore this email.</p>
    """
    
    send_email(subject, [current_user.email], text_body, html_body)
    
    flash('A verification email has been sent. Please check your inbox.', 'info')
    return redirect(url_for('profile'))

@app.route('/confirm_email/<token>')
def confirm_email(token):
    token_record = Token.query.filter_by(token=token, type='verify_email').first_or_404()
    
    if token_record.is_expired():
        flash('The verification link has expired. Please request a new one.', 'danger')
        return redirect(url_for('profile'))
    
    user = User.query.get(token_record.user_id)
    user.email_verified = True
    
    # Delete the token after use
    db.session.delete(token_record)
    db.session.commit()
    
    flash('Your email has been verified! You will now receive notifications.', 'success')
    return redirect(url_for('profile'))

@app.route('/resource/new', methods=['GET', 'POST'])
@login_required
def new_resource():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        resource_type = request.form.get('resource_type')
        category_ids = request.form.getlist('categories')
        content = ""
        
        if resource_type == 'link' or resource_type == 'youtube':
            content = request.form.get('content')
        elif resource_type == 'pdf':
            file = request.files.get('file')
            if file and file.filename.endswith('.pdf'):
                # Make sure the uploads directory exists
                uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'])
                if not os.path.exists(uploads_dir):
                    os.makedirs(uploads_dir)
                
                # Add timestamp to filename to avoid collisions
                filename = secure_filename(file.filename)
                base, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{base}_{timestamp}{ext}"
                
                # Save the file
                file_path = os.path.join(uploads_dir, unique_filename)
                file.save(file_path)
                
                # Store the path relative to the static folder
                # This will be something like "/static/uploads/file.pdf"
                content = f'/static/uploads/{unique_filename}'
                app.logger.info(f"Saved PDF file to {file_path}, stored path as {content}")
            else:
                flash('Invalid file. Please upload a PDF.', 'danger')
                return redirect(url_for('new_resource'))
        
        resource = Resource(
            title=title,
            description=description,
            resource_type=resource_type,
            content=content,
            author=current_user
        )
        
        # Add selected categories to the resource
        if category_ids:
            selected_categories = Category.query.filter(Category.id.in_(category_ids)).all()
            for category in selected_categories:
                resource.categories.append(category)
        
        db.session.add(resource)
        db.session.commit()
        
        # Send notification to users
        send_resource_notification(resource)
        
        flash('Your resource has been created!', 'success')
        return redirect(url_for('home'))
    
    # Get all categories for the form
    categories = Category.query.all()
    return render_template('create_resource.html', categories=categories)

@app.route('/resource/<int:resource_id>')
def resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    user_rating = None
    is_bookmarked = False
    
    if current_user.is_authenticated:
        user_rating = Rating.query.filter_by(user_id=current_user.id, resource_id=resource_id).first()
        is_bookmarked = Bookmark.query.filter_by(user_id=current_user.id, resource_id=resource_id).first() is not None
    
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of comments per page
    comments = Comment.query.filter_by(resource_id=resource_id).order_by(
        Comment.date_posted.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('resource.html', resource=resource, user_rating=user_rating, 
                          comments=comments, is_bookmarked=is_bookmarked)

@app.route('/resource/<int:resource_id>/rate', methods=['POST'])
@login_required
def rate_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    rating_value = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '')
    
    if rating_value < 1 or rating_value > 5:
        flash('Rating must be between 1 and 5 stars.', 'danger')
        return redirect(url_for('resource', resource_id=resource_id))
        
    # Check if user has already rated this resource
    existing_rating = Rating.query.filter_by(user_id=current_user.id, resource_id=resource_id).first()
    
    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating_value
        existing_rating.comment = comment
        db.session.commit()
        flash('Your rating has been updated!', 'success')
    else:
        # Create new rating
        new_rating = Rating(
            rating=rating_value,
            comment=comment,
            user_id=current_user.id,
            resource_id=resource_id
        )
        db.session.add(new_rating)
        db.session.commit()
        flash('Your rating has been submitted!', 'success')
        
    return redirect(url_for('resource', resource_id=resource_id))

@app.route('/resource/<int:resource_id>/comment', methods=['POST'])
@login_required
def add_comment(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    content = request.form.get('content')
    
    if not content:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('resource', resource_id=resource_id))
    
    comment = Comment(
        content=content,
        user_id=current_user.id,
        resource_id=resource_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Send notification to resource author
    send_comment_notification(comment)
    
    flash('Your comment has been added!', 'success')
    
    return redirect(url_for('resource', resource_id=resource_id))

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    resource_id = comment.resource_id
    
    # Only the comment author or resource author can delete a comment
    if comment.author != current_user and comment.resource.author != current_user:
        abort(403)
    
    db.session.delete(comment)
    db.session.commit()
    flash('Comment has been deleted.', 'success')
    
    return redirect(url_for('resource', resource_id=resource_id))

@app.route('/resource/<int:resource_id>/bookmark', methods=['POST'])
@login_required
def toggle_bookmark(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    bookmark = Bookmark.query.filter_by(user_id=current_user.id, resource_id=resource_id).first()
    
    if bookmark:
        # Remove bookmark
        db.session.delete(bookmark)
        db.session.commit()
        flash('Resource removed from bookmarks.', 'success')
    else:
        # Add bookmark
        new_bookmark = Bookmark(
            user_id=current_user.id,
            resource_id=resource_id
        )
        db.session.add(new_bookmark)
        db.session.commit()
        flash('Resource added to bookmarks!', 'success')
    
    return redirect(url_for('resource', resource_id=resource_id))

@app.route('/bookmarks')
@login_required
def bookmarks():
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of resources per page
    
    bookmarked_resources = Resource.query.join(Bookmark).filter(
        Bookmark.user_id == current_user.id
    ).order_by(Resource.date_posted.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('bookmarks.html', resources=bookmarked_resources)

@app.route('/resource/<int:resource_id>/delete', methods=['POST'])
@login_required
def delete_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    if resource.author != current_user:
        abort(403)
        
    if resource.resource_type == 'pdf':
        # Delete the file from the server if it's a PDF
        if os.path.exists(os.path.join(app.root_path, resource.content[1:])):
            os.remove(os.path.join(app.root_path, resource.content[1:]))
            
    db.session.delete(resource)
    db.session.commit()
    flash('Your resource has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    category_id = request.args.get('category_id')
    resource_type = request.args.get('resource_type')
    
    # Base query
    resources_query = Resource.query
    
    # Apply filters
    if query:
        resources_query = resources_query.filter(
            (Resource.title.contains(query)) | 
            (Resource.description.contains(query))
        )
    
    if category_id:
        resources_query = resources_query.join(
            resource_categories
        ).join(
            Category
        ).filter(Category.id == category_id)
        
    if resource_type:
        resources_query = resources_query.filter(Resource.resource_type == resource_type)
    
    # Get results
    resources = resources_query.order_by(Resource.date_posted.desc()).all()
    
    # Get all categories for filtering
    categories = Category.query.all()
    
    return render_template('search.html', resources=resources, query=query, 
                          categories=categories, selected_category_id=category_id)

@app.route('/categories')
def categories():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/category/<int:category_id>')
def category(category_id):
    category = Category.query.get_or_404(category_id)
    # Get resources from this category, ordered by date
    resources = Resource.query.join(Resource.categories).filter(Category.id == category_id).order_by(Resource.date_posted.desc()).all()
    return render_template('category.html', category=category, resources=resources)

@app.route('/categories/manage', methods=['GET', 'POST'])
@login_required
def user_manage_categories():
    # Check if user is admin (you'll need to add an admin field to User model later)
    if current_user.id != 1:  # Assuming user with ID 1 is admin for now
        flash('You do not have permission to manage categories.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            description = request.form.get('description')
            
            if name:
                category = Category(name=name, description=description)
                db.session.add(category)
                db.session.commit()
                flash(f'Category "{name}" has been added!', 'success')
            
        elif action == 'delete':
            category_id = request.form.get('category_id')
            
            if category_id:
                category = Category.query.get(category_id)
                if category:
                    db.session.delete(category)
                    db.session.commit()
                    flash(f'Category "{category.name}" has been deleted!', 'success')
        
        return redirect(url_for('user_manage_categories'))
    
    categories = Category.query.all()
    return render_template('manage_categories.html', categories=categories)

# Admin routes
@app.route('/admin')
@login_required
@role_required('admin')
def admin_panel():
    return render_template('admin/index.html')

@app.route('/admin/users')
@login_required
@role_required('admin')
def manage_users():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    users = User.query.order_by(User.username).paginate(page=page, per_page=per_page)
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/update_role', methods=['POST'])
@login_required
@role_required('admin')
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    
    # Admin can't change their own role
    if user == current_user:
        flash('You cannot change your own role.', 'danger')
        return redirect(url_for('manage_users'))
    
    new_role = request.form.get('role')
    if new_role not in ['user', 'moderator', 'admin']:
        flash('Invalid role.', 'danger')
        return redirect(url_for('manage_users'))
    
    user.role = new_role
    db.session.commit()
    flash(f'Role updated for {user.username} to {new_role}.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/categories')
@login_required
@role_required('moderator')
def admin_manage_categories():
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@login_required
@role_required('moderator')
def add_category():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('add_category'))
        
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            flash('A category with that name already exists.', 'danger')
            return redirect(url_for('add_category'))
        
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully.', 'success')
        return redirect(url_for('admin_manage_categories'))
    
    return render_template('admin/add_category.html')

@app.route('/admin/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('moderator')
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('edit_category', category_id=category_id))
        
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category and existing_category.id != category_id:
            flash('A category with that name already exists.', 'danger')
            return redirect(url_for('edit_category', category_id=category_id))
        
        category.name = name
        category.description = description
        db.session.commit()
        flash('Category updated successfully.', 'success')
        return redirect(url_for('admin_manage_categories'))
    
    return render_template('admin/edit_category.html', category=category)

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    if category.resources.count() > 0:
        flash('Cannot delete category that has resources. Remove all resources from this category first.', 'danger')
        return redirect(url_for('admin_manage_categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully.', 'success')
    return redirect(url_for('admin_manage_categories'))

# Chatbot routes
@app.route('/api/chatbot/init/<int:resource_id>', methods=['POST'])
@login_required
def chatbot_init(resource_id):
    """Initialize chatbot with resource content."""
    # Check if API key is set
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "not_set":
        return jsonify({
            'success': False, 
            'error': 'Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.'
        })
    
    # Check if model works
    if not chatbot.model_works or chatbot.model is None:
        return jsonify({
            'success': False,
            'error': 'The Gemini AI model is not working. Please check your API key and internet connection.'
        })
        
    try:
        resource = Resource.query.get_or_404(resource_id)
        app.logger.info(f"Initializing chatbot for resource ID {resource_id}, type: {resource.resource_type}")
        
        # Get the resource content
        content = resource.content
        if resource.resource_type == 'pdf':
            # For PDF files, content should be a path like "/static/uploads/filename.pdf"
            # We need to convert it to an absolute path
            if content.startswith('/'):
                file_path = os.path.join(app.root_path, content[1:])  # Remove leading slash
            else:
                file_path = os.path.join(app.root_path, content)
            
            app.logger.info(f"Processing PDF file: {file_path}")
                
            if not os.path.exists(file_path):
                error_msg = f'PDF file not found at {file_path}. Please make sure the file exists.'
                app.logger.error(error_msg)
                return jsonify({
                    'success': False,
                    'error': error_msg
                })
            content = file_path
        
        # Get resource text based on type
        app.logger.info(f"Extracting text from {resource.resource_type}: {content[:100]}...")
        resource_text = chatbot.get_resource_text(resource.resource_type, content)
        
        if resource_text.startswith("Error"):
            app.logger.error(f"Error extracting text: {resource_text}")
            return jsonify({
                'success': False,
                'error': resource_text
            })
        
        app.logger.info(f"Successfully extracted text of length {len(resource_text)}")
        
        # Initialize session for this chat
        if 'chatbot_sessions' not in session:
            session['chatbot_sessions'] = {}
        
        # Create a unique session ID for this resource
        session_id = f"resource_{resource_id}"
        session['chatbot_sessions'][session_id] = {
            'resource_id': resource_id,
            'resource_text': resource_text[:15000], # Limit text size
            'history': []
        }
        
        return jsonify({
            'success': True, 
            'session_id': session_id,
            'resource_type': resource.resource_type,
            'model': 'Gemini 2.0 Flash' if chatbot.model_works else 'Not available'
        })
    except Exception as e:
        app.logger.error(f"Error initializing chatbot: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Error initializing chatbot: {str(e)}'
        })

@app.route('/api/chatbot/chat', methods=['POST'])
@login_required
def chatbot_chat():
    """Chat with the chatbot."""
    # Check if API key is set
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "not_set":
        return jsonify({
            'success': False, 
            'error': 'Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file.'
        })
    
    # Check if model works
    if not chatbot.model_works or chatbot.model is None:
        return jsonify({
            'success': False,
            'error': 'The Gemini AI model is not working. Please check your API key and internet connection.'
        })
    
    try:
        data = request.json
        session_id = data.get('session_id')
        prompt = data.get('prompt')
        
        if not session_id or not prompt:
            return jsonify({'success': False, 'error': 'Invalid session ID or prompt'})
            
        if 'chatbot_sessions' not in session:
            return jsonify({'success': False, 'error': 'No active chatbot sessions'})
            
        if session_id not in session['chatbot_sessions']:
            return jsonify({'success': False, 'error': 'Session expired or invalid'})
        
        chat_session = session['chatbot_sessions'][session_id]
        resource_text = chat_session.get('resource_text')
        history = chat_session.get('history', [])
        
        # Get response from Gemini with timeout handling
        try:
            # 45 second timeout for generation
            response_text, updated_history = chatbot.chat_with_gemini(prompt, resource_text, history, timeout=45)
        except chatbot.TimeoutError:
            return jsonify({
                'success': False, 
                'error': 'The AI model took too long to respond. Please try a simpler question or try again later.'
            })
        
        # Check if response indicates an error
        if response_text.startswith("Error generating response:") or response_text.startswith("The AI model took too long"):
            app.logger.error(f"Chatbot error: {response_text}")
            return jsonify({
                'success': False, 
                'error': response_text
            })
        
        # Update session history
        chat_session['history'] = updated_history
        session.modified = True
        
        return jsonify({'success': True, 'response': response_text})
    except Exception as e:
        app.logger.error(f"Error in chatbot_chat: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Error processing request: {str(e)}'
        })

if __name__ == '__main__':
    with app.app_context():
        # Check if the User table exists but doesn't have the 'role' column
        inspector = inspect(db.engine)
        if 'user' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('user')]
            if 'role' not in columns:
                # Add the role column to the existing table
                with db.engine.begin() as conn:
                    conn.execute(db.text('ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT "user" NOT NULL'))
                print("Added 'role' column to User table")
        
        # Create all tables that don't exist yet
        db.create_all()
        
        # Add default categories if none exist
        if Category.query.count() == 0:
            default_categories = [
                {'name': 'Mathematics', 'description': 'Resources for math subjects like algebra, calculus, and statistics'},
                {'name': 'Computer Science', 'description': 'Programming, algorithms, and computer theory resources'},
                {'name': 'Physics', 'description': 'Resources covering mechanics, electromagnetism, and quantum physics'},
                {'name': 'Chemistry', 'description': 'Organic, inorganic, and physical chemistry resources'},
                {'name': 'Biology', 'description': 'Resources for molecular biology, ecology, and more'},
                {'name': 'Literature', 'description': 'Classic and contemporary literature resources'},
                {'name': 'History', 'description': 'World history, civilizations, and historical events'},
                {'name': 'Languages', 'description': 'Resources for learning different languages'}
            ]
            
            for category_data in default_categories:
                category = Category(name=category_data['name'], description=category_data['description'])
                db.session.add(category)
            
            db.session.commit()
            print('Default categories added!')
        
        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_password = generate_password_hash('admin123')
            admin = User(username='admin', email='admin@nestcircle.com', password=admin_password, role='admin')
            db.session.add(admin)
            db.session.commit()
            print('Admin user created! Username: admin, Password: admin123')
    
    app.run(debug=True)
