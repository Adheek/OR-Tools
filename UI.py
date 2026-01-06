import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from or_tools import solve_schedule
from demodata import get_demo_data
from large_demodata import get_large_demo_data, get_extreme_large_demo_data
from time import time as get_time

st.set_page_config(page_title="Production Scheduler", layout="wide")

st.title("Production Scheduler - OR-Tools Optimizer")

# Initialize session state for data persistence
if 'machines' not in st.session_state:
    st.session_state.machines = []
if 'products' not in st.session_state:
    st.session_state.products = []
if 'setup_times' not in st.session_state:
    st.session_state.setup_times = {}
if 'orders' not in st.session_state:
    st.session_state.orders = []

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Machines", "Products", "Setup Times", "Orders", "Schedule"])

# ==================== TAB 1: MACHINES ====================
with tab1:
    st.header("Define Machines")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("machine_form"):
            machine_name = st.text_input("Machine Name", placeholder="e.g., Machine A")
            operations_input = st.text_input("Operations (comma-separated)", placeholder="e.g., cutting, drilling, painting")

            if st.form_submit_button("Add Machine"):
                if machine_name and operations_input:
                    operations = [op.strip() for op in operations_input.split(',')]
                    st.session_state.machines.append({
                        'name': machine_name,
                        'operations': operations
                    })
                    st.success(f"Machine '{machine_name}' added!")
                    st.rerun()
                else:
                    st.error("Please fill all fields")

    with col2:
        st.subheader("Current Machines")
        if st.session_state.machines:
            for idx, machine in enumerate(st.session_state.machines):
                with st.expander(f"{machine['name']}"):
                    st.write(f"**Operations:** {', '.join(machine['operations'])}")
                    if st.button(f"Remove", key=f"remove_machine_{idx}"):
                        st.session_state.machines.pop(idx)
                        st.rerun()
        else:
            st.info("No machines added yet")

# ==================== TAB 2: PRODUCTS ====================
with tab2:
    st.header("Define Products")

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("product_form"):
            product_name = st.text_input("Product Name", placeholder="e.g., Product X")
            st.subheader("Tasks")

            num_tasks = st.number_input("Number of Tasks", min_value=1, max_value=10, value=1)
            tasks = []

            for i in range(num_tasks):
                st.markdown(f"**Task {i+1}**")
                col_a, col_b = st.columns(2)
                with col_a:
                    operation = st.text_input(f"Operation", key=f"op_{i}", placeholder="e.g., cutting")
                with col_b:
                    duration = st.number_input(f"Duration (hours)", key=f"dur_{i}", min_value=1, value=1)
                tasks.append({'operation': operation, 'duration': duration})

            if st.form_submit_button("Add Product"):
                if product_name and all(t['operation'] for t in tasks):
                    st.session_state.products.append({
                        'name': product_name,
                        'tasks': tasks
                    })
                    st.success(f"Product '{product_name}' added!")
                    st.rerun()
                else:
                    st.error("Please fill all fields")

    with col2:
        st.subheader("Current Products")
        if st.session_state.products:
            for idx, product in enumerate(st.session_state.products):
                with st.expander(f"{product['name']}"):
                    for task in product['tasks']:
                        st.write(f"- {task['operation']}: {task['duration']}h")
                    if st.button(f"Remove", key=f"remove_product_{idx}"):
                        st.session_state.products.pop(idx)
                        st.rerun()
        else:
            st.info("No products added yet")

# ==================== TAB 3: SETUP TIMES ====================
with tab3:
    st.header("Define Setup Times")
    st.write("Setup times represent the time needed to switch from one product to another on the same machine.")

    if len(st.session_state.products) >= 2:
        col1, col2 = st.columns([2, 1])

        with col1:
            with st.form("setup_time_form"):
                product_names = [p['name'] for p in st.session_state.products]
                from_product = st.selectbox("From Product", product_names)
                to_product = st.selectbox("To Product", product_names)
                setup_time = st.number_input("Setup Time (hours)", min_value=0, value=0)

                if st.form_submit_button("Add Setup Time"):
                    if from_product != to_product:
                        key = f"{from_product}-{to_product}"
                        st.session_state.setup_times[key] = setup_time
                        st.success(f"Setup time added: {from_product} → {to_product} = {setup_time}h")
                        st.rerun()
                    else:
                        st.error("From and To products must be different")

        with col2:
            st.subheader("Current Setup Times")
            if st.session_state.setup_times:
                for key, time in st.session_state.setup_times.items():
                    from_p, to_p = key.split('-')
                    st.write(f"{from_p} → {to_p}: {time}h")
            else:
                st.info("No setup times defined")
    else:
        st.info("Please add at least 2 products first")

# ==================== TAB 4: ORDERS ====================
with tab4:
    st.header("Define Orders")

    if st.session_state.products:
        col1, col2 = st.columns([2, 1])

        with col1:
            with st.form("order_form"):
                product_names = [p['name'] for p in st.session_state.products]
                order_product = st.selectbox("Product", product_names)
                quantity = st.number_input("Quantity", min_value=1, value=1)
                deadline = st.number_input("Deadline (hours from start)", min_value=1, value=100)

                if st.form_submit_button("Add Order"):
                    st.session_state.orders.append({
                        'product': order_product,
                        'quantity': quantity,
                        'deadline': deadline
                    })
                    st.success(f"Order added: {quantity} x {order_product}")
                    st.rerun()

        with col2:
            st.subheader("Current Orders")
            if st.session_state.orders:
                for idx, order in enumerate(st.session_state.orders):
                    with st.expander(f"Order {idx+1}"):
                        st.write(f"**Product:** {order['product']}")
                        st.write(f"**Quantity:** {order['quantity']}")
                        st.write(f"**Deadline:** {order['deadline']}h")
                        if st.button(f"Remove", key=f"remove_order_{idx}"):
                            st.session_state.orders.pop(idx)
                            st.rerun()
            else:
                st.info("No orders added yet")
    else:
        st.info("Please add products first")

# ==================== TAB 5: SCHEDULE ====================
with tab5:
    st.header("Generate Schedule")

    col1, col2 = st.columns([1, 2])

    with col1:
        start_datetime = st.date_input("Production Start Date", value=datetime.now())
        start_time_input = st.time_input("Production Start Time", value=datetime.now().time())

        start_datetime_combined = datetime.combine(start_datetime, start_time_input)

        st.write("---")
        st.write(f"**Machines:** {len(st.session_state.machines)}")
        st.write(f"**Products:** {len(st.session_state.products)}")
        st.write(f"**Orders:** {len(st.session_state.orders)}")

        if st.button("Run Scheduler", type="primary", width="stretch"):
            if not st.session_state.machines:
                st.error("Please add at least one machine")
            elif not st.session_state.products:
                st.error("Please add at least one product")
            elif not st.session_state.orders:
                st.error("Please add at least one order")
            else:
                with st.spinner("Solving schedule..."):
                    start_solve_time = get_time()
                    result = solve_schedule(
                        st.session_state.machines,
                        st.session_state.products,
                        st.session_state.setup_times,
                        st.session_state.orders,
                        start_datetime_combined.isoformat()
                    )
                    end_solve_time = get_time()
                    solve_duration = end_solve_time - start_solve_time
                    result['solve_time'] = solve_duration
                    st.session_state.result = result

    with col2:
        if 'result' in st.session_state:
            result = st.session_state.result

            if result['status'] in ['OPTIMAL', 'FEASIBLE', 'FEASIBLE_WITH_VIOLATIONS']:
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if result['status'] == 'FEASIBLE_WITH_VIOLATIONS':
                        st.warning(f"Status: {result['status']}")
                    else:
                        st.success(f"Status: {result['status']}")
                with col_b:
                    st.metric("Total Makespan", f"{result['makespan']} hours")
                with col_c:
                    solve_time = result.get('solve_time', 0)
                    st.metric("Solve Time", f"{solve_time:.2f} seconds")

                # Display deadline violations if any
                if result.get('deadline_violations'):
                    st.error(f"⚠️ Deadline Violations Detected: {result.get('total_violation_hours', 0)} total hours late")

                    st.subheader("Deadline Violations")
                    violations_df = pd.DataFrame(result['deadline_violations'])
                    st.dataframe(violations_df, width="stretch")

                    st.info("💡 The schedule shown below exceeds some deadlines. Consider: reducing order quantities, extending deadlines, or adding more machines.")

                # Display schedule table
                st.subheader("Schedule Details")
                df = pd.DataFrame(result['schedule'])
                st.dataframe(df, width="stretch")

                # Create Gantt Chart
                st.subheader("Gantt Chart Visualization")

                if result['schedule']:
                    # Create Gantt chart using shapes
                    fig = go.Figure()

                    # Color map for products
                    products_list = list(set([task['order'] for task in result['schedule']]))
                    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                    color_map = {product: colors[i % len(colors)] for i, product in enumerate(products_list)}

                    # Get unique machines for Y-axis
                    machines_list = sorted(list(set([task['machine'] for task in result['schedule']])))
                    machine_to_y = {machine: i for i, machine in enumerate(machines_list)}

                    # Add each task as a rectangle
                    for task in result['schedule']:
                        start_dt = datetime.strptime(task['start_datetime'], '%Y-%m-%d %H:%M')
                        end_dt = datetime.strptime(task['end_datetime'], '%Y-%m-%d %H:%M')
                        machine_y = machine_to_y[task['machine']]

                        # Add rectangle for task
                        fig.add_shape(
                            type="rect",
                            x0=start_dt,
                            x1=end_dt,
                            y0=machine_y - 0.4,
                            y1=machine_y + 0.4,
                            fillcolor=color_map[task['order']],
                            line=dict(color="black", width=1),
                        )

                        # Add text annotation
                        fig.add_annotation(
                            x=start_dt + (end_dt - start_dt) / 2,
                            y=machine_y,
                            text=f"{task['order']}<br>{task['operation']}",
                            showarrow=False,
                            font=dict(color="white", size=10),
                            xanchor="center",
                            yanchor="middle"
                        )

                    # Add invisible scatter trace for hover info
                    for task in result['schedule']:
                        start_dt = datetime.strptime(task['start_datetime'], '%Y-%m-%d %H:%M')
                        end_dt = datetime.strptime(task['end_datetime'], '%Y-%m-%d %H:%M')
                        machine_y = machine_to_y[task['machine']]
                        mid_time = start_dt + (end_dt - start_dt) / 2

                        fig.add_trace(go.Scatter(
                            x=[mid_time],
                            y=[machine_y],
                            mode='markers',
                            marker=dict(size=0.1, opacity=0),
                            hovertemplate=(
                                f"<b>{task['order']}</b><br>"
                                f"Machine: {task['machine']}<br>"
                                f"Operation: {task['operation']}<br>"
                                f"Start: {task['start_datetime']}<br>"
                                f"End: {task['end_datetime']}<br>"
                                f"Duration: {task['duration']}h<br>"
                                f"Setup Time: {task.get('setup_time', 0)}h<br>"
                                "<extra></extra>"
                            ),
                            showlegend=False
                        ))

                    fig.update_layout(
                        title="Production Schedule - Gantt Chart",
                        xaxis_title="Time",
                        yaxis_title="Machines",
                        height=max(400, len(machines_list) * 80),
                        showlegend=False,
                        xaxis=dict(
                            showgrid=True,
                            type='date',
                            tickformat='%Y-%m-%d %H:%M'
                        ),
                        yaxis=dict(
                            showgrid=True,
                            tickmode='array',
                            tickvals=list(range(len(machines_list))),
                            ticktext=machines_list,
                            range=[-0.5, len(machines_list) - 0.5]
                        )
                    )

                    st.plotly_chart(fig, width="stretch")

            else:
                st.error(f"Status: {result['status']}")
                st.warning(result.get('message', 'No solution found'))
        else:
            st.info("Configure machines, products, and orders, then click 'Run Scheduler'")

# Sidebar with quick stats
with st.sidebar:
    st.header("Quick Stats")
    st.metric("Machines", len(st.session_state.machines))
    st.metric("Products", len(st.session_state.products))
    st.metric("Setup Times", len(st.session_state.setup_times))
    st.metric("Orders", len(st.session_state.orders))

    st.write("---")

    if st.button("Load Demo Data", type="primary", width="stretch"):
        demo_data = get_demo_data()
        st.session_state.machines = demo_data['machines']
        st.session_state.products = demo_data['products']
        st.session_state.setup_times = demo_data['setup_times']
        st.session_state.orders = demo_data['orders']
        if 'result' in st.session_state:
            del st.session_state.result
        st.success("Demo data loaded successfully!")
        st.rerun()

    if st.button("Load Large Demo Data", type="primary", width="stretch"):
        with st.spinner("Generating large random data..."):
            large_data = get_large_demo_data()
            st.session_state.machines = large_data['machines']
            st.session_state.products = large_data['products']
            st.session_state.setup_times = large_data['setup_times']
            st.session_state.orders = large_data['orders']
            if 'result' in st.session_state:
                del st.session_state.result
        st.success("Large demo data loaded! Check terminal for details.")
        st.rerun()

    if st.button("Load EXTREME Large Data", type="primary", width="stretch"):
        with st.spinner("Generating extreme large data..."):
            extreme_data = get_extreme_large_demo_data()
            st.session_state.machines = extreme_data['machines']
            st.session_state.products = extreme_data['products']
            st.session_state.setup_times = extreme_data['setup_times']
            st.session_state.orders = extreme_data['orders']
            if 'result' in st.session_state:
                del st.session_state.result
        st.warning("EXTREME data loaded! Solving may take 10+ seconds or timeout.")
        st.rerun()

    st.write("---")

    if st.button("Clear All Data", type="secondary", width="stretch"):
        st.session_state.machines = []
        st.session_state.products = []
        st.session_state.setup_times = {}
        st.session_state.orders = []
        if 'result' in st.session_state:
            del st.session_state.result
        st.rerun()
