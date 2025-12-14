import socket
from evdev import UInput, ecodes as e

# =================================================================
# 1. 설정
# =================================================================
UDP_PORT = 4200 
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    sock.bind(('0.0.0.0', UDP_PORT))
    print(f"✅ 키보드 모드(방향키) 시작! 포트: {UDP_PORT}")
except OSError as err:
    print(f"❌ 포트 에러: {err}")
    exit()

# =================================================================
# 2. 가상 키보드 설정
# =================================================================

# 사용할 키 목록 정의
# 방향키(상하좌우) + 엔터(선택)
CAPABILITIES = {
    e.EV_KEY: [e.KEY_UP, e.KEY_DOWN, e.KEY_LEFT, e.KEY_RIGHT, e.KEY_ENTER]
}

try:
    virtual_keyboard = UInput(CAPABILITIES, name='ESP32_Keyboard_Controller')
    print("✅ 가상 키보드 장치 생성 완료.")
    print("👉 조이스틱이나 버튼을 누르면 방향키가 입력됩니다.")
except Exception as err:
    print(f"❌ 생성 실패: {err}")
    exit()

# 조이스틱 임계값 (이 값보다 넘어가면 키 눌림으로 인식)
THRESHOLD_LOW = 1000  # 0쪽에 가까울 때
THRESHOLD_HIGH = 3000 # 4095쪽에 가까울 때

# =================================================================
# 3. 메인 루프
# =================================================================
try:
    while True:
        data, addr = sock.recvfrom(1024)
        # 데이터 포맷: X, Y, SW, UP, LEFT, DOWN, RIGHT, Pitch, Roll
        parts = data.decode('utf-8').split(',')
        
        if len(parts) != 9: continue

        try:
            # --- 1. 데이터 파싱 ---
            x_val = int(parts[0])
            y_val = int(parts[1])
            
            # 버튼 상태 (1이면 눌림)
            # parts[2]=SW, [3]=UP, [4]=L, [5]=D, [6]=R
            sw_pressed = (parts[2] == '1')
            btn_up     = (parts[3] == '1')
            btn_left   = (parts[4] == '1')
            btn_down   = (parts[5] == '1')
            btn_right  = (parts[6] == '1')

            # --- 2. 키 입력 판정 (조이스틱 OR 버튼) ---
            # 하나라도 참이면 해당 키를 누른 것으로 처리
            
            # [오른쪽]: 조이스틱 X가 0 근처(User설정) 혹은 오른쪽 버튼
            key_right = (x_val < THRESHOLD_LOW) or btn_right
            
            # [왼쪽]: 조이스틱 X가 4095 근처 혹은 왼쪽 버튼
            key_left  = (x_val > THRESHOLD_HIGH) or btn_left
            
            # [위]: 조이스틱 Y가 0 근처 혹은 위쪽 버튼
            key_up    = (y_val < THRESHOLD_LOW) or btn_up
            
            # [아래]: 조이스틱 Y가 4095 근처 혹은 아래쪽 버튼
            key_down  = (y_val > THRESHOLD_HIGH) or btn_down
            
            # [엔터]: 조이스틱 꾹 누름(SW)
            key_enter = sw_pressed

            # --- 3. 키 전송 ---
            virtual_keyboard.write(e.EV_KEY, e.KEY_RIGHT, 1 if key_right else 0)
            virtual_keyboard.write(e.EV_KEY, e.KEY_LEFT,  1 if key_left else 0)
            virtual_keyboard.write(e.EV_KEY, e.KEY_UP,    1 if key_up else 0)
            virtual_keyboard.write(e.EV_KEY, e.KEY_DOWN,  1 if key_down else 0)
            virtual_keyboard.write(e.EV_KEY, e.KEY_ENTER, 1 if key_enter else 0)

            virtual_keyboard.syn() # 전송

        except ValueError:
            continue

except KeyboardInterrupt:
    print("\n종료합니다.")
finally:
    virtual_keyboard.close()
    sock.close()