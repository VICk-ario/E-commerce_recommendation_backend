#!/usr/bin/env python
import os
import django
import requests
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recommender.ecommerce_recommender.settings')
django.setup()

from apps.stores.models import Store
from apps.users.models import User
from apps.products.models import Product
from apps.interactions.models import Interaction, UserInteractionSession

def test_interactions_models():
    """Test Interactions models and relationships"""
    print("=== Testing Interactions Models ===")
    
    store = Store.objects.first()
    if not store:
        print("❌ No store found. Please create a store first.")
        return
    
    # Create test user
    user, created = User.objects.get_or_create(
        store=store,
        user_id="test_user_interactions",
        defaults={
            'email': "test_interactions@example.com",
            'first_name': "Test",
            'last_name': "Interactions"
        }
    )
    
    # Create test product
    product, created = Product.objects.get_or_create(
        store=store,
        product_id="test_product_interactions",
        defaults={
            'title': "Test Product for Interactions",
            'category': "Electronics",
            'price': 299.99
        }
    )
    
    # Create user session
    session = UserInteractionSession.objects.create(
        store=store,
        user=user,
        session_id="test_session_001",
        landing_page="https://store.com/home",
        user_agent="Mozilla/5.0 (Test Browser)"
    )
    
    print(f"✅ Session created: {session.session_id}")
    
    # Create various interactions
    interactions = [
        {
            'interaction_type': 'view',
            'page_url': 'https://store.com/products/1',
            'time_on_page': 45
        },
        {
            'interaction_type': 'detail_view',
            'page_url': 'https://store.com/products/1/detail',
            'time_on_page': 120
        },
        {
            'interaction_type': 'cart_add',
            'value': 299.99
        },
        {
            'interaction_type': 'purchase',
            'value': 299.99
        }
    ]
    
    for i, interaction_data in enumerate(interactions):
        interaction = Interaction.objects.create(
            store=store,
            user=user,
            product=product,
            session=session,
            **interaction_data
        )
        print(f"✅ Interaction {i+1} created: {interaction.interaction_type}")
    
    # Test session metrics update
    session.update_session_metrics()
    print(f"✅ Session metrics updated - Views: {session.page_views}, Purchased: {session.purchased}")
    
    # Test user engagement update
    user.update_engagement_metrics()
    print(f"✅ User engagement updated - Total interactions: {user.total_interactions}, Purchases: {user.total_purchases}")
    
    return store, user, session

def test_interactions_api(api_key):
    """Test Interactions API endpoints"""
    print("\n=== Testing Interactions API ===")
    
    base_url = "http://localhost:8000/api"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Test interaction creation
        interaction_data = {
            "user_id": "test_user_interactions",
            "session_id": "test_session_api",
            "product_id": "test_product_interactions",
            "interaction_type": "view",
            "page_url": "https://store.com/products/1",
            "time_on_page": 30
        }
        
        response = requests.post(f"{base_url}/interactions/", json=interaction_data, headers=headers)
        if response.status_code == 201:
            print("✅ POST /api/interactions/ - SUCCESS")
        else:
            print(f"❌ POST /api/interactions/ - FAILED: {response.status_code}")
        
        # Test bulk interactions
        bulk_data = {
            "interactions": [
                {
                    "user_id": "test_user_interactions",
                    "session_id": "test_session_api",
                    "product_id": "test_product_interactions",
                    "interaction_type": "click",
                    "page_url": "https://store.com/products/1"
                },
                {
                    "user_id": "test_user_interactions",
                    "session_id": "test_session_api",
                    "interaction_type": "search",
                    "search_query": "electronics",
                    "search_results_count": 15
                }
            ]
        }
        
        response = requests.post(f"{base_url}/interactions/bulk_create/", json=bulk_data, headers=headers)
        if response.status_code == 201:
            print("✅ POST /api/interactions/bulk_create/ - SUCCESS")
        else:
            print(f"❌ POST /api/interactions/bulk_create/ - FAILED: {response.status_code}")
        
        # Test interaction analytics
        response = requests.get(f"{base_url}/interactions/analytics/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ GET /api/interactions/analytics/ - SUCCESS")
            print(f"   Total interactions: {data['overall_stats']['total_interactions']}")
        else:
            print(f"❌ GET /api/interactions/analytics/ - FAILED: {response.status_code}")
        
        # Test popular products
        response = requests.get(f"{base_url}/interactions/popular_products/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("✅ GET /api/interactions/popular_products/ - SUCCESS")
            if data['popular_products']:
                print(f"   Most popular: {data['popular_products'][0]['product__title']}")
        else:
            print(f"❌ GET /api/interactions/popular_products/ - FAILED: {response.status_code}")
        
        # Test session creation
        session_data = {
            "session_id": "test_session_api_2",
            "user_id": "test_user_interactions",
            "landing_page": "https://store.com/home",
            "user_agent": "Mozilla/5.0 (API Test)"
        }
        
        response = requests.post(f"{base_url}/sessions/", json=session_data, headers=headers)
        if response.status_code == 201:
            print("✅ POST /api/sessions/ - SUCCESS")
        else:
            print(f"❌ POST /api/sessions/ - FAILED: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure 'python manage.py runserver' is running.")
    except Exception as e:
        print(f"❌ API test error: {e}")

if __name__ == "__main__":
    # Get API key from first store
    store = Store.objects.first()
    if store:
        api_key = store.api_key
        store, user, session = test_interactions_models()
        test_interactions_api(api_key)
        
        print("\n=== Test Summary ===")
        print("Check admin panel at http://localhost:8000/admin/ to verify interactions were created")
        print(f"Test user: {user.user_id}")
        print(f"Test session: {session.session_id}")
        print(f"Total interactions created: {user.interactions.count()}")
    else:
        print("❌ No stores found. Please create a store first.")