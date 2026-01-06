"""
Large Demo Data Generator for Production Scheduler
Generates random large-scale production data for stress testing
Data changes each time it's called - with varied but achievable deadlines
"""

import random
from datetime import datetime

def get_large_demo_data():
    """
    Generates large random demo data for stress testing
    Returns a dictionary with machines, products, setup times, and orders
    Each call generates different random data
    """

    # Configuration for large data
    NUM_MACHINES = random.randint(8, 15)  # 8-15 machines
    NUM_PRODUCTS = random.randint(15, 25)  # 15-25 products
    NUM_ORDERS = random.randint(20, 40)  # 20-40 orders
    MIN_TASKS_PER_PRODUCT = 3
    MAX_TASKS_PER_PRODUCT = 8

    print(f"\n[LARGE DEMO DATA GENERATOR]")
    print(f"Generating: {NUM_MACHINES} machines, {NUM_PRODUCTS} products, {NUM_ORDERS} orders")
    print(f"Deadlines: Varied (2-6x minimum time, all achievable)")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Define available operations
    operations_pool = [
        'cutting', 'drilling', 'milling', 'turning', 'grinding',
        'welding', 'assembly', 'painting', 'coating', 'polishing',
        'inspection', 'testing', 'packaging', 'heat_treatment',
        'surface_finishing', 'deburring', 'threading', 'boring'
    ]

    # Generate Machines with random operations
    # Strategy: distribute operations across machines to ensure coverage
    machines = []
    operations_per_machine = []

    # First, ensure all key operations are covered
    num_ops_per_machine = max(2, len(operations_pool) // NUM_MACHINES + 1)

    for i in range(NUM_MACHINES):
        # Each machine can do 2-4 operations
        num_ops = random.randint(2, 4)
        machine_ops = operations_pool[i * num_ops_per_machine:(i + 1) * num_ops_per_machine][:num_ops]

        # If not enough ops, sample from pool
        if len(machine_ops) < num_ops:
            additional = random.sample(operations_pool, num_ops - len(machine_ops))
            machine_ops.extend(additional)

        operations_per_machine.extend(machine_ops)

        machines.append({
            'name': f'Machine_{chr(65 + i)}' if i < 26 else f'Machine_{i+1}',
            'operations': machine_ops
        })

    # Collect all available operations
    operations_used = list(set(operations_per_machine))

    # Generate Products with random task sequences
    # IMPORTANT: Only use operations that machines can perform
    products = []
    for i in range(NUM_PRODUCTS):
        num_tasks = random.randint(MIN_TASKS_PER_PRODUCT, MAX_TASKS_PER_PRODUCT)

        # Select random operations ONLY from available operations
        num_to_select = min(num_tasks, len(operations_used))
        product_operations = random.sample(operations_used, num_to_select)

        tasks = []
        for op in product_operations:
            # Random duration between 1-6 hours
            duration = random.randint(1, 6)
            tasks.append({
                'operation': op,
                'duration': duration
            })

        products.append({
            'name': f'Product_{i+1}',
            'tasks': tasks
        })

    # Generate Setup Times (product changeovers)
    setup_times = {}

    # Generate setup times for random product pairs (about 40% of all possible pairs)
    num_setup_times = int((NUM_PRODUCTS * (NUM_PRODUCTS - 1)) * 0.4)

    for _ in range(num_setup_times):
        from_product = random.choice(products)['name']
        to_product = random.choice(products)['name']

        if from_product != to_product:
            setup_key = f"{from_product}-{to_product}"
            # Setup time between 1-4 hours
            setup_times[setup_key] = random.randint(1, 4)

    # Generate Orders with VALID, varied deadlines
    orders = []

    for i in range(NUM_ORDERS):
        product = random.choice(products)
        quantity = random.randint(1, 3)  # 1-3 units per order (reduced for feasibility)

        # Calculate minimum time needed for this order (sequential processing)
        total_task_time = sum(task['duration'] for task in product['tasks']) * quantity

        # Set deadlines between 2x and 6x the minimum time (all achievable)
        # Vary deadlines: some tight (2-3x), some relaxed (4-6x)
        if random.random() < 0.5:
            # 50% tight but achievable deadlines (2-3x minimum)
            deadline = int(total_task_time * random.uniform(2.0, 3.0))
        else:
            # 50% relaxed deadlines (3.5-6x minimum)
            deadline = int(total_task_time * random.uniform(3.5, 6.0))

        # Ensure minimum deadline of 30 hours
        deadline = max(deadline, 30)

        orders.append({
            'product': product['name'],
            'quantity': quantity,
            'deadline': deadline
        })

    # Print statistics
    total_tasks = sum(len(p['tasks']) * sum(o['quantity'] for o in orders if o['product'] == p['name'])
                     for p in products)
    print(f"Total tasks to schedule: ~{total_tasks}")
    print(f"Setup times defined: {len(setup_times)}")
    print(f"Average tasks per product: {sum(len(p['tasks']) for p in products) / len(products):.1f}")
    print(f"Total units to produce: {sum(o['quantity'] for o in orders)}")
    print("-" * 60)

    return {
        'machines': machines,
        'products': products,
        'setup_times': setup_times,
        'orders': orders
    }


def get_extreme_large_demo_data():
    """
    Generates extremely large data for maximum stress testing
    WARNING: May take significant time to solve (30+ seconds or may timeout)
    """

    NUM_MACHINES = random.randint(20, 30)  # 20-30 machines
    NUM_PRODUCTS = random.randint(40, 60)  # 40-60 products
    NUM_ORDERS = random.randint(60, 100)  # 60-100 orders

    print(f"\n[EXTREME LARGE DEMO DATA GENERATOR]")
    print(f"⚠️  WARNING: This will generate EXTREME data!")
    print(f"Generating: {NUM_MACHINES} machines, {NUM_PRODUCTS} products, {NUM_ORDERS} orders")
    print(f"Deadlines: Varied (2-7x minimum time, all achievable)")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚠️  Solving may take time due to problem size!\n")

    operations_pool = [
        'cutting', 'drilling', 'milling', 'turning', 'grinding',
        'welding', 'assembly', 'painting', 'coating', 'polishing',
        'inspection', 'testing', 'packaging', 'heat_treatment',
        'surface_finishing', 'deburring', 'threading', 'boring',
        'stamping', 'forging', 'casting', 'molding', 'extrusion',
        'rolling', 'drawing', 'sintering', 'brazing', 'soldering'
    ]

    # Generate machines ensuring operation coverage
    machines = []
    operations_per_machine = []

    num_ops_per_machine = max(2, len(operations_pool) // NUM_MACHINES + 1)

    for i in range(NUM_MACHINES):
        num_ops = random.randint(2, 5)
        machine_ops = operations_pool[i * num_ops_per_machine:(i + 1) * num_ops_per_machine][:num_ops]

        if len(machine_ops) < num_ops:
            additional = random.sample(operations_pool, num_ops - len(machine_ops))
            machine_ops.extend(additional)

        operations_per_machine.extend(machine_ops)

        machines.append({
            'name': f'Machine_{i+1}',
            'operations': machine_ops
        })

    operations_used = list(set(operations_per_machine))

    # Generate products using ONLY available operations
    products = []
    for i in range(NUM_PRODUCTS):
        num_tasks = random.randint(3, 10)
        num_to_select = min(num_tasks, len(operations_used))
        product_operations = random.sample(operations_used, num_to_select)

        tasks = []
        for op in product_operations:
            duration = random.randint(1, 8)
            tasks.append({
                'operation': op,
                'duration': duration
            })

        products.append({
            'name': f'Product_{i+1}',
            'tasks': tasks
        })

    setup_times = {}
    num_setup_times = int((NUM_PRODUCTS * (NUM_PRODUCTS - 1)) * 0.3)

    for _ in range(num_setup_times):
        from_product = random.choice(products)['name']
        to_product = random.choice(products)['name']

        if from_product != to_product:
            setup_key = f"{from_product}-{to_product}"
            setup_times[setup_key] = random.randint(1, 5)

    # Generate Orders with VALID, varied deadlines
    orders = []
    for i in range(NUM_ORDERS):
        product = random.choice(products)
        quantity = random.randint(1, 3)  # 1-3 units per order (reduced for feasibility)

        total_task_time = sum(task['duration'] for task in product['tasks']) * quantity

        # Set deadlines between 2x and 6x the minimum time (all achievable)
        if random.random() < 0.5:
            # 50% tight but achievable deadlines (2-3.5x minimum)
            deadline = int(total_task_time * random.uniform(2.0, 3.5))
        else:
            # 50% relaxed deadlines (4-7x minimum)
            deadline = int(total_task_time * random.uniform(4.0, 7.0))

        deadline = max(deadline, 40)  # Minimum 40 hours for extreme data

        orders.append({
            'product': product['name'],
            'quantity': quantity,
            'deadline': deadline
        })

    total_tasks = sum(len(p['tasks']) * sum(o['quantity'] for o in orders if o['product'] == p['name'])
                     for p in products)
    print(f"Total tasks to schedule: ~{total_tasks}")
    print(f"Setup times defined: {len(setup_times)}")
    print("-" * 60)

    return {
        'machines': machines,
        'products': products,
        'setup_times': setup_times,
        'orders': orders
    }
