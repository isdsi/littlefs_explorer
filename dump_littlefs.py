# 필요한 라이브러리(esptool, sys, os)를 임포트합니다.
import esptool
import sys
import os

# 1. ESP32 플래시 메모리에서 바이너리 데이터를 추출하는 함수를 정의합니다.
def dump_bin_file(output_file_name: str, offset: str, size: str) -> bool:
    # 1.1 esptool 실행에 필요한 통신 속도, 리셋 설정, 읽기 작업 등의 인자 리스트를 생성합니다.
    argument_list = [
        "--baud", "460800",
        "--before", "default_reset",
        "--after", "hard_reset",
        "read_flash",
        offset,
        size,
        output_file_name
    ]

    # 1.2 실행될 esptool 명령 인자 정보를 콘솔에 출력합니다.
    print(f"Executing esptool with arguments: {argument_list}")

    # 1.3 esptool.main을 호출하여 덤프를 수행하고 종료 코드 및 예외를 처리하여 성공 여부를 반환합니다.
    try:
        esptool.main(argument_list)
        return True
    except SystemExit as e:
        if e.code == 0:
            return True
        print(f"esptool failed with exit code: {e.code}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during esptool execution: {e}")
        return False

# 2. 스크립트의 전체 실행 흐름을 담당하는 메인 함수를 정의합니다.
def main():
    # 2.1 저장될 바이너리 파일 경로와 추출할 영역의 오프셋 및 크기를 설정합니다.
    output_file_name = os.path.join(os.path.dirname(__file__), "littlefs.bin")
    offset = "0x110000"
    size = "0x14F000"

    # 2.2 덤프 함수를 호출하고 결과에 따라 성공 메시지를 출력하거나 프로그램을 종료합니다.
    print(f"Attempting to dump flash from offset {offset} with size {size} to {output_file_name}")
    if not dump_bin_file(output_file_name, offset, size):
        print(f"DumpBinFile Failed for {output_file_name}")
        sys.exit(1)
    else:
        print(f"Successfully dumped flash to {output_file_name}")

# 스크립트가 직접 실행되는 경우 메인 함수를 호출합니다.
if __name__ == "__main__":
    main()