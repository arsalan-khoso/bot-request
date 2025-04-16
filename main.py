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
# Flask application for glass part scraping

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import threading
import time
import logging
import os
import json
from datetime import datetime
from dotenv import load_dotenv
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
        logging.FileHandler("glass_scraper.log") if os.getenv('GAE_ENV', '') == '' else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GlassScraper")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key')  # Set a secure secret key in production

# Create a dictionary to store search results
# In production, consider using a database or cloud storage instead of in-memory
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
        
        # Update the search results
        with threading.Lock():
            if task_id in search_results:
                search_results[task_id]["results"][scraper_name] = search_result
                search_results[task_id]["completed_count"] += 1
                if search_results[task_id]["completed_count"] >= len(search_results[task_id]["scrapers"]):
                    search_results[task_id]["all_completed"] = True
        
        # Log completion
        elapsed = time.time() - start_time
        logger.info(f"{scraper_name} scraper completed in {elapsed:.2f}s for part {part_number}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Error in {scraper_name} scraper: {str(e)}")
        
        # Update the search results with the error
        with threading.Lock():
            if task_id in search_results:
                search_results[task_id]["results"][scraper_name] = {
                    "supplier": scraper_name,
                    "part_number": part_number,
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "results": [],
                    "time_taken": elapsed,
                    "completed": True,
                }
                search_results[task_id]["completed_count"] += 1
                if search_results[task_id]["completed_count"] >= len(search_results[task_id]["scrapers"]):
                    search_results[task_id]["all_completed"] = True


# Updated run_all_scrapers function
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
    search_results[task_id] = {
        "part_number": part_number,
        "start_time": time.time(),
        "results": {},
        "completed_count": 0,
        "all_completed": False,
        "scrapers": list(scrapers.keys())
    }
    
    # Set initial results for each scraper
    for scraper_name in scrapers.keys():
        search_results[task_id]["results"][scraper_name] = {
            "supplier": scraper_name,
            "part_number": part_number,
            "success": False,
            "message": "Search in progress...",
            "results": [],
            "time_taken": 0,
            "completed": False,
        }
    
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
    # Check if task exists
    if task_id not in search_results:
        flash('Invalid task ID', 'error')
        return redirect(url_for('index'))
    
    return render_template('results.html', task_id=task_id)

@app.route('/api/status/<task_id>')
def status(task_id):
    # Check if task exists
    if task_id not in search_results:
        return jsonify({"error": "Invalid task ID"}), 404
    
    # Calculate elapsed time
    elapsed = time.time() - search_results[task_id]["start_time"]
    
    # Prepare response
    response = {
        "part_number": search_results[task_id]["part_number"],
        "elapsed": elapsed,
        "all_completed": search_results[task_id]["all_completed"],
        "completed_count": search_results[task_id]["completed_count"],
        "total_count": len(search_results[task_id]["scrapers"]),
        "results": {}
    }
    
    # Add results for each scraper
    for scraper_name, result in search_results[task_id]["results"].items():
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
    # Check if task exists
    if task_id not in search_results:
        return jsonify({"error": "Invalid task ID"}), 404
    
    # Check if all scrapers have completed
    if not search_results[task_id]["all_completed"]:
        return jsonify({"error": "Task still in progress"}), 400
    
    # Prepare full results
    results = []
    for scraper_name, result in search_results[task_id]["results"].items():
        results.append(result)
    
    return jsonify(results)

@app.route('/download/<task_id>')
def download(task_id):
    # Check if task exists
    if task_id not in search_results:
        flash('Invalid task ID', 'error')
        return redirect(url_for('index'))
    
    # Check if all scrapers have completed
    if not search_results[task_id]["all_completed"]:
        flash('Task still in progress', 'warning')
        return redirect(url_for('results', task_id=task_id))
    
    # Prepare results for download
    results = []
    for scraper_name, result in search_results[task_id]["results"].items():
        results.append(result)
    
    # Create response
    response = jsonify(results)
    response.headers['Content-Disposition'] = f'attachment; filename=results_{search_results[task_id]["part_number"]}_{int(time.time())}.json'
    return response

# Cleanup old results periodically
def cleanup_old_results():
    while True:
        current_time = time.time()
        # Keep results for 1 hour (3600 seconds)
        to_delete = [task_id for task_id, task in search_results.items() 
                    if current_time - task["start_time"] > 3600]
        
        for task_id in to_delete:
            with threading.Lock():
                if task_id in search_results:
                    del search_results[task_id]
        
        # Check every 5 minutes
        time.sleep(300)

# Start cleanup thread when not running on App Engine
if os.getenv('GAE_ENV', '') == '':
    cleanup_thread = threading.Thread(target=cleanup_old_results)
    cleanup_thread.daemon = True
    cleanup_thread.start()

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
else:
    # When running in production
    # Make sure gunicorn is handling the server, not the development server
    pass