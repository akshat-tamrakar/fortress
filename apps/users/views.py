from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class UserListCreateView(APIView):
    """GET /v1/users - List users, POST /v1/users - Create user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # TODO: Implement in task 8.1
        pass

    def post(self, request):
        # TODO: Implement in task 8.1
        pass


class UserDetailView(APIView):
    """GET/PUT/DELETE /v1/users/{id}"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # TODO: Implement in task 8.2
        pass

    def put(self, request, user_id):
        # TODO: Implement in task 8.2
        pass

    def delete(self, request, user_id):
        # TODO: Implement in task 8.2
        pass


class UserDisableView(APIView):
    """POST /v1/users/{id}/disable"""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        # TODO: Implement in task 8.3
        pass


class UserEnableView(APIView):
    """POST /v1/users/{id}/enable"""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        # TODO: Implement in task 8.3
        pass


class MeView(APIView):
    """GET/PUT /v1/me - Self-service profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # TODO: Implement in task 8.4
        pass

    def put(self, request):
        # TODO: Implement in task 8.4
        pass


class MFASetupView(APIView):
    """POST /v1/me/mfa/setup - Setup MFA"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # TODO: Implement in task 8.4
        pass
