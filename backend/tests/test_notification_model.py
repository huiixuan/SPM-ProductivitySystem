from app.models import Notification

def test_notification_model_columns():
    cols = [c.name for c in Notification.__table__.columns]
    assert "id" in cols
    assert "user_id" in cols
    assert "task_id" in cols
    assert "payload" in cols
    assert "trigger_days_before" in cols
