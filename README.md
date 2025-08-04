## Setup and Installation
Follow these steps to get your local development environment up and running.

### 1. Clone the repository

```bash
git clone [https://github.com/your-username/PayJoint.git](https://github.com/your-username/PayJoint.git)
cd PayJoint
````

### 2\. Set up the virtual environment

It is highly recommended to use a Python virtual environment to manage dependencies.

```bash
python -m venv myenv
source myenv/bin/activate
```

### 3\. Install dependencies

Install the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4\. Configure environment variables

Create a `.env` file in the project's root directory to store your sensitive information. This file is ignored by Git.

```env
# .env
DJANGO_SECRET_KEY='your-django-secret-key-here'
SUPABASE_URL='your-supabase-url-here'
SUPABASE_KEY='your-supabase-anon-key-here'
```

### 5\. Run database migrations

Apply the database schema changes to set up the necessary tables.

```bash
python manage.py migrate
```

### 6\. Create a superuser

Create a superuser to access the Django admin panel.

```bash
python manage.py createsuperuser
```

### 7\. Start the development server

```bash
python manage.py runserver
```

You can now access the application at `http://127.0.0.1:8000/`.
