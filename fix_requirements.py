import re

# # 공백이 있는 경우: 공백제거하고 >= 연결하기
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


# # 공백이 없는 경우: >= 로 바꾸기 
with open('requirements.in', 'r', encoding='utf-8') as file:
    lines = file.readlines()

fixed_lines = []
for line in lines:
    fixed_line = re.sub(r'==', '>=', line)
    fixed_lines.append(fixed_line)

with open('requirements.in', 'w', encoding='utf-8') as file:
    file.writelines(fixed_lines)

print("File has been fixed successfully.")

# # requirements.txt 파일에 주석된 부분만 모두 제거하기
# def remove_comments_from_requirements(file_path):
#     try:
#         # 파일 읽기
#         with open(file_path, 'r', encoding='utf-8') as file:
#             lines = file.readlines()
        
#         print("File read successfully.")
        
#         # 주석을 제거하고 주석이 없는 줄만 유지
#         cleaned_lines = []
#         for line in lines:
#             # 주석 제거
#             cleaned_line = re.sub(r'#.*', '', line).rstrip()
#             if cleaned_line:  # 비어있지 않은 줄만 추가
#                 cleaned_lines.append(line)  # 원래의 줄을 그대로 유지
        
#         print("Comments removed. Lines prepared for writing.")
        
#         # 수정된 내용을 파일에 다시 쓰기
#         with open(file_path, 'w', encoding='utf-8') as file:
#             file.writelines(cleaned_lines)
        
#         print("Comments have been removed successfully.")
    
#     except Exception as e:
#         print(f"An error occurred: {e}")

# # 예시로 파일 경로를 입력하여 함수 호출
# remove_comments_from_requirements('requirements.txt')



