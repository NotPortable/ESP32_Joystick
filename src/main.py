import socket
from evdev import UInput, ecodes as e, AbsInfo

# =================================================================
# 1. 설정
# =================================================================
UDP_PORT = 4200 
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    sock.bind(('0.0.0.0', UDP_PORT))
    print(f"✅ 통합 게임패드 서버 시작! 포트: {UDP_PORT}")
except OSError as err:
    print(f"❌ 포트 에러: {err}")
    exit()

# =================================================================
# 2. 장치 설정 (버튼 + 조이스틱 + MPU)
# =================================================================

# 버튼 맵핑 (ESP32에서 오는 순서대로: SW, UP, LEFT, DOWN, RIGHT)
# SW는 '왼쪽 스틱 클릭(THUMBL)'으로, 나머지는 '십자키(DPAD)'로 설정
BTN_CODES = [
    e.BTN_THUMBL,     # SW (인덱스 2)
    e.BTN_DPAD_UP,    # UP (인덱스 3)
    e.BTN_DPAD_LEFT,  # LEFT (인덱스 4)
    e.BTN_DPAD_DOWN,  # DOWN (인덱스 5)
    e.BTN_DPAD_RIGHT  # RIGHT (인덱스 6)
]

# 장치 기능 정의
capabilities = {
    e.EV_KEY: BTN_CODES,
    e.EV_ABS: [
        # 왼쪽 스틱 (조이스틱)
        (e.ABS_X,  AbsInfo(value=0, min=-32768, max=32767, fuzz=10, flat=10, resolution=0)),
        (e.ABS_Y,  AbsInfo(value=0, min=-32768, max=32767, fuzz=10, flat=10, resolution=0)),
        # 오른쪽 스틱 (MPU 기울기)
        (e.ABS_RX, AbsInfo(value=0, min=-32768, max=32767, fuzz=10, flat=10, resolution=0)),
        (e.ABS_RY, AbsInfo(value=0, min=-32768, max=32767, fuzz=10, flat=10, resolution=0)),
    ]
}

try:
    virtual_gamepad = UInput(capabilities, name='ESP32_Ultimate_Gamepad')
    print("✅ 가상 장치 생성 완료. 연결 대기중...")
except Exception as err:
    print(f"❌ 생성 실패: {err}")
    exit()

# -----------------------------------------------------------------
# 🧮 맵핑 함수 (중요!)
# -----------------------------------------------------------------

# 조이스틱 값 보정 (0~4095 -> -32768~32767)
# ESP32: 오른쪽이 0, 왼쪽이 4095 (일반적인 것과 반대) -> 뒤집어줘야 함!
def map_joystick(value, is_inverted=False):
    # 중앙값 2048 기준
    normalized = value - 2048
    
    # -2048 ~ 2048 범위를 -32768 ~ 32767로 확장
    mapped = int(normalized * 16) 
    
    # 범위 제한 (안전장치)
    mapped = max(-32768, min(32767, mapped))
    
    # 방향 뒤집기 (ESP32 하드웨어 특성 반영)
    if is_inverted:
        return -mapped
    return mapped

# MPU 각도 보정 (-90도~90도 -> -32768~32767)
def map_mpu(angle):
    val = int(angle * 364) # 32767 / 90 ≈ 364
    return max(-32768, min(32767, val))

# =================================================================
# 3. 메인 루프
# =================================================================
try:
    while True:
        data, addr = sock.recvfrom(1024)
        # 데이터 포맷: X, Y, SW, UP, L, D, R, Pitch, Roll
        parts = data.decode('utf-8').split(',')
        
        if len(parts) != 9: continue

        try:
            # 1. 데이터 파싱
            raw_x = int(parts[0])
            raw_y = int(parts[1])
            
            # 버튼 데이터 (문자 '1'이면 눌린 것)
            # parts[2]=SW, [3]=UP, [4]=L, [5]=D, [6]=R
            btn_states = [ (p == '1') for p in parts[2:7] ] 
            
            pitch = float(parts[7])
            roll = float(parts[8])

            # 2. 값 변환 및 전송
            
            # [조이스틱] 
            # X축: ESP32는 오른쪽이 0이므로 뒤집어야 함 (is_inverted=True)
            virtual_gamepad.write(e.EV_ABS, e.ABS_X, map_joystick(raw_x, is_inverted=True))
            # Y축: 위가 0이므로 뒤집어야 함 (is_inverted=True) -> 게임패드는 위가 음수(-)
            virtual_gamepad.write(e.EV_ABS, e.ABS_Y, map_joystick(raw_y, is_inverted=False))

            # [MPU 기울기] -> 오른쪽 아날로그 스틱
            virtual_gamepad.write(e.EV_ABS, e.ABS_RX, map_mpu(roll))
            virtual_gamepad.write(e.EV_ABS, e.ABS_RY, map_mpu(pitch))

            # [버튼]
            for i, code in enumerate(BTN_CODES):
                virtual_gamepad.write(e.EV_KEY, code, 1 if btn_states[i] else 0)

            virtual_gamepad.syn() # 라즈베리파이에 "처리해!" 하고 전송

        except ValueError:
            continue

except KeyboardInterrupt:
    print("\n종료합니다.")
finally:
    virtual_gamepad.close()
    sock.close()