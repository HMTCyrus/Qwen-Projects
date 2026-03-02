import tkinter as tk
from tkinter import messagebox
import random

class GuessNumberGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Trò chơi Đoán Số")
        self.root.geometry("400x300")
        
        # Initialize game variables
        self.secret_number = random.randint(1, 100)
        self.attempts = 0
        
        # Create GUI elements
        self.create_widgets()
    
    def create_widgets(self):
        # Title label
        title_label = tk.Label(self.root, text="Trò chơi Đoán Số", font=("Arial", 16))
        title_label.pack(pady=10)
        
        # Instructions
        instruction_label = tk.Label(self.root, text="Tôi đã chọn một số từ 1 đến 100.\nHãy đoán xem đó là số gì!", font=("Arial", 12))
        instruction_label.pack(pady=5)
        
        # Entry for user guess
        entry_frame = tk.Frame(self.root)
        entry_frame.pack(pady=10)
        
        tk.Label(entry_frame, text="Nhập số của bạn:", font=("Arial", 12)).pack(side=tk.LEFT)
        self.guess_entry = tk.Entry(entry_frame, font=("Arial", 12), width=10)
        self.guess_entry.pack(side=tk.LEFT, padx=5)
        self.guess_entry.bind('<Return>', self.process_guess)  # Allow Enter key to submit
        
        # Submit button
        self.submit_button = tk.Button(self.root, text="Gửi", font=("Arial", 12), command=self.process_guess)
        self.submit_button.pack(pady=5)
        
        # Result label
        self.result_label = tk.Label(self.root, text="", font=("Arial", 12), wraplength=350)
        self.result_label.pack(pady=10)
        
        # Attempts counter
        self.attempts_label = tk.Label(self.root, text=f"Số lần thử: {self.attempts}", font=("Arial", 12))
        self.attempts_label.pack(pady=5)
        
        # New game button
        self.new_game_button = tk.Button(self.root, text="Chơi lại", font=("Arial", 12), command=self.new_game)
        self.new_game_button.pack(pady=10)
    
    def process_guess(self, event=None):  # event parameter allows binding to Enter key
        try:
            user_guess = int(self.guess_entry.get())
            
            # Validate input range
            if user_guess < 1 or user_guess > 100:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập số từ 1 đến 100!")
                return
            
            self.attempts += 1
            self.attempts_label.config(text=f"Số lần thử: {self.attempts}")
            
            if user_guess < self.secret_number:
                self.result_label.config(text="Số quá thấp! Hãy thử cao hơn.", fg="blue")
            elif user_guess > self.secret_number:
                self.result_label.config(text="Số quá cao! Hãy thử thấp hơn.", fg="orange")
            else:
                self.result_label.config(text=f"Xin chúc mừng! Bạn đã đoán đúng số {self.secret_number} sau {self.attempts} lần thử!", fg="green")
                messagebox.showinfo("Thành công", f"Bạn đã đoán đúng số {self.secret_number} sau {self.attempts} lần thử!")
                self.submit_button.config(state="disabled")
            
            # Clear the entry field
            self.guess_entry.delete(0, tk.END)
            
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập một số hợp lệ!")
            self.guess_entry.delete(0, tk.END)
    
    def new_game(self):
        # Reset game variables
        self.secret_number = random.randint(1, 100)
        self.attempts = 0
        
        # Update GUI elements
        self.result_label.config(text="")
        self.attempts_label.config(text=f"Số lần thử: {self.attempts}")
        self.guess_entry.delete(0, tk.END)
        self.submit_button.config(state="normal")
        self.guess_entry.focus()

def main():
    root = tk.Tk()
    game = GuessNumberGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()