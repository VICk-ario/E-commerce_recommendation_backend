from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import MLModel
from .serializers import MLModelSerializer, TrainingRequestSerializer
from apps.stores.authentication import StoreAPIKeyAuthentication
from .services import MLService

class MLModelViewSet(viewsets.ModelViewSet):
    authentication_classes = [StoreAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = MLModelSerializer

    def get_queryset(self):
        return MLModel.objects.filter(store=self.request.auth)

    def perform_create(self, serializer):
        serializer.save(store=self.request.auth)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        model = self.get_object()
        model.activate()
        return Response({'status': 'activated'})

    @action(detail=False, methods=['post'])
    def train(self, request):
        serializer = TrainingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = MLService(request.auth)
        task_id = service.train_model(**serializer.validated_data)
        
        return Response({'task_id': task_id, 'status': 'training_started'})

    @action(detail=False, methods=['get'])
    def predictions(self, request):
        user_id = request.query_params.get('user_id')
        product_id = request.query_params.get('product_id')
        
        service = MLService(request.auth)
        predictions = service.get_predictions(user_id, product_id)
        
        return Response(predictions)