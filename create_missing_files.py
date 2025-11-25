import os
import sys

def create_folder_structure():
    """Create necessary folders and files"""
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create folders
    folders = [
        'templates',
        'static/css',
        'static/js'
    ]
    
    for folder in folders:
        folder_path = os.path.join(base_dir, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"✅ Created folder: {folder}")
        else:
            print(f"📁 Folder exists: {folder}")
    
    # Create base.html
    base_html = '''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grab Accounting - {% block title %}{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    {% if session.user_id %}
    <nav class="navbar">
        <div class="container">
            <a href="{{ url_for('dashboard') }}" class="navbar-brand">
                💚 Grab Accounting
            </a>
            <div style="float: right;">
                <span>Halo, {{ session.username }}</span>
                <a href="{{ url_for('logout') }}" class="btn btn-outline" style="margin-left: 1rem;">Logout</a>
            </div>
        </div>
    </nav>
    {% endif %}

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'error' if category == 'error' else 'success' }}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>
</body>
</html>'''
    
    base_html_path = os.path.join(base_dir, 'templates', 'base.html')
    if not os.path.exists(base_html_path):
        with open(base_html_path, 'w', encoding='utf-8') as f:
            f.write(base_html)
        print("✅ Created: templates/base.html")
    
    # Create basic CSS
    css_content = ''':root {
    --primary: #00B14F;
    --primary-dark: #007A33;
    --secondary: #3B82F6;
    --danger: #EF4444;
    --warning: #F59E0B;
    --success: #10B981;
    --white: #FFFFFF;
    --gray-50: #F9FAFB;
    --gray-100: #F3F4F6;
    --gray-200: #E5E7EB;
    --gray-300: #D1D5DB;
    --text-primary: #111827;
    --text-secondary: #6B7280;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: var(--gray-50);
    color: var(--text-primary);
}

.navbar {
    background: var(--white);
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    padding: 1rem 2rem;
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.25rem;
    font-weight: bold;
    color: var(--primary);
    text-decoration: none;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

.card {
    background: var(--white);
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 1.5rem;
}

.card-header {
    padding: 1.5rem;
    border-bottom: 1px solid var(--gray-200);
}

.card-body {
    padding: 1.5rem;
}

.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    text-decoration: none;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background: var(--primary);
    color: var(--white);
}

.btn-primary:hover {
    background: var(--primary-dark);
}

.btn-outline {
    background: var(--white);
    color: var(--primary);
    border: 1px solid var(--primary);
}

.btn-outline:hover {
    background: var(--gray-50);
}

.form-group {
    margin-bottom: 1rem;
}

.form-label {
    display: block;
    margin-bottom: 0.5rem;
    color: var(--text-secondary);
    font-weight: 500;
}

.form-control {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid var(--gray-300);
    border-radius: 6px;
    font-size: 1rem;
}

.form-control:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(0, 177, 79, 0.1);
}

.alert {
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
}

.alert-success {
    background: #D1FAE5;
    color: #065F46;
    border: 1px solid #A7F3D0;
}

.alert-error {
    background: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FECACA;
}

.login-container {
    max-width: 400px;
    margin: 4rem auto;
    padding: 2rem;
}'''
    
    css_path = os.path.join(base_dir, 'static', 'css', 'style.css')
    if not os.path.exists(css_path):
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        print("✅ Created: static/css/style.css")
    
    print("\n🎉 Folder structure created successfully!")
    print("🚀 Now run: python app.py")

if __name__ == '__main__':
    create_folder_structure()