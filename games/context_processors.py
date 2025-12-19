from .models import Announcement

def global_news(request):
    site_news = Announcement.objects.filter(is_active=True).order_by("-created_at")[:3]
    return {"site_news": site_news}
