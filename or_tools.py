"""
Production Scheduler using Google OR-Tools CP-SAT Solver
=========================================================
This module solves a production scheduling problem with the following constraints:
- Multiple machines with specific capabilities (operations they can perform)
- Products requiring sequential tasks (operations) with specific durations
- Orders with quantities and deadlines
- No two tasks can run on the same machine simultaneously (no-overlap constraint)
- Tasks within a product must be completed sequentially (precedence constraint)
- Soft deadline constraints with penalty (allows violations if necessary)

The solver minimizes: makespan + 1000 * deadline_violations
"""

from ortools.sat.python import cp_model
from datetime import datetime


def solve_schedule(machines, products, setup_times, orders, start_time):
    """
    Solves the production scheduling problem using CP-SAT solver.

    Args:
        machines: List of dicts with 'name' and 'operations' (list of operation names)
        products: List of dicts with 'name' and 'tasks' (list of operations with durations)
        setup_times: Dict mapping "product1-product2" to setup time in hours
        orders: List of dicts with 'product', 'quantity', and 'deadline' (in hours)
        start_time: Production start datetime (ISO string or datetime object)

    Returns:
        Dict with 'status', 'makespan', 'schedule', and violation information
    """

    print("\n[API CALL] solve_schedule function called")
    print(f"Inputs: {len(machines)} machines, {len(products)} products, {len(orders)} orders")

    # ========================================================================
    # STEP 1: Initialize CP-SAT Model
    # ========================================================================
    # CP-SAT (Constraint Programming - Satisfiability) is a constraint solver
    # that finds optimal solutions by exploring the search space intelligently
    model = cp_model.CpModel()

    # ========================================================================
    # STEP 2: Parse Start Time
    # ========================================================================
    # Convert start_time from ISO string to datetime object for calculations
    if isinstance(start_time, str):
        start_datetime = datetime.fromisoformat(start_time)
    else:
        start_datetime = datetime.now()

    # ========================================================================
    # STEP 3: Initialize Data Structures
    # ========================================================================
    all_tasks = []  # Master list of all tasks with their CP variables
    task_vars = {}  # Quick lookup: task_id -> task info
    machine_tasks = {m['name']: [] for m in machines}  # Tasks grouped by machine for no-overlap constraints
    order_info = {}  # Track order completion times and deadline violations

    # ========================================================================
    # STEP 4: Calculate Time Horizon
    # ========================================================================
    # Horizon = maximum time bound for all variables in the model
    # We calculate total sequential work time, then multiply by 3 to allow:
    # - Parallel execution on multiple machines
    # - Setup times between product changes
    # - Buffer for optimization flexibility
    total_work = sum(
        sum(task['duration'] for task in product['tasks']) *
        sum(order['quantity'] for order in orders if order['product'] == product['name'])
        for product in products
    )
    horizon = max(1000, int(total_work * 3))
    print(f"Total work: {total_work}h, Horizon set to: {horizon}h")

    # ========================================================================
    # STEP 5: Initialize Task Tracking
    # ========================================================================
    task_id = 0  # Unique identifier for each task instance

    # Track tasks by machine for setup time constraints
    machine_last_product = {m['name']: [] for m in machines}

    # ========================================================================
    # STEP 6: Create Tasks and Variables for Each Order
    # ========================================================================
    # For each order, we create individual task instances with CP variables
    # Each task has: start time, end time, and interval (for no-overlap constraints)

    order_id = 0
    for order in orders:
        product_name = order['product']
        quantity = order['quantity']
        deadline = order['deadline']

        # Find the product definition (recipe) for this order
        product = next((p for p in products if p['name'] == product_name), None)
        if not product:
            continue  # Skip if product doesn't exist

        # ====================================================================
        # SOFT CONSTRAINT: Deadline Violations
        # ====================================================================
        # We allow deadline violations but heavily penalize them in the objective
        # order_violation = hours late (0 if on time)
        order_violation = model.NewIntVar(0, horizon, f'order_violation_{order_id}')

        # Track order information for later violation reporting
        order_info[order_id] = {
            'product': product_name,
            'deadline': deadline,
            'quantity': quantity,
            'violation_var': order_violation,
            'last_task_end': None  # Will be set to the end time of the last task
        }

        # ====================================================================
        # Create Tasks for Each Unit in the Order
        # ====================================================================
        # If quantity=3, we create 3 separate instances of all tasks for this product
        # Note: We use _ as the loop variable since we only need to iterate quantity times

        for _ in range(quantity):
            prev_task_end = None  # Track previous task end for precedence constraints

            # Iterate through each task in the product's recipe
            for task in product['tasks']:
                operation = task['operation']
                duration = task['duration']

                # Find a machine capable of performing this operation
                machine = next((m for m in machines if operation in m['operations']), None)
                if not machine:
                    continue  # Skip if no machine can perform this operation

                # ============================================================
                # CREATE CP-SAT VARIABLES
                # ============================================================
                # Each task needs three variables for OR-Tools:

                # 1. start_var: When the task begins [0, horizon]
                start_var = model.NewIntVar(0, horizon, f'start_{task_id}')

                # 2. end_var: When the task finishes [0, horizon]
                end_var = model.NewIntVar(0, horizon, f'end_{task_id}')

                # 3. interval_var: Represents the task as an interval [start, start+duration]
                #    This is used for no-overlap constraints
                interval_var = model.NewIntervalVar(start_var, duration, end_var, f'interval_{task_id}')

                # ============================================================
                # PRECEDENCE CONSTRAINT
                # ============================================================
                # Tasks within the same product unit must be sequential
                # Task N cannot start until Task N-1 has finished
                if prev_task_end is not None:
                    model.Add(start_var >= prev_task_end)

                # ============================================================
                # Store Task Information
                # ============================================================
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

                # Update for next iteration
                prev_task_end = end_var
                order_info[order_id]['last_task_end'] = end_var  # Track last task
                task_id += 1

        # ====================================================================
        # SOFT DEADLINE CONSTRAINT
        # ====================================================================
        # Constraint: last_task_end <= deadline + violation
        # If we finish late, violation will be > 0 (penalized in objective)
        model.Add(order_info[order_id]['last_task_end'] <= deadline + order_violation)

        order_id += 1

    # ========================================================================
    # STEP 7: Add No-Overlap Constraints with Setup Times
    # ========================================================================
    # NO-OVERLAP: Ensures that no two tasks run simultaneously on the same machine
    # SETUP TIMES: Add minimum gap between tasks when switching products
    #
    # Strategy: Use efficient conditional constraints for setup times
    # Only create constraints for task pairs with non-zero setup times

    for machine_name, tasks in machine_tasks.items():
        if len(tasks) > 0:
            # Extract interval variables for all tasks on this machine
            intervals = [t['interval'] for t in tasks]

            # Add the no-overlap constraint: no two intervals can overlap in time
            model.AddNoOverlap(intervals)

            # ================================================================
            # Add Setup Time Constraints (Efficient Method)
            # ================================================================
            # For each pair of tasks on the same machine, if they have
            # different products with a defined setup time, enforce a minimum
            # gap between them using conditional constraints

            if len(tasks) > 1 and setup_times:
                for i in range(len(tasks)):
                    for j in range(i + 1, len(tasks)):  # Only check j > i to reduce constraints
                        task_i = tasks[i]
                        task_j = tasks[j]

                        # Check both directions for setup times
                        setup_key_ij = f"{task_i['product']}-{task_j['product']}"
                        setup_key_ji = f"{task_j['product']}-{task_i['product']}"

                        setup_time_ij = setup_times.get(setup_key_ij, 0)
                        setup_time_ji = setup_times.get(setup_key_ji, 0)

                        # Only add constraints if setup time exists
                        if setup_time_ij > 0:
                            # If task_i comes before task_j: j.start >= i.end + setup_time_ij
                            # Create boolean: does task_i precede task_j?
                            i_before_j = model.NewBoolVar(f'setup_{task_i["id"]}_before_{task_j["id"]}')
                            model.Add(task_j['start'] >= task_i['end'] + setup_time_ij).OnlyEnforceIf(i_before_j)
                            model.Add(task_j['start'] < task_i['start']).OnlyEnforceIf(i_before_j.Not())

                        if setup_time_ji > 0 and task_i['product'] != task_j['product']:
                            # If task_j comes before task_i: i.start >= j.end + setup_time_ji
                            j_before_i = model.NewBoolVar(f'setup_{task_j["id"]}_before_{task_i["id"]}')
                            model.Add(task_i['start'] >= task_j['end'] + setup_time_ji).OnlyEnforceIf(j_before_i)
                            model.Add(task_i['start'] < task_j['start']).OnlyEnforceIf(j_before_i.Not())

    # ========================================================================
    # STEP 8: Define Makespan and Objective Function
    # ========================================================================
    # MAKESPAN: The time when all tasks are completed (max of all end times)
    # We want to minimize makespan to finish production as quickly as possible

    if all_tasks:
        # Create a variable to represent the makespan
        makespan = model.NewIntVar(0, horizon, 'makespan')

        # Collect all task end times
        all_ends = [t['end'] for t in all_tasks]

        # Constraint: makespan = max(all end times)
        # This built-in constraint efficiently tracks the maximum
        model.AddMaxEquality(makespan, all_ends)

        # ====================================================================
        # OBJECTIVE FUNCTION
        # ====================================================================
        # Minimize: makespan + 1000 * total_deadline_violations
        #
        # The 1000x multiplier on violations ensures the solver prioritizes
        # meeting deadlines over minimizing makespan. This creates a
        # lexicographic objective where:
        # 1. First priority: minimize deadline violations
        # 2. Second priority: minimize makespan (total completion time)
        total_violation = sum(order_info[oid]['violation_var'] for oid in order_info)
        model.Minimize(makespan + 1000 * total_violation)

    # ========================================================================
    # STEP 9: Configure and Run the Solver
    # ========================================================================
    print(f"Model created with {len(all_tasks)} tasks, {len(order_info)} orders")
    print("Starting solver...")

    # Create the CP-SAT solver instance
    solver = cp_model.CpSolver()

    # Configure solver parameters
    solver.parameters.max_time_in_seconds = 60 
    solver.parameters.log_search_progress = True  # Show solving progress in console

    # Solve the model
    # The solver will search for the optimal solution that satisfies all
    # constraints while minimizing the objective function
    status = solver.Solve(model)

    # ========================================================================
    # STEP 10: Display Solver Statistics
    # ========================================================================
    print(f"\n[SOLVER FINISHED]")
    print(f"Status: {solver.StatusName(status)}")
    print(f"Solve time: {solver.WallTime():.2f} seconds")
    print(f"Branches: {solver.NumBranches()}")  # Search tree branches explored
    print(f"Conflicts: {solver.NumConflicts()}")  # Conflicts found during search

    # ========================================================================
    # STEP 11: Process Results
    # ========================================================================
    # Extract the solution values from the solver and format for output

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        from datetime import timedelta

        # ====================================================================
        # Extract Schedule from Solver Solution
        # ====================================================================
        # The solver has assigned values to all our decision variables
        # We now extract those values to create the final schedule

        schedule = []
        for task in all_tasks:
            # Get the solved start and end times for this task
            task_start_hours = solver.Value(task['start'])
            task_end_hours = solver.Value(task['end'])

            # Convert relative hours to actual datetime
            actual_start = start_datetime + timedelta(hours=task_start_hours)
            actual_end = start_datetime + timedelta(hours=task_end_hours)

            schedule.append({
                'task_id': task['id'],
                'order': task['order'],
                'operation': task['operation'],
                'machine': task['machine'],
                'product': task['product'],  # Temporary, removed later
                'start': task_start_hours,
                'end': task_end_hours,
                'duration': task['duration'],
                'start_datetime': actual_start.strftime('%Y-%m-%d %H:%M'),
                'end_datetime': actual_end.strftime('%Y-%m-%d %H:%M'),
                'setup_time': 0  # Will be calculated below
            })

        # Sort schedule by start time for readability
        schedule.sort(key=lambda x: x['start'])

        # ====================================================================
        # Calculate Setup Times (Post-Processing)
        # ====================================================================
        # Setup times are the transition time between different products
        # on the same machine. We calculate this based on the actual sequence.

        # Group tasks by machine
        machine_schedule = {}
        for task in schedule:
            machine = task['machine']
            if machine not in machine_schedule:
                machine_schedule[machine] = []
            machine_schedule[machine].append(task)

        # For each machine, calculate setup times between consecutive tasks
        for machine, tasks in machine_schedule.items():
            tasks.sort(key=lambda x: x['start'])  # Ensure chronological order
            for i in range(len(tasks)):
                if i > 0:  # If not the first task on this machine
                    prev_task = tasks[i - 1]
                    curr_task = tasks[i]

                    # Check if a setup time is defined for this product transition
                    setup_key = f"{prev_task['product']}-{curr_task['product']}"
                    setup_time = setup_times.get(setup_key, 0)
                    curr_task['setup_time'] = setup_time

        # Clean up: remove internal 'product' field from output
        for task in schedule:
            task.pop('product', None)

        # ====================================================================
        # Calculate Deadline Violations
        # ====================================================================
        # Check which orders exceeded their deadlines and by how much

        deadline_violations = []
        total_violations = 0

        for oid, oinfo in order_info.items():
            # Get the violation variable value (hours late)
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

        # ====================================================================
        # Determine Final Status
        # ====================================================================
        # OPTIMAL: Found proven optimal solution with no violations
        # FEASIBLE: Found good solution with no violations (may not be optimal)
        # FEASIBLE_WITH_VIOLATIONS: Found solution but some deadlines missed

        if total_violations > 0:
            result_status = 'FEASIBLE_WITH_VIOLATIONS'
        else:
            result_status = 'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE'

        # ====================================================================
        # Return Success Result
        # ====================================================================
        result = {
            'status': result_status,
            'makespan': solver.Value(makespan) if all_tasks else 0,
            'schedule': schedule,
            'start_datetime': start_datetime.strftime('%Y-%m-%d %H:%M'),
            'deadline_violations': deadline_violations,
            'total_violation_hours': total_violations
        }
    else:
        # ====================================================================
        # STEP 12: Handle Solver Failure
        # ====================================================================
        # The solver could not find a solution. Provide diagnostics to help
        # the user understand why and how to fix the problem.

        print(f"\n[SOLVER FAILED]")
        print(f"Status: {solver.StatusName(status)}")

        # Provide detailed diagnostics based on failure type
        if status == cp_model.INFEASIBLE:
            # INFEASIBLE: No solution exists that satisfies all constraints
            # This usually means the problem is over-constrained
            print("Problem is INFEASIBLE - constraints cannot be satisfied")
            print("Possible causes:")
            print(f"  - Total work ({total_work}h) too large for machine capacity")
            print(f"  - Setup time constraints too restrictive")
            print(f"  - Precedence constraints create circular dependencies")
            print(f"  - Deadlines too tight (even with soft constraints)")

        elif status == cp_model.MODEL_INVALID:
            # MODEL_INVALID: The model itself has errors
            # This is usually a programming error, not a data issue
            print("Model is INVALID - check constraint definitions")
            print("This indicates a bug in the model construction code")

        elif status == cp_model.UNKNOWN:
            # UNKNOWN: Solver timed out or hit resource limits
            # The problem might be solvable with more time or smaller input
            print("Status UNKNOWN - solver may have timed out or hit resource limits")
            print(f"  Consider: reducing orders, increasing time limit, or simplifying setup times")

        # Return failure result
        result = {
            'status': 'INFEASIBLE',
            'message': f'Solver status: {solver.StatusName(status)}. Check console for details.'
        }

    return result

