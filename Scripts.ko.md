

# mklittlefs.py 명세
1. **LittleFS 바이너리 파일을 읽어 내부에 저장된 파일들을 로컬 폴더로 추출하는 함수 정의**
   - 1.1 블록사이즈를 함수의 매개변수로 받고 블록 카운트는 파일 크기로 계산한다.
   - 1.2 LittleFS 인스턴스 초기화 및 바이너리 데이터를 메모리 버퍼에 로드하여 파일 시스템 마운트한다.    
   - 1.3 로컬에 대상 폴더의 내용을 모두 삭제한다.
   - 1.4 가상 파일 시스템 내부를 순회하며 디렉토리를 생성하고 파일 데이터를 읽어 로컬에 기록
   - 1.5 파일 시스템 사용 종료 후 안전하게 언마운트 수행
2. **로컬 폴더에 있는 파일들을 수집하여 하나의 LittleFS 바이너리 파일로 만드는 함수 정의**
   - 2.1 블록사이즈를 함수의 매개변수로 받고 블록 카운트는 파일 크기로 계산한다.
   - 2.2 새 파일 시스템을 위한 인스턴스 생성, 포맷 및 로컬 디렉토리 파일 대량 임포트
   - 2.3 메모리 버퍼에 생성된 최종 파일 시스템 이미지를 실제 물리 바이너리 파일로 저장

# mklittlefs.py 사용법
이 스크립트를 사용하기 전에 littlefs-python 라이브러리가 설치되어 있어야 합니다.

bash
python mklittlefs.py --action extract --bin_file littlefs.bin --folder extracted_data

python mklittlefs.py --action assemble --bin_file new_littlefs.bin --folder extracted_data

# flash_littlefs.py 명세
1. 바이너리 파일을 ESP32의 특정 오프셋에 업로드하는 함수를 정의합니다.
   1.1 esptool 실행에 필요한 통신 속도, 리셋 설정, 쓰기 모드 등의 인자 리스트를 생성합니다.
   1.2 실행될 esptool 명령 인자 정보를 콘솔에 출력합니다.
   1.3. esptool.main을 호출하여 플래싱을 수행하고 종료 코드 및 예외를 처리하여 성공 여부를 반환합니다.
2. 스크립트의 전체 실행 흐름을 담당하는 메인 함수를 정의합니다.
   2.1 업로드할 LittleFS 바이너리 파일 경로와 대상 오프셋 주소를 설정합니다.
   2.2 바이너리 파일이 해당 경로에 실제로 존재하는지 검사합니다.
   2.3 업로드 함수를 호출하고 결과에 따라 성공 메시지를 출력하거나 프로그램을 종료합니다.

# flash_littlefs.py 사용법
이 스크립트는 생성된 `new_littlefs.bin` 파일을 ESP32의 지정된 오프셋(0x110000)에 업로드합니다.

## 기본값 사용
python flash_littlefs.py

## 특정 파일과 오프셋 지정
python flash_littlefs.py --bin custom.bin --offset 0x310000 --port COM3

# dump_littlefs.py 명세
1. ESP32 플래시 메모리에서 바이너리 데이터를 추출하는 함수를 정의합니다.
   1.2 실행될 esptool 명령 인자 정보를 콘솔에 출력합니다.
   1.3 esptool.main을 호출하여 덤프를 수행하고 종료 코드 및 예외를 처리하여 성공 여부를 반환합니다.
2. 스크립트의 전체 실행 흐름을 담당하는 메인 함수를 정의합니다.
   2.1 저장될 바이너리 파일 경로와 추출할 영역의 오프셋 및 크기를 설정합니다.
   2.2 덤프 함수를 호출하고 결과에 따라 성공 메시지를 출력하거나 프로그램을 종료합니다.
    
# dump_littlefs.py 사용법
이 스크립트는 ESP32의 플래시 메모리에서 LittleFS 영역(0x110000, 1.3MB)을 읽어 `littlefs.bin` 파일로 저장합니다.

## 기본값 사용
python dump_littlefs.py

## 오프셋과 크기 직접 지정
python dump_littlefs.py --offset 0x210000 --size 0x100000 --port COM3

# main.cpp 명세
1. LittleFS 마운트 (포맷 여부 false: 마운트 실패 시 자동 포맷)
2. 이미 존재하는 파일 존재 확인 및 읽고 표시하기
3. 파일 생성 및 기록 (FILE_WRITE)
4. 파일 다시 읽기 및 표시 (FILE_READ)

# gen_esp32part.py 사용법

CSV 파일을 바이너리로 변환 

python gen_esp32part.py partitions.csv partition_table.bin

바이너리 파일을 CSV로 변환

python gen_esp32part.py partition_table.bin partitions.csv


# littlefs_explorer
0. esp32 의 파티션 테이블을 읽어 분석한다.
   0.1 esp32의 offset 0x8000, size 0x1000 을 읽어 partition_table.bin 을 읽어온다.
   0.2 gen_esp32part 로 partition_table.bin 을 partitions.csv 파일로 변환한다.
   0.3 partitions.csv 파일의 내용을 '컨테이너' 안에 '블록'들로 가로로 표시하고 블록 별로 파티션의 종류도 표시한다.
   0.4 사용자가 블록을 누르면 offset과 size를 기억한다.
1. esp32 의 파티션을 읽어 littlefs.bin 파일을 읽어온다. dump_littlefs.py 를 사용한다.
2. littlefs.bin 파일을 extracted_data 폴더에 추출한다. mklittlefs.py 를 사용한다.
   2.1 이미 존재하는 extracted_data 폴더의 내용을 지우고 나서 추출한다.
3. pyside 를 이용한 gui에서 extracted_data 폴더를 표시하고 사용자가 파일을 생성,조회,변경,삭제한다.
   3.1 외부에서 파일을 드래그 앤 드롭하면 해당 파일들을 extracted_data 에 복사한다.
   3.2 여러파일을 선택해서 삭제할 수 있다.
   3.3 특정 littlefs.bin 파일을 읽어서 extracted_data 폴더에 추출하는 read from bin 버튼이 있다.
   3.4 extracted_data 폴더를 조립해서 새로운 new_littlefs.bin 파일을 만드는 write to bin 버튼이 있다.
   3.5 화면 하단 상태 창에 읽은 bin 파일의 용량을 표시하고, extracted_data 폴더의 내용이 변경하면 갱신하고 해당 용량을 초과할 경우 붉은 색으로 표시한다.   
4. extracted_data 폴더를 new_littlefs.bin 파일로 조립한다. mklittlefs.py 를 사용한다.
5. esp32 의 파티션에 new_littlefs.bin 파일을 기록한다. flash_littlefs.py 를 사용한다.
6. COM 포트를 선택할수 있다.
---
