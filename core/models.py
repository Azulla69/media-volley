from django.db import models
from django.conf import settings


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name='Пользователь')
    message = models.CharField(max_length=500, verbose_name='Сообщение')
    link = models.CharField(max_length=200, blank=True, verbose_name='Ссылка')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    invite = models.ForeignKey('teams.TeamInvite', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications', verbose_name='Приглашение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user}: {self.message[:50]}'


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following', verbose_name='Подписчик')
    followed_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='followers', verbose_name='Игрок')
    followed_team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, null=True, blank=True, related_name='followers', verbose_name='Команда')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        if self.followed_user:
            return f'{self.follower} → {self.followed_user}'
        return f'{self.follower} → {self.followed_team}'