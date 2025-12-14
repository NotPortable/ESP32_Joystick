import socket
from evdev import UInput, ecodes as e

# =================================================================
# 1. UDP 통신 설정
# =================================================================
# 🚨 라즈베리파이 IP 주소는 '0.0.0.0' (모든 IP에서 수신) 유지
UDP_PORT = 4200      # ESP32 코드와 동일해야 합니다!

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind(('0.0.0.0', UDP_PORT))
    print(f"✅ UDP 서버 시작. 포트: {UDP_PORT}")
except OSError as e_msg:
    print(f"❌ 오류: 포트 {UDP_PORT}를 사용할 수 없습니다. 다른 프로세스가 사용 중일 수 있습니다.")
    exit()

# =================================================================
# 2. 가상 게임패드 정의
# =================================================================
capabilities = {
    e.EV_ABS: [
        (e.ABS_X, (-32768, 32767, 0, 0)),   # 왼쪽 X축 (조이스틱 VRX)
        (e.ABS_Y, (-32768, 32767, 0, 0)),   # 왼쪽 Y축 (조이스틱 VRY)
        (e.ABS_RX, (-32768, 32767, 0, 0)),  # 오른쪽 X축 (MPU Roll)
        (e.ABS_RY, (-32768, 32767, 0, 0)),  # 오른쪽 Y축 (MPU Pitch)
    ],
    e.EV_KEY: [
        e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y, # 버튼 4개
        e.BTN_TL                            # SW 버튼
    ]
}

# 가상 장치 생성
virtual_gamepad = UInput(capabilities, name='ESP32_Motion_Controller')
print("✅ 가상 게임패드 'ESP32_Motion_Controller' 생성 완료.")

# 조이스틱/MPU 값 매핑을 위한 상수
ANALOG_CENTER = 2047 
MPU_RANGE = 90.0 
# 버튼 매핑 리스트 (ESP32 데이터 순서와 일치: SW, B1, B2, B3, B4)
BUTTON_MAP = [e.BTN_TL, e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y] # 매핑 순서 변경: SW를 TL로, B1~B4를 ABXY로 매핑

# -----------------------------------------------------------------
# 3. 데이터 변환 함수
# -----------------------------------------------------------------

def map_joystick_value(raw_value):
    """ESP32의 0~4095 값을 표준 게임패드의 -32768~32767로 매핑 (왼쪽 스틱)"""
    return int((raw_value - ANALOG_CENTER) * (32767 / ANALOG_CENTER))

def map_motion_value(raw_angle):
    """MPU의 각도 값(-90.0 ~ 90.0)을 표준 게임패드의 -32768~32767로 매핑 (오른쪽 스틱/모션)"""
    mapped_val = int(raw_angle / MPU_RANGE * 32767)
    return max(-32768, min(32767, mapped_val))

# -----------------------------------------------------------------
# 4. 메인 루프 (데이터 수신 및 이벤트 전송)
# -----------------------------------------------------------------

try:
    while True:
        data, addr = sock.recvfrom(1024)
        data_str = data.decode('utf-8').split(',')
        
        # 데이터 길이 검증: 총 9개 값 (X, Y, SW, B1, B2, B3, B4, Pitch, Roll)
        if len(data_str) != 9: continue

        try:
            x_raw = int(data_str[0])
            y_raw = int(data_str[1])
            
            # SW(2)부터 B4(6)까지 버튼 데이터 (5개)
            button_data = data_str[2:7] 

            pitch_angle = float(data_str[7]) 
            roll_angle = float(data_str[8])
        except ValueError:
            continue # 데이터 형식 오류 시 패킷 무시

        # 4-1. 아날로그 입력 전송 (왼쪽 스틱 - 조이스틱)
        virtual_gamepad.write(e.EV_ABS, e.ABS_X, map_joystick_value(x_raw))
        virtual_gamepad.write(e.EV_ABS, e.ABS_Y, map_joystick_value(y_raw))

        # 4-2. 모션 입력 전송 (오른쪽 스틱 - MPU)
        virtual_gamepad.write(e.EV_ABS, e.ABS_RX, map_motion_value(roll_angle))
        virtual_gamepad.write(e.EV_ABS, e.ABS_RY, map_motion_value(pitch_angle)) 

        # 4-3. 버튼 입력 전송
        for i in range(len(BUTTON_MAP)):
            if i < len(button_data):
                is_pressed = (button_data[i] == '1')
                virtual_gamepad.write(e.EV_KEY, BUTTON_MAP[i], 1 if is_pressed else 0)

        virtual_gamepad.syn() # 모든 이벤트를 한 번에 시스템에 전송
        
except KeyboardInterrupt:
    print("\n👋 서버 종료 요청. 가상 게임패드를 해제합니다.")
finally:
    virtual_gamepad.close()
    sock.close()