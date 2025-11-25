import sys
import os

# Add your project directory to Python path
project_dir = r'C:\xampp\htdocs\grab_accounting'
sys.path.insert(0, project_dir)

from app import app as application