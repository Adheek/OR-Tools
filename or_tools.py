from ortools.sat.python import cp_model
from datetime import datetime

def solve_schedule(machines, products, setup_times, orders, start_time):
    print("\n[API CALL] solve_schedule function called")
    print(f"Inputs: {len(machines)} machines, {len(products)} products, {len(orders)} orders")

    model = cp_model.CpModel()  # Create CP-SAT model

    # Convert start_time from ISO string to datetime
    if isinstance(start_time, str):
        start_datetime = datetime.fromisoformat(start_time)  # Parse ISO datetime string
    else:
        start_datetime = datetime.now()  # Default to now if not provided

    # Data structures
    all_tasks = []  # Store all task info
    task_vars = {}  # Store task variables (start, end, interval)
    machine_tasks = {m['name']: [] for m in machines}  # Tasks grouped by machine
    order_info = {}  # Store order deadline info for violation tracking

    # Calculate appropriate horizon based on workload
    total_work = sum(
        sum(task['duration'] for task in product['tasks']) *
        sum(order['quantity'] for order in orders if order['product'] == product['name'])
        for product in products
    )
    # Horizon = 3x total work to allow for parallelization and setup times
    horizon = max(1000, int(total_work * 3))
    print(f"Total work: {total_work}h, Horizon set to: {horizon}h")

    task_id = 0  # Unique task ID

    # Track previous product on each machine for setup time calculation
    machine_last_product = {}  # {machine_name: [(task, product_name)]}
    for machine in machines:
        machine_last_product[machine['name']] = []
    
    # Create tasks for each order
    order_id = 0
    for order in orders:
        product_name = order['product']  # Get product name
        quantity = order['quantity']  # Get order quantity
        deadline = order['deadline']  # Get deadline

        # Find product definition
        product = next((p for p in products if p['name'] == product_name), None)
        if not product:
            continue  # Skip if product not found

        # Create violation variable for this order (soft constraint)
        order_violation = model.NewIntVar(0, horizon, f'order_violation_{order_id}')

        # Store order info for later violation reporting
        order_info[order_id] = {
            'product': product_name,
            'deadline': deadline,
            'quantity': quantity,
            'violation_var': order_violation,
            'last_task_end': None
        }

        # Create tasks for each unit in the order
        for unit in range(quantity):
            prev_task_end = None  # Track previous task end for dependencies

            for task in product['tasks']:
                operation = task['operation']  # Get operation name
                duration = task['duration']  # Get task duration

                # Find machine that can do this operation
                machine = next((m for m in machines if operation in m['operations']), None)
                if not machine:
                    continue  # Skip if no machine can do this operation

                # Create variables for this task
                start_var = model.NewIntVar(0, horizon, f'start_{task_id}')  # Task start time
                end_var = model.NewIntVar(0, horizon, f'end_{task_id}')  # Task end time
                interval_var = model.NewIntervalVar(start_var, duration, end_var, f'interval_{task_id}')  # Task interval

                # Task dependency: must start after previous task ends
                if prev_task_end is not None:
                    model.Add(start_var >= prev_task_end)  # Precedence constraint

                # Store task info
                task_info = {
                    'id': task_id,
                    'order': order['product'],
                    'operation': operation,
                    'machine': machine['name'],
                    'start': start_var,
                    'end': end_var,
                    'interval': interval_var,
                    'duration': duration,
                    'product': product_name,
                    'order_id': order_id
                }
                all_tasks.append(task_info)
                task_vars[task_id] = task_info
                machine_tasks[machine['name']].append(task_info)
                machine_last_product[machine['name']].append(task_info)

                prev_task_end = end_var  # Update for next task
                order_info[order_id]['last_task_end'] = end_var  # Track last task of order
                task_id += 1

        # Soft deadline constraint: last task of order should finish before deadline + violation
        model.Add(order_info[order_id]['last_task_end'] <= deadline + order_violation)

        order_id += 1
    
    # Add no-overlap constraints and setup time constraints for each machine
    for machine_name, tasks in machine_tasks.items():  # machine_name is a string, tasks is a list
        if len(tasks) > 0:
            intervals = [t['interval'] for t in tasks]  # Get all intervals
            model.AddNoOverlap(intervals)  # No two tasks can overlap on same machine
            
            # Add setup time constraints between consecutive tasks on same machine
            if len(tasks) > 1 and setup_times:  # Only if there are multiple tasks and setup times defined
                for i in range(len(tasks)):
                    for j in range(len(tasks)):
                        if i != j:  # Don't compare task with itself
                            task_i = tasks[i]
                            task_j = tasks[j]
                            
                            # Check if there's a setup time defined for this product switch
                            setup_key = f"{task_i['product']}-{task_j['product']}"
                            setup_time = setup_times.get(setup_key, 0)  # Get setup time, default 0
                            
                            if setup_time > 0:  # Only add constraint if setup time exists
                                # Create boolean: is task_i immediately before task_j?
                                is_before = model.NewBoolVar(f'setup_{task_i["id"]}_to_{task_j["id"]}')
                                
                                # If task_i comes before task_j, add setup time
                                model.Add(task_j['start'] >= task_i['end'] + setup_time).OnlyEnforceIf(is_before)
                                model.Add(task_i['end'] <= task_j['start']).OnlyEnforceIf(is_before)
                                
                                # If not before, then task_j comes before task_i
                                model.Add(task_i['start'] >= task_j['end']).OnlyEnforceIf(is_before.Not())
    
    # Calculate makespan (total completion time)
    if all_tasks:
        makespan = model.NewIntVar(0, horizon, 'makespan')  # Variable for makespan
        all_ends = [t['end'] for t in all_tasks]  # All task end times
        model.AddMaxEquality(makespan, all_ends)  # Makespan = max(all end times)

        # Objective: minimize makespan + penalty for deadline violations
        # High penalty (1000x) ensures solver tries to meet deadlines first
        total_violation = sum(order_info[oid]['violation_var'] for oid in order_info)
        model.Minimize(makespan + 1000 * total_violation)
    
    # Solve
    print(f"Model created with {len(all_tasks)} tasks, {len(order_info)} orders")
    print("Starting solver...")

    solver = cp_model.CpSolver()  # Create solver
    solver.parameters.max_time_in_seconds = 30.0  # Time limit 30 seconds (increased for large datasets)
    solver.parameters.log_search_progress = True  # Enable solver logging

    status = solver.Solve(model)  # Solve the model

    print(f"\n[SOLVER FINISHED]")
    print(f"Status: {solver.StatusName(status)}")
    print(f"Solve time: {solver.WallTime():.2f} seconds")
    print(f"Branches: {solver.NumBranches()}")
    print(f"Conflicts: {solver.NumConflicts()}")
    
    # Prepare result
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        from datetime import timedelta

        # First, create schedule with solved values
        schedule = []
        for task in all_tasks:
            task_start_hours = solver.Value(task['start'])
            task_end_hours = solver.Value(task['end'])

            actual_start = start_datetime + timedelta(hours=task_start_hours)
            actual_end = start_datetime + timedelta(hours=task_end_hours)

            schedule.append({
                'task_id': task['id'],
                'order': task['order'],
                'operation': task['operation'],
                'machine': task['machine'],
                'product': task['product'],
                'start': task_start_hours,
                'end': task_end_hours,
                'duration': task['duration'],
                'start_datetime': actual_start.strftime('%Y-%m-%d %H:%M'),
                'end_datetime': actual_end.strftime('%Y-%m-%d %H:%M'),
                'setup_time': 0  # Will be calculated below
            })

        # Sort by start time
        schedule.sort(key=lambda x: x['start'])

        # Calculate setup times - group by machine and find previous task
        machine_schedule = {}
        for task in schedule:
            machine = task['machine']
            if machine not in machine_schedule:
                machine_schedule[machine] = []
            machine_schedule[machine].append(task)

        # For each machine, calculate setup time based on previous task
        for machine, tasks in machine_schedule.items():
            tasks.sort(key=lambda x: x['start'])  # Sort by start time
            for i in range(len(tasks)):
                if i > 0:  # If not the first task on this machine
                    prev_task = tasks[i - 1]
                    curr_task = tasks[i]

                    # Check if there's a setup time defined
                    setup_key = f"{prev_task['product']}-{curr_task['product']}"
                    setup_time = setup_times.get(setup_key, 0)
                    curr_task['setup_time'] = setup_time

        # Remove 'product' field from final output (order_id not in schedule)
        for task in schedule:
            task.pop('product', None)

        # Calculate deadline violations for each order
        deadline_violations = []
        total_violations = 0
        for oid, oinfo in order_info.items():
            violation_hours = solver.Value(oinfo['violation_var'])
            actual_end = solver.Value(oinfo['last_task_end'])

            if violation_hours > 0:
                deadline_violations.append({
                    'product': oinfo['product'],
                    'quantity': oinfo['quantity'],
                    'deadline': oinfo['deadline'],
                    'actual_completion': actual_end,
                    'violation_hours': violation_hours
                })
                total_violations += violation_hours

        # Determine status based on violations
        if total_violations > 0:
            result_status = 'FEASIBLE_WITH_VIOLATIONS'
        else:
            result_status = 'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'

        result = {
            'status': result_status,
            'makespan': solver.Value(makespan) if all_tasks else 0,
            'schedule': schedule,
            'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M'),
            'deadline_violations': deadline_violations,
            'total_violation_hours': total_violations
        }
    else:
        print(f"\n[SOLVER FAILED]")
        print(f"Status: {solver.StatusName(status)}")

        # Provide detailed diagnostics
        if status == cp_model.INFEASIBLE:
            print("Problem is INFEASIBLE - constraints cannot be satisfied")
            print("Possible causes:")
            print(f"  - Total work ({total_work}h) too large for machine capacity")
            print(f"  - Setup time constraints too restrictive")
            print(f"  - Precedence constraints create circular dependencies")
        elif status == cp_model.MODEL_INVALID:
            print("Model is INVALID - check constraint definitions")
        elif status == cp_model.UNKNOWN:
            print("Status UNKNOWN - solver may have timed out or hit resource limits")
            print(f"  Consider: reducing orders, increasing time limit, or simplifying setup times")

        result = {
            'status': 'INFEASIBLE',
            'message': f'Solver status: {solver.StatusName(status)}. Check console for details.'
        }

    return result  # Return solution