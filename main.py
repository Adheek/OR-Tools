from flask import Flask, render_template, request, jsonify
from or_tools import solve_schedule

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')  # Render the HTML page

@app.route('/solve', methods=['POST'])
def solve():
    data = request.json  # Get JSON data from frontend
    
    # Extract data
    machines = data.get('machines', [])  # List of machines with operations
    products = data.get('products', [])  # List of products with tasks
    setup_times = data.get('setup_times', {})  # Setup time matrix
    orders = data.get('orders', [])  # List of orders with quantities and deadlines
    start_time = data.get('start_time', 0)  # Production start time
    
    # Call OR-Tools solver
    result = solve_schedule(machines, products, setup_times, orders, start_time)
    
    return jsonify(result)  # Send result back as JSON

if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Run Flask server on port 5000