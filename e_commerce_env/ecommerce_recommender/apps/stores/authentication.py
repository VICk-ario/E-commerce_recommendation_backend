from rest_framework import authentication
from rest_framework import exceptions
from apps.stores.models import Store

class StoreAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate using store API key in X-API-Key header
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
        
        try:
            store = Store.objects.get(api_key=api_key, is_active=True)
        except Store.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key or store is inactive')
        
        return (store, None)