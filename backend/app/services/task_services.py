from app.models import db, Task, User, Attachment
from datetime import datetime

def save_task(title, description, duedate, status, owner_id, collaborator_ids, attachments, note):
    owner = User.query.get(owner_id)
    if not owner:
        raise ValueError(f"Owner with id {owner_id} does not exist.")
    
    collaborators = []
    if collaborator_ids:
        collaborators = User.query.filter(User.id.in_(collaborator_ids)).all()

    task = Task(title=title, description=description, duedate=duedate, status=status, owner=owner, collaborators=collaborators, note=note)

    if attachments:
        for file_path in attachments:
            attachment = Attachment(file_path=file_path, task=task)
            db.session.add(attachment)

    db.session.add(task)
    db.session.commit()

    return task
