# import re

# # 읽기/쓰기 모드로 파일 열기
# with open('requirements.in', 'r', encoding='utf-8') as file:
#     lines = file.readlines()

# # 공백을 제거하고 >=로 연결하기
# fixed_lines = []
# for line in lines:
#     match = re.match(r'(\S+)\s+(\S+)', line)
#     if match:
#         package, version = match.groups()
#         fixed_lines.append(f'{package}>={version}\n')
#     else:
#         fixed_lines.append(line)

# # 수정된 내용을 파일에 다시 쓰기
# with open('requirements.in', 'w', encoding='utf-8') as file:
#     file.writelines(fixed_lines)

# print("File has been fixed successfully.")

# import re

# # 읽기/쓰기 모드로 파일 열기
# with open('requirements.in', 'r', encoding='utf-8') as file:
#     lines = file.readlines()

# # ==를 >=로 바꾸기
# fixed_lines = []
# for line in lines:
#     fixed_line = re.sub(r'==', '>=', line)
#     fixed_lines.append(fixed_line)

# # 수정된 내용을 파일에 다시 쓰기
# with open('requirements.in', 'w', encoding='utf-8') as file:
#     file.writelines(fixed_lines)

# print("File has been fixed successfully.")


# 주석을 제거하는 스크립트

import re

def remove_comments_from_requirements(file_path):
    # 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 주석을 제거하고 주석이 아닌 줄만 유지
    cleaned_lines = []
    for line in lines:
        # 주석이 시작되는 '# ' 또는 '#' 뒤의 공백을 제거
        cleaned_line = re.sub(r'#.*', '', line).strip()
        if cleaned_line:  # 비어있지 않은 줄만 추가
            cleaned_lines.append(cleaned_line + '\n')

    # 수정된 내용을 파일에 다시 쓰기
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(cleaned_lines)

    print("Comments have been removed successfully.")

