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

import re

# 읽기/쓰기 모드로 파일 열기
with open('requirements.in', 'r', encoding='utf-8') as file:
    lines = file.readlines()

# ==를 >=로 바꾸기
fixed_lines = []
for line in lines:
    fixed_line = re.sub(r'==', '>=', line)
    fixed_lines.append(fixed_line)

# 수정된 내용을 파일에 다시 쓰기
with open('requirements.in', 'w', encoding='utf-8') as file:
    file.writelines(fixed_lines)

print("File has been fixed successfully.")

