import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .graph_compiler import compile_graph


def canvas(request):
    """Render the playground canvas page."""
    return render(request, 'playground/canvas.html', {
        'user_type': request.GET.get('type', 'developer'),
    })


@csrf_exempt
def compile_graph_view(request):
    """API endpoint to compile a canvas graph."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        canvas_json = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    result = compile_graph(canvas_json)
    status = 200 if result.get('success') else 400
    return JsonResponse(result, status=status)
