import re

def remove_comments_from_requirements_txt(file_path='requirements.txt'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue  # 빈 줄이나 전체 주석 제거

            # '#' 이후 주석 제거 (공백 없이 붙은 것도 포함)
            cleaned_line = re.sub(r'#.*$', '', line).strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line + '\n')

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(cleaned_lines)

        print("✅ requirements.txt comments removed successfully.")
    except Exception as e:
        print(f"❌ Error processing requirements.txt: {e}")

# 실행
if __name__ == '__main__':
    remove_comments_from_requirements_txt()