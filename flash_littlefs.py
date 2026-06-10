# 필요한 라이브러리(esptool, sys, os)를 임포트합니다.
import esptool
import sys
import os

# 1. 바이너리 파일을 ESP32의 특정 오프셋에 업로드하는 함수를 정의합니다.
def download_bin_file(bin_file_name: str, offset: str) -> bool:
    # 1.1 esptool 실행에 필요한 통신 속도, 리셋 설정, 쓰기 모드 등의 인자 리스트를 생성합니다.
    argument_list = [
        "--baud", "460800",
        "--before", "default_reset",
        "--after", "hard_reset",
        "write_flash",
        "--compress",
        "--flash_mode", "dio",
        offset,
        bin_file_name
    ]

    # 1.2 실행될 esptool 명령 인자 정보를 콘솔에 출력합니다.
    print(f"Executing esptool with arguments: {argument_list}")

    # 1.3. esptool.main을 호출하여 플래싱을 수행하고 종료 코드 및 예외를 처리하여 성공 여부를 반환합니다.
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
    # 2.1 업로드할 LittleFS 바이너리 파일 경로와 대상 오프셋 주소를 설정합니다.
    bin_file_name = os.path.join(os.path.dirname(__file__), "new_littlefs.bin")
    offset = "0x110000"

    # 2.2 바이너리 파일이 해당 경로에 실제로 존재하는지 검사합니다.
    if not os.path.exists(bin_file_name):
        print(f"Error: Binary file not found at {bin_file_name}. Please ensure it exists in the same directory as this script.")
        sys.exit(1)

    # 2.3 업로드 함수를 호출하고 결과에 따라 성공 메시지를 출력하거나 프로그램을 종료합니다.
    print(f"Attempting to download {bin_file_name} to offset {offset}")
    if not download_bin_file(bin_file_name, offset):
        print(f"DownloadBinFile Failed for {bin_file_name}")
        sys.exit(1)
    else:
        print(f"Successfully downloaded {bin_file_name}")

# 스크립트가 직접 실행되는 경우 메인 함수를 호출합니다.
if __name__ == "__main__":
    main()