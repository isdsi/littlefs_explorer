#include <Arduino.h>
#include "LittleFS.h"

void setup() {
    Serial.begin(115200);
    delay(5000); // 시리얼 모니터 안정화 대기

    Serial.println("\n--- LittleFS 테스트 시작 ---");

    // 1. LittleFS 마운트 (포맷 여부 false: 마운트 실패 시 자동 포맷)
    if (!LittleFS.begin(false)) {
        Serial.println("LittleFS 마운트 실패");
        return;
    }

    const char* path = "/example.txt";

    // 2. 이미 존재하는 파일 존재 확인 및 읽고 표시하기
    if (LittleFS.exists(path)) {
        Serial.println("기존 파일이 발견되었습니다. 내용을 읽어옵니다...");
        File existingFile = LittleFS.open(path, FILE_READ);
        if (existingFile && !existingFile.isDirectory()) {
            Serial.println("--- 기존 파일 내용 ---");
            while (existingFile.available()) {
                Serial.write(existingFile.read());
            }
            Serial.println("\n---------------------");
            existingFile.close();
        } else {
            Serial.println("기존 파일을 여는 데 실패했습니다.");
        }
    } else {
        Serial.println("기존 파일이 존재하지 않습니다. 새로 생성을 시작합니다.");
    }

    // 3. 파일 생성 및 기록 (FILE_WRITE)
    Serial.println("파일 쓰기 중...");
    File file = LittleFS.open(path, FILE_WRITE);
    if (!file) {
        Serial.println("파일을 열 수 없습니다 (쓰기 모드)");
        return;
    }

    file.println("Hello, LittleFS!");
    file.println("이것은 ESP32 파일 시스템 테스트입니다.");
    file.close(); // 파일 닫기
    Serial.println("파일 기록 완료 및 닫기");

    // 4. 파일 다시 읽기 및 표시 (FILE_READ)
    Serial.println("파일 읽기 중...");
    file = LittleFS.open(path, FILE_READ);
    if (!file || file.isDirectory()) {
        Serial.println("파일을 읽을 수 없거나 디렉토리입니다.");
        return;
    }

    Serial.println("--- 파일 내용 ---");
    while (file.available()) {
        Serial.write(file.read());
    }
    Serial.println("-----------------");

    file.close(); // 파일 닫기
    Serial.println("파일 읽기 완료 및 닫기");
}

void loop() {
    // 추가 반복 작업 없음
}