# # app.py
# # Flask application for glass part scraping

# from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
# import asyncio
# import threading
# import time
# import logging
# import os
# import json
# from datetime import datetime
# from dotenv import load_dotenv
# from concurrent.futures import ThreadPoolExecutor
# import uuid

# # Import all scrapers
# from Scrapers.igc_scraper import IGCScraper
# from Scrapers.mygrant_scraper import MyGrantScraper
# from Scrapers.pilkington_scraper import PilkingtonScraper
# from Scrapers.pwg_scraper import PWGScraper

# # Load environment variables
# load_dotenv()

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#     handlers=[
#         logging.FileHandler("glass_scraper.log"),
#         logging.StreamHandler()
#     ]
# )

# logger = logging.getLogger("GlassScraper")

# # Initialize Flask app
# app = Flask(__name__)
# app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key')  # Set a secure secret key in production

# # Create a dictionary to store search results
# search_results = {}

# # Function to run a scraper in a thread
# def run_scraper(scraper_class, scraper_name, part_number, task_id):
#     start_time = time.time()
#     logger.info(f"Starting {scraper_name} scraper for part: {part_number}")
    
#     try:
#         # For Pilkington and other request-based scrapers that accept part_number directly
#         if scraper_name in ["Pilkington", "Mygrant Glass", "PWG"]:
#             # These scrapers accept part_number directly
#             results = scraper_class(part_number, logger)
            
#             # Format the results
#             formatted_results = []
#             for part in results:
#                 formatted_results.append({
#                     'part_number': part[0],
#                     'stock': part[1] if scraper_name == "Mygrant Glass" else None,
#                     'availability': part[1] if scraper_name != "Mygrant Glass" else None,
#                     'price': part[2],
#                     'location': part[3],
#                     'description': part[4] if len(part) > 4 else 'N/A'
#                 })
                
#             # Create search_result in the expected format
#             search_result = {
#                 "supplier": scraper_name,
#                 "part_number": part_number,
#                 "success": len(results) > 0,
#                 "message": "Search completed successfully" if len(results) > 0 else "No parts found",
#                 "results": formatted_results,
#                 "time_taken": time.time() - start_time,
#                 "completed": True
#             }
#         else:
#             # Class-based scrapers with separate login/search methods
#             # Create a new instance of the scraper
#             scraper = scraper_class()
            
#             # Login
#             if scraper_name == "Import Glass Corp":
#                 login_result = scraper.login()
#             else:
#                 login_result = {"success": False, "message": "Unknown scraper"}
            
#             # Check if login was successful
#             if not login_result.get("success", False):
#                 search_result = {
#                     "supplier": scraper_name,
#                     "part_number": part_number,
#                     "success": False,
#                     "message": login_result.get("message", "Login failed"),
#                     "results": [],
#                     "time_taken": time.time() - start_time,
#                     "completed": True
#                 }
#             else:
#                 # Search for the part
#                 search_result = scraper.search(part_number)
                
#                 # Add supplier and part_number info to the result
#                 search_result["supplier"] = scraper_name
#                 search_result["part_number"] = part_number
#                 search_result["completed"] = True
        
#         # Update the search results
#         with threading.Lock():
#             if task_id in search_results:
#                 search_results[task_id]["results"][scraper_name] = search_result
#                 search_results[task_id]["completed_count"] += 1
#                 if search_results[task_id]["completed_count"] >= len(search_results[task_id]["scrapers"]):
#                     search_results[task_id]["all_completed"] = True
        
#         # Log completion
#         elapsed = time.time() - start_time
#         logger.info(f"{scraper_name} scraper completed in {elapsed:.2f}s for part {part_number}")
        
#     except Exception as e:
#         elapsed = time.time() - start_time
#         logger.error(f"Error in {scraper_name} scraper: {str(e)}")
        
#         # Update the search results with the error
#         with threading.Lock():
#             if task_id in search_results:
#                 search_results[task_id]["results"][scraper_name] = {
#                     "supplier": scraper_name,
#                     "part_number": part_number,
#                     "success": False,
#                     "message": f"Error: {str(e)}",
#                     "results": [],
#                     "time_taken": elapsed,
#                     "completed": True,
#                 }
#                 search_results[task_id]["completed_count"] += 1
#                 if search_results[task_id]["completed_count"] >= len(search_results[task_id]["scrapers"]):
#                     search_results[task_id]["all_completed"] = True


# # In your app.py, update the run_all_scrapers function
# def run_all_scrapers(part_number, selected_scrapers=None):
#     task_id = str(uuid.uuid4())
    
#     # Define available scrapers
#     scrapers = {
#         "Import Glass Corp": IGCScraper,
#         "Mygrant Glass": MyGrantScraper,
#         "Pilkington": PilkingtonScraper,
#         "PWG": PWGScraper
#     }
    
#     # Filter scrapers if selected_scrapers is provided
#     if selected_scrapers and isinstance(selected_scrapers, list):
#         scrapers = {k: v for k, v in scrapers.items() if k in selected_scrapers}
    
#     # Initialize search results entry
#     search_results[task_id] = {
#         "part_number": part_number,
#         "start_time": time.time(),
#         "results": {},
#         "completed_count": 0,
#         "all_completed": False,
#         "scrapers": list(scrapers.keys())
#     }
    
#     # Set initial results for each scraper
#     for scraper_name in scrapers.keys():
#         search_results[task_id]["results"][scraper_name] = {
#             "supplier": scraper_name,
#             "part_number": part_number,
#             "success": False,
#             "message": "Search in progress...",
#             "results": [],
#             "time_taken": 0,
#             "completed": False,
#         }
    
#     # Start a thread for each scraper
#     threads = []
#     for scraper_name, scraper_class in scrapers.items():
#         thread = threading.Thread(
#             target=run_scraper,
#             args=(scraper_class, scraper_name, part_number, task_id)
#         )
#         thread.daemon = True
#         thread.start()
#         threads.append(thread)
    
#     # Return the task ID for status checking
#     return task_id
# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/search', methods=['POST'])
# def search():
#     # Get form data
#     part_number = request.form.get('part_number', '').strip()
    
#     # Get selected scrapers
#     selected_scrapers = request.form.getlist('scrapers')
    
#     # Validate input
#     if not part_number:
#         flash('Please enter a part number', 'error')
#         return redirect(url_for('index'))
    
#     # Start the scraping process
#     task_id = run_all_scrapers(part_number, selected_scrapers)
    
#     # Redirect to results page
#     return redirect(url_for('results', task_id=task_id))

# @app.route('/results/<task_id>')
# def results(task_id):
#     # Check if task exists
#     if task_id not in search_results:
#         flash('Invalid task ID', 'error')
#         return redirect(url_for('index'))
    
#     return render_template('results.html', task_id=task_id)

# @app.route('/api/status/<task_id>')
# def status(task_id):
#     # Check if task exists
#     if task_id not in search_results:
#         return jsonify({"error": "Invalid task ID"}), 404
    
#     # Calculate elapsed time
#     elapsed = time.time() - search_results[task_id]["start_time"]
    
#     # Prepare response
#     response = {
#         "part_number": search_results[task_id]["part_number"],
#         "elapsed": elapsed,
#         "all_completed": search_results[task_id]["all_completed"],
#         "completed_count": search_results[task_id]["completed_count"],
#         "total_count": len(search_results[task_id]["scrapers"]),
#         "results": {}
#     }
    
#     # Add results for each scraper
#     for scraper_name, result in search_results[task_id]["results"].items():
#         response["results"][scraper_name] = {
#             "completed": result.get("completed", False),
#             "success": result.get("success", False),
#             "message": result.get("message", ""),
#             "time_taken": result.get("time_taken", 0),
#             "result_count": len(result.get("results", []))
#         }
    
#     return jsonify(response)

# @app.route('/api/results/<task_id>')
# def api_results(task_id):
#     # Check if task exists
#     if task_id not in search_results:
#         return jsonify({"error": "Invalid task ID"}), 404
    
#     # Check if all scrapers have completed
#     if not search_results[task_id]["all_completed"]:
#         return jsonify({"error": "Task still in progress"}), 400
    
#     # Prepare full results
#     results = []
#     for scraper_name, result in search_results[task_id]["results"].items():
#         results.append(result)
    
#     return jsonify(results)

# @app.route('/download/<task_id>')
# def download(task_id):
#     # Check if task exists
#     if task_id not in search_results:
#         flash('Invalid task ID', 'error')
#         return redirect(url_for('index'))
    
#     # Check if all scrapers have completed
#     if not search_results[task_id]["all_completed"]:
#         flash('Task still in progress', 'warning')
#         return redirect(url_for('results', task_id=task_id))
    
#     # Prepare results for download
#     results = []
#     for scraper_name, result in search_results[task_id]["results"].items():
#         results.append(result)
    
#     # Create response
#     response = jsonify(results)
#     response.headers['Content-Disposition'] = f'attachment; filename=results_{search_results[task_id]["part_number"]}_{int(time.time())}.json'
#     return response

# # Cleanup old results periodically
# def cleanup_old_results():
#     while True:
#         current_time = time.time()
#         # Keep results for 1 hour (3600 seconds)
#         to_delete = [task_id for task_id, task in search_results.items() 
#                     if current_time - task["start_time"] > 3600]
        
#         for task_id in to_delete:
#             with threading.Lock():
#                 if task_id in search_results:
#                     del search_results[task_id]
        
#         # Check every 5 minutes
#         time.sleep(300)

# # Start cleanup thread
# cleanup_thread = threading.Thread(target=cleanup_old_results)
# cleanup_thread.daemon = True
# cleanup_thread.start()

# if __name__ == '__main__':
#     # Run the Flask app
#     app.run(debug=True, host='0.0.0.0', port=5000)



# app.py
# Flask application for glass part scraping with SQLite persistence

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g
import asyncio
import threading
import time
import logging
import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import uuid

# Import all scrapers
from Scrapers.igc_scraper import IGCScraper
from Scrapers.mygrant_scraper import MyGrantScraper
from Scrapers.pilkington_scraper import PilkingtonScraper
from Scrapers.pwg_scraper import PWGScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("glass_scraper.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GlassScraper")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key')  # Set a secure secret key in production

# Database configuration
DATABASE = 'glass_scraper.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Create schema.sql file if it doesn't exist
def create_schema_file():
    schema_content = """-- Drop tables if they already exist
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS task_results;

-- Create tables
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    part_number TEXT NOT NULL,
    start_time REAL NOT NULL,
    all_completed BOOLEAN NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    scrapers TEXT NOT NULL
);

CREATE TABLE task_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    scraper_name TEXT NOT NULL,
    supplier TEXT NOT NULL,
    part_number TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT 0,
    message TEXT,
    time_taken REAL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT 0,
    results_json TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
);"""
    
    schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_file):
        with open(schema_file, 'w') as f:
            f.write(schema_content)
        logger.info("Created schema.sql file")

# Initialize database if it doesn't exist
def initialize_db():
    create_schema_file()
    
    if not os.path.exists(DATABASE):
        with app.app_context():
            init_db()
            logger.info("Database initialized")

# Database helper functions
def save_task_to_db(task_id, task_data):
    """Save task to SQLite database"""
    db = get_db()
    try:
        # Insert task record
        db.execute(
            'INSERT INTO tasks (task_id, part_number, start_time, all_completed, completed_count, scrapers) VALUES (?, ?, ?, ?, ?, ?)',
            (task_id, task_data["part_number"], task_data["start_time"], 
             task_data["all_completed"], task_data["completed_count"], 
             json.dumps(task_data["scrapers"]))
        )
        
        # Insert initial results for each scraper
        for scraper_name, result in task_data["results"].items():
            db.execute(
                'INSERT INTO task_results (task_id, scraper_name, supplier, part_number, success, message, time_taken, completed, results_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (task_id, scraper_name, result["supplier"], result["part_number"], 
                 result["success"], result["message"], result["time_taken"], 
                 result["completed"], json.dumps(result.get("results", [])))
            )
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error saving task: {str(e)}")

def update_task_result_in_db(task_id, scraper_name, result):
    """Update a specific scraper result in the database"""
    db = get_db()
    try:
        db.execute(
            'UPDATE task_results SET success = ?, message = ?, time_taken = ?, completed = ?, results_json = ? WHERE task_id = ? AND scraper_name = ?',
            (result["success"], result["message"], result["time_taken"], 
             result["completed"], json.dumps(result.get("results", [])), 
             task_id, scraper_name)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error updating task result: {str(e)}")

def update_task_completion_in_db(task_id, completed_count, all_completed):
    """Update task completion status"""
    db = get_db()
    try:
        db.execute(
            'UPDATE tasks SET completed_count = ?, all_completed = ? WHERE task_id = ?',
            (completed_count, all_completed, task_id)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error updating task completion: {str(e)}")

def load_task_from_db(task_id):
    """Load task data from database"""
    db = get_db()
    try:
        # Get task basic info
        task = db.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,)).fetchone()
        
        if not task:
            return None
            
        # Build task data structure
        task_data = {
            "part_number": task["part_number"],
            "start_time": task["start_time"],
            "all_completed": bool(task["all_completed"]),
            "completed_count": task["completed_count"],
            "scrapers": json.loads(task["scrapers"]),
            "results": {}
        }
        
        # Get all results for this task
        results = db.execute('SELECT * FROM task_results WHERE task_id = ?', (task_id,)).fetchall()
        
        for result in results:
            task_data["results"][result["scraper_name"]] = {
                "supplier": result["supplier"],
                "part_number": result["part_number"],
                "success": bool(result["success"]),
                "message": result["message"],
                "time_taken": result["time_taken"],
                "completed": bool(result["completed"]),
                "results": json.loads(result["results_json"])
            }
            
        return task_data
        
    except Exception as e:
        logger.error(f"Database error loading task: {str(e)}")
        return None

# Create a dictionary to store search results (in-memory cache)
search_results = {}

# Function to run a scraper in a thread
def run_scraper(scraper_class, scraper_name, part_number, task_id):
    start_time = time.time()
    logger.info(f"Starting {scraper_name} scraper for part: {part_number}")
    
    try:
        # For Pilkington and other request-based scrapers that accept part_number directly
        if scraper_name in ["Pilkington", "Mygrant Glass", "PWG"]:
            # These scrapers accept part_number directly
            results = scraper_class(part_number, logger)
            
            # Format the results
            formatted_results = []
            for part in results:
                formatted_results.append({
                    'part_number': part[0],
                    'stock': part[1] if scraper_name == "Mygrant Glass" else None,
                    'availability': part[1] if scraper_name != "Mygrant Glass" else None,
                    'price': part[2],
                    'location': part[3],
                    'description': part[4] if len(part) > 4 else 'N/A'
                })
                
            # Create search_result in the expected format
            search_result = {
                "supplier": scraper_name,
                "part_number": part_number,
                "success": len(results) > 0,
                "message": "Search completed successfully" if len(results) > 0 else "No parts found",
                "results": formatted_results,
                "time_taken": time.time() - start_time,
                "completed": True
            }
        else:
            # Class-based scrapers with separate login/search methods
            # Create a new instance of the scraper
            scraper = scraper_class()
            
            # Login
            if scraper_name == "Import Glass Corp":
                login_result = scraper.login()
            else:
                login_result = {"success": False, "message": "Unknown scraper"}
            
            # Check if login was successful
            if not login_result.get("success", False):
                search_result = {
                    "supplier": scraper_name,
                    "part_number": part_number,
                    "success": False,
                    "message": login_result.get("message", "Login failed"),
                    "results": [],
                    "time_taken": time.time() - start_time,
                    "completed": True
                }
            else:
                # Search for the part
                search_result = scraper.search(part_number)
                
                # Add supplier and part_number info to the result
                search_result["supplier"] = scraper_name
                search_result["part_number"] = part_number
                search_result["completed"] = True
        
        # Update the search results in memory and database
        with threading.Lock():
            if task_id in search_results:
                search_results[task_id]["results"][scraper_name] = search_result
                search_results[task_id]["completed_count"] += 1
                all_completed = search_results[task_id]["completed_count"] >= len(search_results[task_id]["scrapers"])
                search_results[task_id]["all_completed"] = all_completed
                
                # Update database
                with app.app_context():
                    update_task_result_in_db(task_id, scraper_name, search_result)
                    update_task_completion_in_db(
                        task_id, 
                        search_results[task_id]["completed_count"],
                        all_completed
                    )
        
        # Log completion
        elapsed = time.time() - start_time
        logger.info(f"{scraper_name} scraper completed in {elapsed:.2f}s for part {part_number}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in {scraper_name} scraper: {str(e)}")
        
        # Update the search results with the error
        with threading.Lock():
            if task_id in search_results:
                error_result = {
                    "supplier": scraper_name,
                    "part_number": part_number,
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "results": [],
                    "time_taken": elapsed,
                    "completed": True,
                }
                search_results[task_id]["results"][scraper_name] = error_result
                search_results[task_id]["completed_count"] += 1
                all_completed = search_results[task_id]["completed_count"] >= len(search_results[task_id]["scrapers"])
                search_results[task_id]["all_completed"] = all_completed
                
                # Update database
                with app.app_context():
                    update_task_result_in_db(task_id, scraper_name, error_result)
                    update_task_completion_in_db(
                        task_id, 
                        search_results[task_id]["completed_count"],
                        all_completed
                    )

# Update run_all_scrapers function
def run_all_scrapers(part_number, selected_scrapers=None):
    task_id = str(uuid.uuid4())
    
    # Define available scrapers
    scrapers = {
        "Import Glass Corp": IGCScraper,
        "Mygrant Glass": MyGrantScraper,
        "Pilkington": PilkingtonScraper,
        "PWG": PWGScraper
    }
    
    # Filter scrapers if selected_scrapers is provided
    if selected_scrapers and isinstance(selected_scrapers, list):
        scrapers = {k: v for k, v in scrapers.items() if k in selected_scrapers}
    
    # Initialize search results entry
    task_data = {
        "part_number": part_number,
        "start_time": time.time(),
        "results": {},
        "completed_count": 0,
        "all_completed": False,
        "scrapers": list(scrapers.keys())
    }
    
    # Set initial results for each scraper
    for scraper_name in scrapers.keys():
        task_data["results"][scraper_name] = {
            "supplier": scraper_name,
            "part_number": part_number,
            "success": False,
            "message": "Search in progress...",
            "results": [],
            "time_taken": 0,
            "completed": False,
        }
    
    # Save to in-memory dictionary
    search_results[task_id] = task_data
    
    # Save to database
    with app.app_context():
        save_task_to_db(task_id, task_data)
    
    # Start a thread for each scraper
    threads = []
    for scraper_name, scraper_class in scrapers.items():
        thread = threading.Thread(
            target=run_scraper,
            args=(scraper_class, scraper_name, part_number, task_id)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Return the task ID for status checking
    return task_id

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    # Get form data
    part_number = request.form.get('part_number', '').strip()
    
    # Get selected scrapers
    selected_scrapers = request.form.getlist('scrapers')
    
    # Validate input
    if not part_number:
        flash('Please enter a part number', 'error')
        return redirect(url_for('index'))
    
    # Start the scraping process
    task_id = run_all_scrapers(part_number, selected_scrapers)
    
    # Redirect to results page
    return redirect(url_for('results', task_id=task_id))

@app.route('/results/<task_id>')
def results(task_id):
    # Try to load from memory or database
    if task_id in search_results:
        task_exists = True
    else:
        with app.app_context():
            task_data = load_task_from_db(task_id)
            if task_data:
                search_results[task_id] = task_data
                task_exists = True
            else:
                task_exists = False
    
    # Check if task exists
    if not task_exists:
        flash('Invalid task ID', 'error')
        return redirect(url_for('index'))
    
    return render_template('results.html', task_id=task_id)

@app.route('/api/status/<task_id>')
def status(task_id):
    # First check in-memory cache
    if task_id in search_results:
        task_data = search_results[task_id]
    else:
        # Try to load from database
        with app.app_context():
            task_data = load_task_from_db(task_id)
        
        # If found in database, cache it in memory
        if task_data:
            search_results[task_id] = task_data
    
    # Check if task exists
    if not task_data:
        return jsonify({"error": "Invalid task ID"}), 404
    
    # Calculate elapsed time
    elapsed = time.time() - task_data["start_time"]
    
    # Prepare response
    response = {
        "part_number": task_data["part_number"],
        "elapsed": elapsed,
        "all_completed": task_data["all_completed"],
        "completed_count": task_data["completed_count"],
        "total_count": len(task_data["scrapers"]),
        "results": {}
    }
    
    # Add results for each scraper
    for scraper_name, result in task_data["results"].items():
        response["results"][scraper_name] = {
            "completed": result.get("completed", False),
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "time_taken": result.get("time_taken", 0),
            "result_count": len(result.get("results", []))
        }
    
    return jsonify(response)

@app.route('/api/results/<task_id>')
def api_results(task_id):
    # Similar pattern to status route
    if task_id in search_results:
        task_data = search_results[task_id]
    else:
        with app.app_context():
            task_data = load_task_from_db(task_id)
        if task_data:
            search_results[task_id] = task_data
    
    # Check if task exists
    if not task_data:
        return jsonify({"error": "Invalid task ID"}), 404
    
    # Check if all scrapers have completed
    if not task_data["all_completed"]:
        return jsonify({"error": "Task still in progress"}), 400
    
    # Prepare full results
    results = []
    for scraper_name, result in task_data["results"].items():
        results.append(result)
    
    return jsonify(results)

@app.route('/download/<task_id>')
def download(task_id):
    # Try to load from memory or database
    if task_id in search_results:
        task_data = search_results[task_id]
    else:
        with app.app_context():
            task_data = load_task_from_db(task_id)
        if task_data:
            search_results[task_id] = task_data
    
    # Check if task exists
    if not task_data:
        flash('Invalid task ID', 'error')
        return redirect(url_for('index'))
    
    # Check if all scrapers have completed
    if not task_data["all_completed"]:
        flash('Task still in progress', 'warning')
        return redirect(url_for('results', task_id=task_id))
    
    # Prepare results for download
    results = []
    for scraper_name, result in task_data["results"].items():
        results.append(result)
    
    # Create response
    response = jsonify(results)
    response.headers['Content-Disposition'] = f'attachment; filename=results_{task_data["part_number"]}_{int(time.time())}.json'
    return response

# Cleanup old results periodically
def cleanup_old_results():
    while True:
        current_time = time.time()
        # Keep results for 1 hour (3600 seconds)
        to_delete = []
        
        # Find old tasks in memory
        for task_id, task in search_results.items():
            if current_time - task["start_time"] > 3600:
                to_delete.append(task_id)
        
        # Delete from memory and database
        with app.app_context():
            db = get_db()
            for task_id in to_delete:
                with threading.Lock():
                    if task_id in search_results:
                        del search_results[task_id]
                
                try:
                    # Delete from database
                    db.execute('DELETE FROM task_results WHERE task_id = ?', (task_id,))
                    db.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error deleting old task {task_id}: {str(e)}")
        
        # Also clean up old records directly from database
        with app.app_context():
            try:
                db = get_db()
                cutoff_time = current_time - 3600
                
                # Get old task IDs
                old_tasks = db.execute('SELECT task_id FROM tasks WHERE start_time < ?', 
                                      (cutoff_time,)).fetchall()
                
                # Delete old records
                for task in old_tasks:
                    task_id = task['task_id']
                    db.execute('DELETE FROM task_results WHERE task_id = ?', (task_id,))
                    db.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
                
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error cleaning up old database records: {str(e)}")
        
        # Check every 5 minutes
        time.sleep(300)

if __name__ == '__main__':
    # Initialize database
    initialize_db()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_old_results)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)