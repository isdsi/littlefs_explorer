# 1. 가상 환경 생성 (시스템 PATH에 python이 있는 경우)
# 만약 PATH에서 제거했다면 "C:\경로\python.exe" -m venv .\venv 로 실행하세요.
python -m venv venv

# 2. 가상 환경 내의 python 인터프리터를 직접 지칭하여 pip 및 패키지 설치
# 이 방식은 현재 셸의 Activate 여부와 상관없이 항상 venv 내부에 설치를 보장합니다.
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "VENV Environment Setup Completed." -ForegroundColor Green
