#include <WiFi.h>

const char* ssid = "SK_WIFIGIGAE826_5G";
const char* password = "2011013865";

void setup() {
  Serial.begin(115200);
  // ... (Serial.begin)
  WiFi.begin(ssid, password);
  // ... (while 루프: 연결 대기)
  // ... (연결 성공 시 IP 출력)
}

void loop() {
  Serial.println("안녕\n");
  // ... (통신 코드: HTTP 요청 등)
}