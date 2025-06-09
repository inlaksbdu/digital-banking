from config import celery_app
from accounts.models import CustomUser, ActivityLog


@celery_app.task
def log_action(user_id, action):
    # pass
    user = CustomUser.objects.get(id=user_id)
    ActivityLog.objects.create(user=user, action=action)
    return "action logged"
