import uuid

def generate_short_uuid():
    return str(uuid.uuid4())[:8]  # 8자리로 자름

if __name__ == "__main__":
    print(generate_short_uuid())