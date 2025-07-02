# management/base_access_views.py

from rest_framework.generics import GenericAPIView
from .permissions import *

class BaseProjectAccessView(GenericAPIView):
    permission_classes = [IsProjectParticipant]

class BaseAdminAccessView(GenericAPIView):
    permission_classes = [IsAdmin]

class BaseProjectLeaderAccessView(GenericAPIView):
    permission_classes = [IsProjectLeader]

class BaseAssignerAccessView(GenericAPIView):
    permission_classes = [IsAssigner]

class BaseCheckCanAssignView(GenericAPIView):
    permission_classes = [CanAssign]

class BaseCheckNotOrdinaryUserView(GenericAPIView):
    permission_classes = [CanAssignOrAdmin]
