# Restaurant POS System

A modern, web-based restaurant billing and POS (Point of Sale) system built with Python Flask. This system is designed for dine-in restaurants and allows owners/admins and staff/waiters to manage orders, tables, billing, and delivery integrations.

## Features

- **User Roles**
  - Admin account for restaurant owners (billing counter)
  - Staff account for waiters taking orders

- **Menu Management**
  - Add, edit, delete menu items with names, prices, and quantities (half/full)
  - CRUD UI for managing the full menu

- **Table Management**
  - Set up multiple tables (Table 1, Table 2, etc.)
  - Assign orders to specific tables
  - View active orders by table

- **Order Flow**
  - Select a table, add items with selected quantity, and place orders
  - Real-time order updates from staff to admin dashboard

- **Billing**
  - Generate compact bills showing restaurant details, ordered items, and totals
  - Printable in thermal receipt format

- **Dashboard**
  - Real-time sales data
  - Order tracking
  - Revenue breakdown (daily/weekly/monthly)
  - Popular items analysis

- **Delivery Integration**
  - Connect with Zomato and Swiggy accounts
  - Accept/reject orders
  - Update order statuses
  - View all delivery orders in the same dashboard

## Tech Stack

- **Backend**: Python Flask with SQLAlchemy ORM
- **Frontend**: Jinja2 templates with Tailwind CSS
- **Database**: SQLite (default), PostgreSQL or MySQL (configurable)
- **Real-time Updates**: Flask-SocketIO
- **Authentication**: Flask-Login
- **API**: RESTful endpoints for delivery integrations

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- PostgreSQL or MySQL (optional, for production)
- wkhtmltopdf (required for PDF generation)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/restaurant-pos.git
   cd restaurant-pos
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install wkhtmltopdf (required for PDF generation):
   - On Windows:
     - Download the installer from https://wkhtmltopdf.org/downloads.html
     - Install it to the default location (usually C:\Program Files\wkhtmltopdf)
   - On macOS:
     ```bash
     brew install wkhtmltopdf
     ```
   - On Ubuntu/Debian:
     ```bash
     sudo apt-get install wkhtmltopdf
     ```
   - On CentOS/RHEL:
     ```bash
     sudo yum install wkhtmltopdf
     ```

5. Set up environment variables:
   - Create a `.env` file in the project root
   - Add the following variables:
     ```
     FLASK_APP=run.py
     FLASK_ENV=development
     SECRET_KEY=your_secret_key_here
     DATABASE_URL=sqlite:///restaurant_pos.db  # or your PostgreSQL/MySQL URL
     RESTAURANT_NAME=Your Restaurant Name
     RESTAURANT_PHONE=+1234567890
     RESTAURANT_ADDRESS=123 Main St, City, Country
     ZOMATO_API_KEY=your_zomato_api_key
     SWIGGY_API_KEY=your_swiggy_api_key
     ```

6. Initialize the database:
   ```bash
   python init_db.py
   ```

7. Run the application:
   ```bash
   python run.py
   ```

8. Access the application:
   - Open your browser and go to `http://localhost:5000`
   - Login with:
     - Admin: username `admin`, password `admin123`
     - Staff: username `staff`, password `staff123`

## Deployment

### Deploying to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Configure the service:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn run:app`
   - Add environment variables from your `.env` file

### Deploying to Other Cloud Providers

The application can be deployed to any cloud provider that supports Python applications, such as:
- Heroku
- AWS Elastic Beanstalk
- Google Cloud Run
- DigitalOcean App Platform

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Flask and its extensions
- Tailwind CSS
- Font Awesome
- Socket.IO
