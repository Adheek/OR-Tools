"""
Demo data for Production Scheduler
Contains sample machines, products, setup times, and orders
"""

# Toggle to alternate between possible and impossible deadlines
_deadline_toggle = {'impossible': False}

def get_demo_data():
    """
    Returns a dictionary with demo data for the production scheduler
    Alternates between possible and impossible deadlines on each call
    """

    # Toggle deadline mode
    _deadline_toggle['impossible'] = not _deadline_toggle['impossible']
    impossible_mode = _deadline_toggle['impossible']

    print(f"\n[DEMO DATA] Mode: {'IMPOSSIBLE DEADLINES' if impossible_mode else 'POSSIBLE DEADLINES'}")

    # Demo Machines
    machines = [
        {
            'name': 'Machine A',
            'operations': ['cutting', 'drilling']
        },
        {
            'name': 'Machine B',
            'operations': ['painting', 'assembly']
        },
        {
            'name': 'Machine C',
            'operations': ['welding', 'finishing']
        }
    ]

    # Demo Products
    products = [
        {
            'name': 'Product X',
            'tasks': [
                {'operation': 'cutting', 'duration': 2},
                {'operation': 'welding', 'duration': 3},
                {'operation': 'painting', 'duration': 2}
            ]
        },
        {
            'name': 'Product Y',
            'tasks': [
                {'operation': 'drilling', 'duration': 2},
                {'operation': 'finishing', 'duration': 1},
                {'operation': 'assembly', 'duration': 3}
            ]
        },
        {
            'name': 'Product Z',
            'tasks': [
                {'operation': 'cutting', 'duration': 1},
                {'operation': 'drilling', 'duration': 2},
                {'operation': 'welding', 'duration': 2},
                {'operation': 'painting', 'duration': 2}
            ]
        }
    ]

    # Demo Setup Times (changeover times between products)
    setup_times = {
        'Product X-Product Y': 1,
        'Product Y-Product X': 1,
        'Product X-Product Z': 2,
        'Product Z-Product X': 2,
        'Product Y-Product Z': 1,
        'Product Z-Product Y': 1
    }

    # Demo Orders with alternating deadlines
    if impossible_mode:
        # Impossible deadlines - very tight
        orders = [
            {
                'product': 'Product X',
                'quantity': 2,
                'deadline': 10  # Too tight (needs ~14h)
            },
            {
                'product': 'Product Y',
                'quantity': 3,
                'deadline': 15  # Too tight (needs ~18h)
            },
            {
                'product': 'Product Z',
                'quantity': 1,
                'deadline': 5   # Too tight (needs ~7h)
            }
        ]
    else:
        # Possible deadlines - reasonable
        orders = [
            {
                'product': 'Product X',
                'quantity': 2,
                'deadline': 50
            },
            {
                'product': 'Product Y',
                'quantity': 3,
                'deadline': 60
            },
            {
                'product': 'Product Z',
                'quantity': 1,
                'deadline': 40
            }
        ]

    return {
        'machines': machines,
        'products': products,
        'setup_times': setup_times,
        'orders': orders
    }
