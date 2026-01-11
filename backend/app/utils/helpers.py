import uuid

def generate_user_id():
    return str(uuid.uuid4())

def format_timestamp(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")
