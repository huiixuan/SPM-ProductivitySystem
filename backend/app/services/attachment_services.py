from app.models import db, Attachment
from sqlalchemy.exc import SQLAlchemyError

def get_attachment(attachment_id):
  try:
    attachment = Attachment.query.get(attachment_id)
    if not attachment:
      raise ValueError(f"Attachment with attachment ID {attachment_id} not found")
    
    return attachment
  
  except SQLAlchemyError as e:
    db.session.rollback()
    raise RuntimeError(f"Database error while retrieving attachment {attachment_id}: {e}")
  
def get_attachment_by_task(task_id):
  try:
    attachments = Attachment.query.filter_by(task_id=task_id) or []
    return attachments
  
  except SQLAlchemyError as e:
    db.session.rollback()
    raise RuntimeError(f"Database error while retrieving attachment from task {task_id}: {e}")