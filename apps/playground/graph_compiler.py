"""Canvas JSON to LangGraph compiler (placeholder)."""

VALID_NODE_TYPES = ['llm', 'tool', 'condition', 'memory', 'human', 'agent']


def validate_canvas(canvas_json):
    """Validate a canvas JSON structure."""
    nodes = canvas_json.get('nodes', [])
    connections = canvas_json.get('connections', [])
    errors = []
    node_ids = set()

    for node in nodes:
        if node.get('type') not in VALID_NODE_TYPES:
            errors.append(f"Invalid node type: {node.get('type')}")
        node_ids.add(node.get('id'))

    for conn in connections:
        if conn.get('from') not in node_ids:
            errors.append(f"Connection from unknown node: {conn.get('from')}")
        if conn.get('to') not in node_ids:
            errors.append(f"Connection to unknown node: {conn.get('to')}")

    return {'valid': len(errors) == 0, 'errors': errors}


def compile_graph(canvas_json):
    """Compile a canvas JSON into a graph structure."""
    validation = validate_canvas(canvas_json)
    if not validation['valid']:
        return {'success': False, 'errors': validation['errors']}

    # Placeholder compilation
    compiled = {
        'success': True,
        'graph': {
            'nodes': len(canvas_json.get('nodes', [])),
            'edges': len(canvas_json.get('connections', [])),
            'compiled_at': 'now',
            'status': 'ready',
        }
    }
    return compiled
