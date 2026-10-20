"""
Context processors for API Sentinel.
Makes user project list and active project context available across all templates.
"""

def global_project_context(request):
    """
    Supplies the user's projects and the currently active project to all templates.
    """
    if not request.user.is_authenticated:
        return {
            'user_projects': [],
            'active_project': None,
            'active_project_id': None,
        }

    # Avoid circular import by importing Project inside function
    from core.models import Project

    projects = Project.objects.filter(owner=request.user).order_by('name')
    active_project_id = request.GET.get('project') or request.session.get('active_project_id')
    active_project = None

    if active_project_id:
        try:
            active_project = projects.get(id=active_project_id)
            request.session['active_project_id'] = str(active_project.id)
        except (Project.DoesNotExist, ValueError):
            request.session.pop('active_project_id', None)
            active_project = None

    return {
        'user_projects': projects,
        'active_project': active_project,
        'active_project_id': active_project.id if active_project else None,
    }
