#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// -------------------- 📌 핀 정의 --------------------
#define VRX_PIN 34     // X축
#define VRY_PIN 35     // Y축
#define SW_PIN 5       // 조이스틱 꾹 누르는 버튼

// 🔘 방향 버튼 4개 (순서: 위, 왼, 아래, 오)
#define PIN_UP    32
#define PIN_LEFT  33
#define PIN_DOWN  25
#define PIN_RIGHT 26

const int pushButtonPins[] = {PIN_UP, PIN_LEFT, PIN_DOWN, PIN_RIGHT}; 
const int numButtons = 4;

// 📐 MPU-6050 (I2C)
#define I2C_SDA_PIN 14 
#define I2C_SCL_PIN 27 
Adafruit_MPU6050 mpu;
bool mpu_initialized = false;

// 🌐 Wi-Fi 정보
const char* ssid = "bssm_free";
const char* password = "bssm_free";

// 🚨 라즈베리파이 IP 주소 (확인 후 수정)
IPAddress remoteIp(10, 150, 3, 57); 
const int remotePort = 4200;
WiFiUDP Udp;

// 함수 선언
void connectWiFi();
void runI2CScannerAndInitMPU(); // 👈 스캐너와 초기화를 합친 함수
void getMotionData(float &pitch, float &roll);
String getIntegratedDirection(int x, int y, int up, int left, int down, int right);

void setup() {
  Serial.begin(115200);
  delay(2000); // 시리얼 모니터 켜질 시간 확보
  Serial.println("\n\n=========================================");
  Serial.println("      ESP32 올인원 컨트롤러 (진단모드 포함)");
  Serial.println("=========================================");

  // 1. 핀 설정
  pinMode(SW_PIN, INPUT_PULLUP);
  pinMode(PIN_UP, INPUT_PULLUP);
  pinMode(PIN_LEFT, INPUT_PULLUP);
  pinMode(PIN_DOWN, INPUT_PULLUP);
  pinMode(PIN_RIGHT, INPUT_PULLUP);

  // 2. I2C 스캔 및 MPU 초기화 (디버깅 기능)
  runI2CScannerAndInitMPU();

  // 3. Wi-Fi 연결
  connectWiFi();
}

void loop() {
  // --- 센서 데이터 읽기 ---
  int xValue = analogRead(VRX_PIN);
  int yValue = analogRead(VRY_PIN);
  int swState = digitalRead(SW_PIN);
  
  // 버튼 상태 (눌림=0, 뗌=1)
  int b_up    = digitalRead(PIN_UP);
  int b_left  = digitalRead(PIN_LEFT);
  int b_down  = digitalRead(PIN_DOWN);
  int b_right = digitalRead(PIN_RIGHT);
  
  // MPU 값 읽기
  float pitch = 0.0, roll = 0.0;
  if (mpu_initialized) {
     getMotionData(pitch, roll);
  }

  // --- 통합 방향 판별 ---
  String direction = getIntegratedDirection(xValue, yValue, b_up, b_left, b_down, b_right);

  // --- 시리얼 출력 (디버깅 정보 포함) ---
  Serial.printf("방향: %-15s | X:%4d Y:%4d | MPU: %5.1f, %5.1f\n", 
                direction.c_str(), xValue, yValue, pitch, roll);

  // --- UDP 전송 데이터 생성 ---
  // 포맷: X, Y, SW, UP, LEFT, DOWN, RIGHT, Pitch, Roll
  String dataString = "";
  dataString += String(xValue) + ",";
  dataString += String(yValue) + ",";
  dataString += String(swState == LOW ? 1 : 0) + ",";
  
  dataString += String(b_up == LOW ? 1 : 0) + ",";
  dataString += String(b_left == LOW ? 1 : 0) + ",";
  dataString += String(b_down == LOW ? 1 : 0) + ",";
  dataString += String(b_right == LOW ? 1 : 0) + ",";
  
  dataString += String(pitch, 1) + ","; 
  dataString += String(roll, 1);

  // 전송
  if (WiFi.status() == WL_CONNECTED) {
    Udp.beginPacket(remoteIp, remotePort);
    Udp.print(dataString);
    Udp.endPacket();
  }

  delay(50); // 너무 빠르면 보기 힘드므로 0.05초 대기
}

// -------------------- 함수 정의 --------------------

// 🔍 I2C 스캐너 + MPU 초기화 통합 함수
void runI2CScannerAndInitMPU() {
  Serial.println("\n[1단계] I2C 버스 스캔 시작 (SDA:14, SCL:27)...");
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  
  byte error, address;
  int nDevices = 0;
  bool mpuFound = false;

  // 1~127 주소 전체 스캔
  for(address = 1; address < 127; address++ ) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
 
    if (error == 0) {
      Serial.printf("  ✅ 기기 발견! 주소: 0x%02X", address);
      if (address == 0x68 || address == 0x69) {
        Serial.println(" -> (MPU-6050 추정)");
        mpuFound = true;
      } else {
        Serial.println();
      }
      nDevices++;
    }
  }
  
  if (nDevices == 0) {
    Serial.println("  ❌ 연결된 I2C 기기가 없습니다. 배선(SDA,SCL,VCC,GND)을 확인하세요!");
    mpu_initialized = false;
  } else if (!mpuFound) {
    Serial.println("  ⚠️ 기기는 찾았으나 MPU-6050(0x68)은 아닙니다.");
    mpu_initialized = false;
  } else {
    Serial.println("\n[2단계] MPU-6050 초기화 시도...");
    if (mpu.begin()) {
      Serial.println("  🟢 MPU-6050 정상 작동 시작!");
      mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
      mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
      mpu_initialized = true;
    } else {
      Serial.println("  ❌ 센서 응답 없음 (칩 불량 혹은 전원 불안정)");
      mpu_initialized = false;
    }
  }
  Serial.println("-----------------------------------------");
}

// 🕹️ 통합 방향 판별 함수
String getIntegratedDirection(int x, int y, int up, int left, int down, int right) {
  // 1. 조이스틱 우선
  if (x < 500) return "오른쪽 (스틱)";
  if (x > 3500) return "왼쪽 (스틱)";
  if (y < 500) return "위 (스틱)";
  if (y > 3500) return "아래 (스틱)";

  // 2. 버튼 확인
  if (up == LOW)    return "위 (버튼)";
  if (left == LOW)  return "왼쪽 (버튼)";
  if (down == LOW)  return "아래 (버튼)";
  if (right == LOW) return "오른쪽 (버튼)";

  return "중앙";
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  Serial.print("\n[3단계] Wi-Fi 연결 중 (" + String(ssid) + ")");
  int cnt = 0;
  while (WiFi.status() != WL_CONNECTED && cnt < 20) { // 10초 대기
    delay(500);
    Serial.print(".");
    cnt++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n  🎉 연결 성공! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n  ❌ Wi-Fi 연결 실패 (핫스팟 켜져 있나요?)");
  }
}

void getMotionData(float &pitch, float &roll) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
    float accX = a.acceleration.x;
    float accY = a.acceleration.y;
    float accZ = a.acceleration.z;
    roll = atan2(accY, accZ) * 180 / PI; 
    pitch = atan2(-accX, sqrt(accY * accY + accZ * accZ)) * 180 / PI;
}