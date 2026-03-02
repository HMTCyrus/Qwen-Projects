import random

def guess_number_game():
    """
    Trò chơi 'Đoán số':
    - Máy tính chọn một số ngẫu nhiên từ 1-100
    - Người chơi đoán số
    - Máy tính sẽ gợi ý 'cao hơn' hoặc 'thấp hơn'
    - Trò chơi tiếp tục cho đến khi người chơi đoán đúng
    """
    print("Chào mừng bạn đến với trò chơi Đoán Số!")
    print("Tôi đã chọn một số từ 1 đến 100. Hãy cố gắng đoán xem đó là số gì.")
    
    secret_number = random.randint(1, 100)
    attempts = 0
    
    while True:
        try:
            # Nhập số đoán từ người chơi
            user_guess = int(input("\nNhập số của bạn: "))
            attempts += 1
            
            # Kiểm tra số đoán
            if user_guess < secret_number:
                print("Số quá thấp! Hãy thử cao hơn.")
            elif user_guess > secret_number:
                print("Số quá cao! Hãy thử thấp hơn.")
            else:
                print(f"\nXin chúc mừng! Bạn đã đoán đúng số {secret_number} sau {attempts} lần thử!")
                break
                
        except ValueError:
            print("Vui lòng nhập một số hợp lệ.")

if __name__ == "__main__":
    guess_number_game()