# NestCircle

NestCircle is a platform for students to share educational resources like links, PDF documents, YouTube playlists, and other materials. 

## Features

- User registration with email verification
- Login/logout system
- Profile management
- Resource management (links, PDFs, YouTube videos)
- Categories for organizing resources
- Rating system for resources (1-5 stars)
- Comments section for resources
- Bookmarking system for saving resources
- Search functionality
- Role-based user management (admin, moderator)
- Email notifications for new resources and comments
- Mobile-responsive design

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/NestCircle.git
cd NestCircle
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Update email configuration in `app.py`:
```python
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-password'
app.config['MAIL_DEFAULT_SENDER'] = ('NestCircle', 'your-email@gmail.com')
```

5. Create the database:
```bash
python
>>> from app import app, db
>>> with app.app_context():
>>>     db.create_all()
>>> exit()
```

## Running the Application

```bash
python app.py
```

The application will run on `http://localhost:5000/`

## Admin Access

The application will automatically create an admin user on first run:
- Username: admin
- Password: admin123

Use these credentials to access the admin panel at `/admin`

## License

MIT License

## Created By

NestCircle was created as a student project for sharing educational resources.
