import argparse
import os
import shutil
from littlefs import LittleFS

# 1. LittleFS 바이너리 파일을 읽어 내부에 저장된 파일들을 로컬 폴더로 추출하는 함수 정의
def extract_files(bin_file_path, output_folder, block_size):
    if not os.path.exists(bin_file_path):
        print(f"오류: littlefs.bin 파일 '{bin_file_path}'을(를) 찾을 수 없습니다.")
        return

    # 1.1 블록사이즈를 함수의 매개변수로 받고 블록 카운트는 파일 크기로 계산한다.
    file_size = os.path.getsize(bin_file_path)
    block_count = file_size // block_size

    # 1.3 로컬에 대상 폴더의 내용을 모두 삭제한다.
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    
    os.makedirs(output_folder, exist_ok=True)
    print(f"'{bin_file_path}'에서 파일 추출 중 (크기: {file_size} bytes, 블록 수: {block_count})...")

    try:
        # 1.2 LittleFS 인스턴스 초기화 및 바이너리 데이터를 메모리 버퍼에 로드하여 파일 시스템 마운트한다.
        fs = LittleFS(block_size=block_size, block_count=block_count)
        with open(bin_file_path, 'rb') as f:
            fs.context.buffer = bytearray(f.read())
        fs.mount()

        # 1.3 가상 파일 시스템 내부를 순회하며 디렉토리를 생성하고 파일 데이터를 읽어 로컬에 기록
        for root, dirs, files in fs.walk('/'):
            relative_path = root.lstrip('/')
            current_output_dir = os.path.join(output_folder, relative_path)
            os.makedirs(current_output_dir, exist_ok=True)

            for file_name in files:
                file_path_in_fs = os.path.join(root, file_name)
                output_file_path = os.path.join(current_output_dir, file_name)
                with fs.open(file_path_in_fs, 'rb') as lfs_file:
                    with open(output_file_path, 'wb') as local_file:
                        local_file.write(lfs_file.read())
                print(f"  추출됨: {file_path_in_fs} -> {output_file_path}")
        print(f"파일 추출 완료. '{output_folder}' 폴더를 확인하세요.")
    except Exception as e:
        print(f"파일 추출 중 오류 발생: {e}")
    finally:
        # 1.4 파일 시스템 사용 종료 후 안전하게 언마운트 수행
        if 'fs' in locals():
            try:
                fs.unmount()
            except Exception:
                pass

# 2. 로컬 폴더에 있는 파일들을 수집하여 하나의 LittleFS 바이너리 파일로 만드는 함수 정의
def assemble_files(input_folder, bin_file_path, block_size, image_size):
    if not os.path.exists(input_folder):
        print(f"오류: 입력 폴더 '{input_folder}'을(를) 찾을 수 없습니다.")
        return

    # 2.1 블록사이즈를 함수의 매개변수로 받고 블록 카운트는 파일 크기로 계산한다.
    block_count = image_size // block_size

    print(f"'{input_folder}'의 파일들을 '{bin_file_path}'로 조립 중 (대상 크기: {image_size} bytes)...")
    try:
        # 2.2 새 파일 시스템을 위한 인스턴스 생성, 포맷 및 로컬 디렉토리 파일 대량 임포트
        fs = LittleFS(block_size=block_size, block_count=block_count)
        fs.format()
        fs.mount()

        for root, dirs, files in os.walk(input_folder):
            rel_path = os.path.relpath(root, input_folder)
            lfs_dir = "/" if rel_path == "." else "/" + rel_path.replace(os.path.sep, "/")
            
            for d in dirs:
                fs.mkdir(os.path.join(lfs_dir, d).replace(os.path.sep, "/"))
            
            for f in files:
                local_file_path = os.path.join(root, f)
                lfs_file_path = os.path.join(lfs_dir, f).replace(os.path.sep, "/")
                with open(local_file_path, "rb") as src:
                    with fs.open(lfs_file_path, "wb") as dst:
                        dst.write(src.read())

        # 2.3 메모리 버퍼에 생성된 최종 파일 시스템 이미지를 실제 물리 바이너리 파일로 저장
        with open(bin_file_path, 'wb') as f:
            f.write(fs.context.buffer)
        print(f"파일 조립 완료. '{bin_file_path}' 파일이 생성되었습니다.")
    except Exception as e:
        print(f"파일 조립 중 오류 발생: {e}")

# 명령줄 인자(추출/조립 액션, 경로 등)를 파싱하고 해당 기능을 분기 실행하는 메인 함수
def main():
    parser = argparse.ArgumentParser(description="littlefs.bin 파일 관리 도구")
    parser.add_argument("--bin_file", required=True, help="littlefs.bin 파일 경로")
    parser.add_argument("--action", choices=["extract", "assemble"], required=True,
                        help="수행할 작업: 'extract' (추출) 또는 'assemble' (조립)")
    parser.add_argument("--folder", required=True, help="파일을 추출하거나 조립할 폴더 경로")
    parser.add_argument("--block_size", type=int, default=4096, help="LittleFS 블록 크기 (기본값: 4096)")
    parser.add_argument("--image_size", type=int, default=0x14F000, help="조립 시 생성할 바이너리 전체 크기 (기본값: 0x14F000)")

    args = parser.parse_args()

    if args.action == "extract":
        extract_files(args.bin_file, args.folder, args.block_size)
    elif args.action == "assemble":
        assemble_files(args.folder, args.bin_file, args.block_size, args.image_size)

# 스크립트가 직접 실행될 때 main() 함수를 호출하는 진입점
if __name__ == "__main__":
    main()