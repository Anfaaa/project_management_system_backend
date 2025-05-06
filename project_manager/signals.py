# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from .models import Projects
# from .consumers import ProjectConsumer  # Импортируем ваш WebSocket Consumer

# # При создании проекта
# @receiver(post_save, sender=Projects)
# def project_created(sender, instance, created, **kwargs):
#     if created:
#         ProjectConsumer.send_projects_to_all()  # Отправить обновленный список проектов

# # При изменении проекта
# @receiver(post_save, sender=Projects)
# def project_updated(sender, instance, **kwargs):
#     ProjectConsumer.send_projects_to_all()  # Отправить обновленный список проектов

# # При удалении проекта
# @receiver(post_delete, sender=Projects)
# def project_deleted(sender, instance, **kwargs):
#     ProjectConsumer.send_projects_to_all()  # Отправить обновленный список проектов