import re

# 1. requirements.in 정리 (== → >=, 공백 → >=)
def clean_requirements_in(file_path='requirements.in'):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        fixed_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue  # 빈 줄은 무시

            # 공백으로 버전 구분된 경우 처리: "Django 5.1" → "Django>=5.1"
            match = re.match(r'^(\S+)\s+(\d[\w.\-]+)$', line)
            if match:
                package, version = match.groups()
                fixed_lines.append(f'{package}>={version}\n')
            else:
                # 이미 형식이 "package==version"이라면 ==를 >=로
                fixed_lines.append(re.sub(r'==', '>=', line) + '\n')

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(fixed_lines)

        print("✅ requirements.in has been cleaned and updated.")
    except Exception as e:
        print(f"❌ Error processing requirements.in: {e}")



# 실행
if __name__ == '__main__':
    clean_requirements_in('requirements.in')

