from app.models import db, Task, Attachment
from app.services.user_services import get_user_by_email
from sqlalchemy.exc import SQLAlchemyError

def save_task(title, description, duedate, status, owner_email, collaborator_emails, attachments, notes):
    try:
        owner = get_user_by_email(owner_email)
        if not owner:
            raise ValueError(f"Owner with email {owner_email} not found")
        
        collaborators = []
        if collaborator_emails:
            for email in collaborator_emails:
                user = get_user_by_email(email)
                if user:
                    collaborators.append(user)

        task = Task(title=title, description=description, duedate=duedate, status=status, owner=owner, collaborators=collaborators, notes=notes)

        if attachments:
            for file in attachments:
                attachment = Attachment(filename=file.filename, content=file.read(), task=task)
                db.session.add(attachment)

        db.session.add(task)
        db.session.commit()

        return task
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise e