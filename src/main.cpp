#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>          // UDP 통신을 위해 추가
#include <Wire.h>             // I2C 통신을 위해 추가
#include <Adafruit_MPU6050.h> // MPU-6050 라이브러리
#include <Adafruit_Sensor.h>

// -------------------- 📌 핀 정의 --------------------
// 🕹️ 조이스틱 & 5개 버튼
#define VRX_PIN 34     // X축 아날로그 (ADC1)
#define VRY_PIN 35     // Y축 아날로그 (ADC1) 
#define SW_PIN 5       // 조이스틱 버튼 디지털 (SW)

// 개별 푸시 버튼 (B1, B2, B3, B4)
const int pushButtonPins[] = {32, 33, 25, 26}; 
const int numButtons = sizeof(pushButtonPins) / sizeof(pushButtonPins[0]);

// 📐 MPU-6050 (I2C) - SCL: 27, SDA: 14
#define I2C_SDA_PIN 14 // 요청하신 SDA 핀
#define I2C_SCL_PIN 27 // 요청하신 SCL 핀
Adafruit_MPU6050 mpu;
bool mpu_initialized = false; // MPU 초기화 상태 플래그

// 🌐 Wi-Fi 및 통신
const char* ssid = "bssm_free";   // 2.4GHz SSID
const char* password = "bssm_free";       // 비밀번호

// 🚨 라즈베리파이의 실제 IP 주소로 변경하세요!
IPAddress remoteIp(192, 168, 0, 10); 
const int remotePort = 4200; // RPi 파이썬 서버 포트
WiFiUDP Udp;

// -------------------- 함수 선언 --------------------
void connectWiFi();
void initializeMPU();
void getMotionData(float &pitch, float &roll);


// -------------------- ⚙️ SETUP --------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n\n=== ESP32 컨트롤러 시작 ===");

  // 1. 핀모드 설정 (조이스틱 SW, 4개 버튼)
  pinMode(SW_PIN, INPUT_PULLUP);
  for (int i = 0; i < numButtons; i++) {
    pinMode(pushButtonPins[i], INPUT_PULLUP);
  }

  // 2. MPU-6050 초기화
  initializeMPU();

  // 3. Wi-Fi 연결
  connectWiFi();
  
  // 최종 헤더 출력
  Serial.println("\n--- 컨트롤러 준비 완료 ---");
  Serial.println("X | Y | SW | B1 | B2 | B3 | B4 | Pitch | Roll");
  Serial.println("-----------------------------------------------------");
}

// -------------------- 🔁 LOOP --------------------
void loop() {
  // 1. 센서 데이터 읽기
  int xValue = analogRead(VRX_PIN);
  int yValue = analogRead(VRY_PIN);
  int swState = digitalRead(SW_PIN);
  
  float pitch = 0.0, roll = 0.0;
  if (mpu_initialized) {
     getMotionData(pitch, roll);
  }

  // 2. 버튼 상태 문자열 생성 (B1, B2, B3, B4)
  String buttonStates = "";
  for (int i = 0; i < numButtons; i++) {
    int state = digitalRead(pushButtonPins[i]);
    buttonStates += (state == LOW ? "1" : "0"); 
    if (i < numButtons - 1) {
      buttonStates += ","; // UDP 전송을 위해 콤마 사용
    }
  }

  // 3. UDP 전송 데이터 문자열 생성 (총 9개 값)
  // 포맷: X,Y,SW,B1,B2,B3,B4,Pitch,Roll
  String dataString = "";
  dataString += String(xValue) + ",";
  dataString += String(yValue) + ",";
  dataString += String(swState == LOW ? 1 : 0) + ",";
  dataString += buttonStates + ","; // B1,B2,B3,B4 부분
  dataString += String(pitch, 1) + ","; 
  dataString += String(roll, 1);

  // 4. 시리얼 출력 (디버깅)
  // Serial.print는 UDP 포맷 대신 사람이 읽기 쉽게 재구성하여 출력
  Serial.print(xValue);
  Serial.print(" | ");
  Serial.print(yValue);
  Serial.print(" | ");
  Serial.print(swState == LOW ? "1" : "0");
  Serial.print(" | ");
  Serial.print(buttonStates);
  Serial.print(" | ");
  Serial.print(pitch, 1);
  Serial.print(" | ");
  Serial.println(roll, 1);

  // 5. UDP 패킷 전송
  if (WiFi.status() == WL_CONNECTED) {
    Udp.beginPacket(remoteIp, remotePort);
    Udp.print(dataString);
    Udp.endPacket();
  }

  delay(10); // 10ms마다 업데이트 (초당 100회)
}


// -------------------- 🗃️ 보조 함수 --------------------

void initializeMPU() {
  Serial.println("MPU-6050 초기화 시도...");
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN); // 커스텀 I2C 핀 설정 (14, 27)
  
  if (!mpu.begin()) {
    Serial.println("🔴 MPU-6050 초기화 실패! (핀 27/14 연결 확인)");
    mpu_initialized = false;
  } else {
    Serial.println("🟢 MPU-6050 초기화 성공!");
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G); 
    mpu_initialized = true;
  }
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  
  Serial.print("\n연결 시도: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 40) {
    delay(500);
    Serial.print(".");
    timeout++;
    
    // 5초마다 상태 출력
    if (timeout % 10 == 0) {
      Serial.println();
      Serial.print("Wi-Fi 상태 코드: ");
      Serial.println(WiFi.status()); // 오류 코드 확인용
    }
  }
  
  Serial.println();
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi 연결 성공! 🎉");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi 연결 실패!");
    Serial.print("최종 상태: ");
    Serial.println(WiFi.status());
    Serial.println("Wi-Fi 없이 계속 진행. (UDP 전송 불가)");
  }
}

void getMotionData(float &pitch, float &roll) {
    // MPU-6050에서 센서 이벤트 데이터를 가져옵니다.
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // 가속도 기반 Pitch/Roll 계산 (각도, 단위: Degree)
    float accX = a.acceleration.x;
    float accY = a.acceleration.y;
    float accZ = a.acceleration.z;

    // 아크탄젠트(atan2)를 사용하여 Roll과 Pitch 계산
    roll = atan2(accY, accZ) * 180 / PI; 
    pitch = atan2(-accX, sqrt(accY * accY + accZ * accZ)) * 180 / PI;
}