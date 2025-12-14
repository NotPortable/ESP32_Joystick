import socket
from evdev import UInput, ecodes as e, AbsInfo # 👈 AbsInfo 추가됨!

# =================================================================
# 1. 설정
# =================================================================
UDP_PORT = 4200 
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 포트 바인딩
try:
    sock.bind(('0.0.0.0', UDP_PORT))
    print(f"✅ 라즈베리파이 UDP 서버 시작! 포트: {UDP_PORT}")
except OSError as err:
    print(f"❌ 포트 에러: {err}")
    exit()

# =================================================================
# 2. 가상 게임패드 설정 (이 부분이 수정됨)
# =================================================================

# 버튼 매핑 (ESP32 순서: SW, 위, 왼, 아래, 오)
BUTTON_MAP = [
    e.BTN_TL,         # SW
    e.BTN_DPAD_UP,    # 위
    e.BTN_DPAD_LEFT,  # 왼
    e.BTN_DPAD_DOWN,  # 아래
    e.BTN_DPAD_RIGHT  # 오
]

# 🚨 수정된 부분: AbsInfo를 사용하여 명확하게 정의
# 형식: AbsInfo(value=0, min=최소, max=최대, fuzz=0, flat=0, resolution=0)
capabilities = {
    e.EV_ABS: [
        (e.ABS_X,  AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
        (e.ABS_Y,  AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
        (e.ABS_RX, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
        (e.ABS_RY, AbsInfo(value=0, min=-32768, max=32767, fuzz=0, flat=0, resolution=0)),
    ],
    e.EV_KEY: BUTTON_MAP
}

# 가상 장치 생성
try:
    virtual_gamepad = UInput(capabilities, name='ESP32_BSSM_Controller')
    print("✅ 가상 게임패드 생성 완료. ESP32 데이터를 기다립니다...")
except Exception as err:
    print(f"❌ 가상 장치 생성 실패: {err}")
    print("👉 'sudo python3 gamepad_server.py'로 실행했는지 확인하세요.")
    exit()

# 상수 설정
ANALOG_CENTER = 2047 
MPU_RANGE = 90.0

def map_value(value, center, out_max):
    # 정수로 변환하여 계산
    return int((value - center) * (out_max / center))

def map_motion(angle):
    val = int(angle / MPU_RANGE * 32767)
    return max(-32768, min(32767, val))

# =================================================================
# 3. 메인 루프
# =================================================================
try:
    while True:
        data, addr = sock.recvfrom(1024)
        data_str = data.decode('utf-8').split(',')
        
        if len(data_str) != 9: continue

        try:
            # 데이터 파싱
            x_raw = int(data_str[0])
            y_raw = int(data_str[1])
            btn_data = data_str[2:7]
            pitch = float(data_str[7])
            roll = float(data_str[8])

            # --- 입력 전송 ---
            
            # 조이스틱 (X, Y)
            virtual_gamepad.write(e.EV_ABS, e.ABS_X, map_value(x_raw, ANALOG_CENTER, 32767))
            virtual_gamepad.write(e.EV_ABS, e.ABS_Y, map_value(y_raw, ANALOG_CENTER, 32767))
            
            # 자이로 (오른쪽 스틱)
            virtual_gamepad.write(e.EV_ABS, e.ABS_RX, map_motion(roll))
            virtual_gamepad.write(e.EV_ABS, e.ABS_RY, map_motion(pitch))

            # 버튼
            for i, btn_code in enumerate(BUTTON_MAP):
                is_pressed = (btn_data[i] == '1')
                virtual_gamepad.write(e.EV_KEY, btn_code, 1 if is_pressed else 0)

            virtual_gamepad.syn() # 전송

        except ValueError:
            continue

except KeyboardInterrupt:
    print("\n종료합니다.")
finally:
    virtual_gamepad.close()
    sock.close()