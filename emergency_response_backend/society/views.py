from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Society
from users.permissions import IsAdminRole
from users.permissions import IsAdminOrSubAdmin
from rest_framework import status
from django.core.mail import send_mail
from .models import Flat
from users.permissions import IsSecurity
from users.permissions import IsSubAdminOrSecurity

class SocietyView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSubAdmin]
    def post(self, request):
        society = Society.objects.create(
            society_name=request.data.get("society_name"),
            owner_name=request.data.get("owner_name"),
            incharge=request.data.get("incharge"),
            address=request.data.get("address")
        )

        return Response({
            "id": society.id,
            "message": "Society Added Successfully"
        })
class SocietyListView(APIView):
    permission_classes = [IsAuthenticated,IsSubAdminOrSecurity]

    def get(self, request):

        data = Society.objects.all().values()

        return Response(data)
    
    
class GetSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsSubAdminOrSecurity]    

class UpdateSocietyView(APIView):
    permission_classes = [IsAuthenticated,IsSubAdminOrSecurity]
    def put(self, request, pk):

        society = Society.objects.get(id=pk)

        society.society_name = request.data.get(
            "society_name",
            society.society_name
        )

        society.owner_name = request.data.get(
            "owner_name",
            society.owner_name
        )

        society.incharge = request.data.get(
            "incharge",
            society.incharge
        )

        society.address = request.data.get(
            "address",
            society.address
        )

        society.save()

        return Response({
            "message": "Society Updated Successfully"
        })
        
class DeleteSocietyView(APIView):
    permission_classes = [IsAuthenticated,IsAdminOrSubAdmin]

    def delete(self, request, pk):

        society = Society.objects.get(id=pk)

        society.delete()

        return Response({
            "message": "Society Deleted Successfully"
        })   
        
class InviteUserView(APIView):

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        send_mail(
            subject="Invitation to Gated Society",
            message="You have been invited to join Gated Society.",
            from_email=None,
            recipient_list=[email],
            fail_silently=False
        )

        return Response(
            {"message": "Invitation sent successfully"},
            status=status.HTTP_200_OK
        )  

class FlatView(APIView):

    def post(self, request):

        flat = Flat.objects.create(
            flat_number=request.data.get("flat_number"),
            owner_name=request.data.get("owner_name"),
            floor=request.data.get("floor"),
            society_name=request.data.get("society_name")
        )

        return Response({
            "id": flat.id,
            "message": "Flat Added Successfully"
        })
class FlatListView(APIView):

    def get(self, request):

        flats = Flat.objects.all().values()

        return Response(flats)
    
class UpdateFlatView(APIView):

    def put(self, request, pk):

        flat = Flat.objects.get(id=pk)

        flat.flat_number = request.data.get("flat_number")
        flat.owner_name = request.data.get("owner_name")
        flat.floor = request.data.get("floor")
        flat.society_name = request.data.get("society_name")

        flat.save()

        return Response({
            "message": "Flat Updated Successfully"
        })
        
class DeleteFlatView(APIView):

    def delete(self, request, pk):

        flat = Flat.objects.get(id=pk)

        flat.delete()

        return Response({
            "message": "Flat Deleted Successfully"
        }) 
class GetFlatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            flat = Flat.objects.get(id=pk)

            data = {
                "id": flat.id,
                "flat_number": flat.flat_number,
                "owner_name": flat.owner_name,
                "floor": flat.floor,
                "society_name": flat.society_name
            }

            return Response(data)

        except Flat.DoesNotExist:
            return Response(
                {"message": "Flat not found"},
                status=status.HTTP_404_NOT_FOUND
            )   
            
class UpdateSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsSubAdminOrSecurity]

    def put(self, request, pk):
        return Response({
            "message": "Update Society"
        })
    
class SocietyListView(APIView):
    permission_classes = [IsAuthenticated, IsSubAdminOrSecurity]

    def get(self, request):
        return Response({
            "message": "Society List"
        })
        
class GetSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsSubAdminOrSecurity]
    
class DeleteSocietyView(APIView):
    permission_classes = [IsAuthenticated, IsSubAdminOrSecurity]            
        
        
                                                  
        
                               
        