### Step-by-Step Guide to Creating a Basic Django App

#### 1. **Set Up Your Environment**
Make sure you have Python and Django installed. If you haven't already installed Django, you can do so with:
```bash
pip install django
```

#### 2. **Create a Django Project**
A Django project is a collection of settings for an instance of Django, including database configuration, Django-specific options, and application-specific settings.

1. Open a terminal or command prompt.
2. Run the following command to create a new project:
   ```bash
   django-admin startproject myproject
   cd myproject
   ```

#### 3. **Create a Django App**
An app is a web application that does something — e.g., a blog system, a database of public records, or a simple poll app.

1. While inside the `myproject` directory, run:
   ```bash
   python manage.py startapp myapp
   ```

2. Your project structure should now look like this:
   ```
   myproject/
       manage.py
       myproject/
           __init__.py
           settings.py
           urls.py
           asgi.py
           wsgi.py
       myapp/
           __init__.py
           admin.py
           apps.py
           models.py
           tests.py
           views.py
           migrations/
   ```

#### 4. **Define a Model**
Models are the single, definitive source of information about your data. They contain the essential fields and behaviors of the data you’re storing.

1. Open `myapp/models.py` and add a model:
   ```python
   from django.db import models

   class Post(models.Model):
       title = models.CharField(max_length=100)
       content = models.TextField()
       created_at = models.DateTimeField(auto_now_add=True)

       def __str__(self):
           return self.title
   ```

2. Apply the migrations to create the database tables:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

#### 5. **Register the Model in Admin**
To make the model accessible from the admin interface, register it in `myapp/admin.py`:
```python
from django.contrib import admin
from .models import Post

admin.site.register(Post)
```

#### 6. **Create a View**
Views are Python functions that take a web request and return a web response.

1. Open `myapp/views.py` and create a view:
   ```python
   from django.http import HttpResponse

   def home(request):
       return HttpResponse("Hello, Django!")
   ```

#### 7. **Map the View to a URL**
1. Create a file named `urls.py` inside `myapp` directory and add the following:
   ```python
   from django.urls import path
   from . import views

   urlpatterns = [
       path('', views.home, name='home'),
   ]
   ```

2. Include `myapp` URLs in the project's URL configuration. Open `myproject/urls.py` and modify it:
   ```python
   from django.contrib import admin
   from django.urls import include, path

   urlpatterns = [
       path('admin/', admin.site.urls),
       path('', include('myapp.urls')),
   ]
   ```

#### 8. **Run the Development Server**
Start the development server to see your app in action:
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your web browser. You should see "Hello, Django!".

#### 9. **Creating Templates**
To render HTML templates instead of simple text, you need to set up templates.

1. Create a directory named `templates` inside `myapp` directory and then create a file named `home.html` inside it:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>Home</title>
   </head>
   <body>
       <h1>Hello, Django with Template!</h1>
   </body>
   </html>
   ```

2. Modify the `home` view to render this template. Update `myapp/views.py`:
   ```python
   from django.shortcuts import render

   def home(request):
       return render(request, 'home.html')
   ```

### Summary
- **Set up a Django project**: `django-admin startproject myproject`
- **Create a Django app**: `python manage.py startapp myapp`
- **Define models, views, and URLs** within your app.
- **Create templates** and use the `render` function to serve HTML content.
- **Run the development server** to see your app in action.
