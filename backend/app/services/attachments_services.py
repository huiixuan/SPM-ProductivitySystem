from werkzeug.utils import secure_filename

def save_attachments(task, files):
    attachments = []
    
    for file_storage in files:
        filename = secure_filename(file_storage)