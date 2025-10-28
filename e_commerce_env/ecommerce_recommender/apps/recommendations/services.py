import numpy as np
import pandas as pd
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
import random
from typing import List, Dict, Any

from apps.users.models import User
from apps.products.models import Product
from apps.interactions.models import Interaction
from .models import Recommendation, SimilarProduct, TrendingProduct

class BaseRecommendationEngine:
    """Base class for all recommendation engines"""
    
    def __init__(self, store):
        self.store = store
    
    def get_recommendations(self, user_id=None, session_id=None, max_results=10, context=None):
        """Get recommendations - to be implemented by subclasses"""
        raise NotImplementedError
    
    def explain_recommendation(self, product, user_id=None, session_id=None):
        """Generate human-readable explanation for recommendation"""
        return f"Recommended based on {self.__class__.__name__}"

class PopularityBasedEngine(BaseRecommendationEngine):
    """Popularity-based recommendations"""
    
    def get_recommendations(self, user_id=None, session_id=None, max_results=10, context=None):
        # Get popular products based on interactions in last 30 days
        since_date = timezone.now() - timedelta(days=30)
        
        popular_products = Interaction.objects.filter(
            store=self.store,
            created_at__gte=since_date,
            product__isnull=False
        ).values('product').annotate(
            popularity_score=Count('id') + Count('id', filter=Q(interaction_type='purchase')) * 5
        ).order_by('-popularity_score')[:max_results * 2]  # Get extra for filtering
        
        recommendations = []
        for idx, item in enumerate(popular_products[:max_results]):
            try:
                product = Product.objects.get(id=item['product'])
                score = item['popularity_score'] / (idx + 1)  # Normalize score
                
                recommendations.append({
                    'product': product,
                    'score': min(score / 100, 1.0),  # Normalize to 0-1
                    'rank': idx + 1,
                    'explanation': f"Popular item with {item['popularity_score']} interactions"
                })
            except Product.DoesNotExist:
                continue
        
        return recommendations

class CollaborativeFilteringEngine(BaseRecommendationEngine):
    """Simple collaborative filtering using user similarity"""
    
    def get_recommendations(self, user_id=None, session_id=None, max_results=10, context=None):
        if not user_id:
            return []  # Collaborative filtering requires user history
        
        try:
            user = User.objects.get(store=self.store, user_id=user_id)
        except User.DoesNotExist:
            return []
        
        # Get users with similar interaction patterns
        user_interactions = set(user.interactions.values_list('product_id', flat=True))
        
        if not user_interactions:
            return []  # No user history
        
        # Find similar users (simplified implementation)
        similar_users = User.objects.filter(
            store=self.store,
            interactions__product_id__in=user_interactions
        ).exclude(id=user.id).annotate(
            similarity=Count('interactions__product_id', filter=Q(interactions__product_id__in=user_interactions))
        ).order_by('-similarity')[:10]
        
        # Get products from similar users that target user hasn't interacted with
        similar_user_products = Interaction.objects.filter(
            store=self.store,
            user__in=similar_users
        ).exclude(product_id__in=user_interactions).values('product').annotate(
            score=Count('id') + Count('id', filter=Q(interaction_type='purchase')) * 3
        ).order_by('-score')[:max_results]
        
        recommendations = []
        for idx, item in enumerate(similar_user_products):
            try:
                product = Product.objects.get(id=item['product'])
                recommendations.append({
                    'product': product,
                    'score': min(item['score'] / 10, 1.0),
                    'rank': idx + 1,
                    'explanation': "Users with similar interests also liked this"
                })
            except Product.DoesNotExist:
                continue
        
        return recommendations

class ContentBasedEngine(BaseRecommendationEngine):
    """Content-based recommendations using product attributes"""
    
    def get_recommendations(self, user_id=None, session_id=None, max_results=10, context=None):
        if user_id:
            # User-based content filtering
            return self._get_user_based_recommendations(user_id, max_results)
        elif context and context.get('product_id'):
            # Similar products based on current product
            return self._get_similar_products(context['product_id'], max_results)
        else:
            return []
    
    def _get_user_based_recommendations(self, user_id, max_results):
        try:
            user = User.objects.get(store=self.store, user_id=user_id)
        except User.DoesNotExist:
            return []
        
        # Get user's preferred categories from interactions
        user_categories = user.interactions.filter(
            product__isnull=False
        ).values('product__category').annotate(
            weight=Count('id') + Count('id', filter=Q(interaction_type='purchase')) * 2
        ).order_by('-weight')[:5]
        
        if not user_categories:
            return []
        
        preferred_categories = [cat['product__category'] for cat in user_categories]
        
        # Recommend products from preferred categories
        recommendations = []
        products = Product.objects.filter(
            store=self.store,
            category__in=preferred_categories
        ).exclude(
            interactions__user=user  # Exclude already interacted products
        )[:max_results * 2]
        
        for idx, product in enumerate(products[:max_results]):
            # Simple scoring based on category match
            category_weight = next(
                (cat['weight'] for cat in user_categories if cat['product__category'] == product.category),
                1
            )
            score = min(category_weight / 10, 1.0)
            
            recommendations.append({
                'product': product,
                'score': score,
                'rank': idx + 1,
                'explanation': f"Matches your interest in {product.category}"
            })
        
        return recommendations
    
    def _get_similar_products(self, product_id, max_results):
        try:
            source_product = Product.objects.get(store=self.store, product_id=product_id)
        except Product.DoesNotExist:
            return []
        
        # Find similar products by category and price range
        price_range = source_product.price * 0.5 if source_product.price else 100
        
        similar_products = Product.objects.filter(
            store=self.store,
            category=source_product.category,
            price__range=(
                (source_product.price - price_range) if source_product.price else 0,
                (source_product.price + price_range) if source_product.price else 1000
            )
        ).exclude(product_id=product_id)[:max_results]
        
        recommendations = []
        for idx, product in enumerate(similar_products):
            # Calculate similarity score
            score = 0.7  # Base score for same category
            
            if source_product.price and product.price:
                price_similarity = 1 - abs(source_product.price - product.price) / source_product.price
                score += price_similarity * 0.3
            
            recommendations.append({
                'product': product,
                'score': min(score, 1.0),
                'rank': idx + 1,
                'explanation': f"Similar to {source_product.title}"
            })
        
        return recommendations

class HybridRecommendationEngine(BaseRecommendationEngine):
    """Hybrid engine combining multiple algorithms"""
    
    def __init__(self, store):
        super().__init__(store)
        self.engines = {
            'popularity': PopularityBasedEngine(store),
            'collaborative': CollaborativeFilteringEngine(store),
            'content': ContentBasedEngine(store),
        }
    
    def get_recommendations(self, user_id=None, session_id=None, max_results=10, context=None):
        all_recommendations = {}
        
        # Get recommendations from all engines
        for engine_name, engine in self.engines.items():
            try:
                engine_recommendations = engine.get_recommendations(
                    user_id=user_id,
                    session_id=session_id,
                    max_results=max_results * 2,
                    context=context
                )
                
                for rec in engine_recommendations:
                    product_id = rec['product'].id
                    if product_id not in all_recommendations:
                        all_recommendations[product_id] = {
                            'product': rec['product'],
                            'scores': {},
                            'explanations': []
                        }
                    
                    all_recommendations[product_id]['scores'][engine_name] = rec['score']
                    all_recommendations[product_id]['explanations'].append(rec['explanation'])
                    
            except Exception as e:
                print(f"Error in {engine_name} engine: {e}")
                continue
        
        # Combine scores using weighted average
        final_recommendations = []
        for product_id, data in all_recommendations.items():
            # Weight different algorithms (could be configurable)
            weights = {
                'collaborative': 0.4,
                'content': 0.35,
                'popularity': 0.25
            }
            
            combined_score = 0
            total_weight = 0
            
            for engine_name, score in data['scores'].items():
                weight = weights.get(engine_name, 0.1)
                combined_score += score * weight
                total_weight += weight
            
            if total_weight > 0:
                combined_score /= total_weight
            
            final_recommendations.append({
                'product': data['product'],
                'score': combined_score,
                'explanations': data['explanations']
            })
        
        # Sort by score and limit results
        final_recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Add rank and final explanation
        for idx, rec in enumerate(final_recommendations[:max_results]):
            rec['rank'] = idx + 1
            rec['explanation'] = self._combine_explanations(rec['explanations'])
        
        return final_recommendations[:max_results]
    
    def _combine_explanations(self, explanations):
        """Combine multiple explanations into one"""
        if not explanations:
            return "Recommended for you"
        
        # Remove duplicates and take first 2 explanations
        unique_explanations = list(dict.fromkeys(explanations))
        if len(unique_explanations) == 1:
            return unique_explanations[0]
        else:
            return f"{unique_explanations[0]} and {unique_explanations[1].lower()}"

class RecommendationService:
    """Main service for handling recommendations"""
    
    def __init__(self, store):
        self.store = store
        self.engine = HybridRecommendationEngine(store)
    
    def get_recommendations(self, user_id=None, session_id=None, max_results=10, context=None, algorithm=None):
        """Get recommendations for user or session"""
        # Use specific algorithm if requested, otherwise use hybrid
        if algorithm and algorithm != 'hybrid':
            engine_map = {
                'popularity': PopularityBasedEngine,
                'collaborative_filtering': CollaborativeFilteringEngine,
                'content_based': ContentBasedEngine,
            }
            
            if algorithm in engine_map:
                engine = engine_map[algorithm](self.store)
            else:
                engine = self.engine
        else:
            engine = self.engine
        
        recommendations = engine.get_recommendations(
            user_id=user_id,
            session_id=session_id,
            max_results=max_results,
            context=context
        )
        
        # Store recommendations in database
        stored_recommendations = []
        for rec in recommendations:
            stored_rec, created = Recommendation.objects.get_or_create(
                store=self.store,
                user_id=user_id,
                session_id=session_id or '',
                product=rec['product'],
                algorithm=algorithm or 'hybrid',
                defaults={
                    'score': rec['score'],
                    'rank': rec['rank'],
                    'explanation': rec.get('explanation', ''),
                    'context': context or {},
                    'expires_at': timezone.now() + timedelta(hours=24)  # Recommendations expire in 24h
                }
            )
            
            if not created:
                # Update existing recommendation
                stored_rec.score = rec['score']
                stored_rec.rank = rec['rank']
                stored_rec.explanation = rec.get('explanation', '')
                stored_rec.context = context or {}
                stored_rec.expires_at = timezone.now() + timedelta(hours=24)
                stored_rec.save()
            
            stored_recommendations.append(stored_rec)
        
        return stored_recommendations
    
    def get_similar_products(self, product_id, max_results=10):
        """Get similar products for a given product"""
        service = ContentBasedEngine(self.store)
        recommendations = service._get_similar_products(product_id, max_results)
        
        # Store similar products for caching
        for rec in recommendations:
            SimilarProduct.objects.update_or_create(
                store=self.store,
                source_product_id=product_id,
                target_product=rec['product'],
                defaults={
                    'similarity_score': rec['score'],
                    'similarity_type': 'content_based',
                    'features_used': ['category', 'price']
                }
            )
        
        return recommendations
    
    def record_impression(self, recommendation_id):
        """Record that a recommendation was shown to user"""
        try:
            recommendation = Recommendation.objects.get(id=recommendation_id)
            recommendation.increment_shown()
            
            # Update user profile
            if recommendation.user:
                self._update_user_profile(recommendation.user)
                
        except Recommendation.DoesNotExist:
            pass
    
    def record_click(self, recommendation_id):
        """Record that a recommendation was clicked"""
        try:
            recommendation = Recommendation.objects.get(id=recommendation_id)
            recommendation.increment_click()
            
            # Update user profile
            if recommendation.user:
                self._update_user_profile(recommendation.user)
                
        except Recommendation.DoesNotExist:
            pass
    
    def _update_user_profile(self, user):
        """Update user recommendation profile"""
        from .models import UserRecommendationProfile
        
        profile, created = UserRecommendationProfile.objects.get_or_create(
            store=user.store,
            user=user
        )
        
        profile.total_recommendations_shown = user.recommendations.aggregate(
            total=Sum('shown_count')
        )['total'] or 0
        
        profile.total_recommendations_clicked = user.recommendations.aggregate(
            total=Sum('click_count')
        )['total'] or 0
        
        profile.total_recommendations_purchased = user.recommendations.aggregate(
            total=Sum('purchase_count')
        )['total'] or 0
        
        profile.last_recommendation_at = timezone.now()
        profile.update_performance_metrics()