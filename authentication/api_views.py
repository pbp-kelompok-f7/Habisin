from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import LoginForm, RegisterForm
from .profile_forms import ProfileForm


def errors_of(form):
    return {f: [str(e) for e in errs] for f, errs in form.errors.items()}


def profile_data(request, user):
    profile = getattr(user, "profile", None)
    photo = getattr(profile, "photo", None)
    return {
        "name": user.get_full_name() or user.username,
        "username": user.username,
        "email": user.email,
        "photo": request.build_absolute_uri(photo.url) if photo else None,
        "since": user.date_joined.year,
        "meals_made": 0,  # TODO: ganti dengan data asli kalau sudah ada modelnya
    }


class RegisterAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        form = RegisterForm(request.data)
        if not form.is_valid():
            return Response({"errors": errors_of(form)}, status=400)
        form.save()
        return Response({"detail": "Account created."}, status=201)


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        form = LoginForm(request.data)
        if not form.is_valid():
            return Response({"errors": errors_of(form)}, status=400)
        user = form.cleaned_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "profile": profile_data(request, user)})


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out."})


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(profile_data(request, request.user))

    def patch(self, request):
        form = ProfileForm(request.data, request.FILES)
        if not form.is_valid():
            return Response({"errors": errors_of(form)}, status=400)
        form.save(request.user)
        return Response(profile_data(request, request.user))