import os
from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def get_avatars():
    avatar_dir = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars')
    avatars = []
    if os.path.exists(avatar_dir):
        for f in sorted(os.listdir(avatar_dir)):
            if f.endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp')):
                avatars.append(f)
    return avatars