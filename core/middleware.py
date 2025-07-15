class ThemeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            theme = request.user.theme_preference
        else:
            theme = request.session.get('theme', 'classic')
        
        request.theme = theme
        response = self.get_response(request)
        return response
