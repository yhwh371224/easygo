from datetime import datetime, date

def date_to_ordinal(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.toordinal()

def ordinal_to_date(ordinal_num):
    return date.fromordinal(ordinal_num)

# 시작
print("무엇을 하시겠습니까?")
print("1: 날짜를 toordinal 번호로 변환")
print("2: toordinal 번호를 날짜로 변환")

choice = input("선택 (1 또는 2): ").strip()

if choice == "1":
    date_input = input("날짜를 입력하세요 (YYYY-MM-DD): ").strip()
    try:
        ordinal = date_to_ordinal(date_input)
        print(f"입력한 날짜의 toordinal 번호: {ordinal}")
    except ValueError:
        print("날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식으로 입력하세요.")

elif choice == "2":
    ordinal_input = input("toordinal 번호를 입력하세요 (정수): ").strip()
    try:
        ordinal_num = int(ordinal_input)
        restored_date = ordinal_to_date(ordinal_num)
        print(f"복원된 날짜: {restored_date}")
    except ValueError:
        print("올바른 정수를 입력하세요.")
    except Exception as e:
        print(f"변환 중 오류 발생: {e}")

else:
    print("1 또는 2 중에서 선택하세요.")
