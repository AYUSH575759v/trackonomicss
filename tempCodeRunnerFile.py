# --- Root Setup ---
root = tk.Tk()
root.title("Trackonomics - Login/Signup")
root.geometry("400x300")
root.configure(bg="#FFFBE9")

HEADER_FONT = ("Arial", 16, "bold")
BUTTON_FONT = ("Arial", 11, "bold")

tk.Label(root, text="Trackonomics", font=HEADER_FONT, bg="#FFFBE9", fg="#AD8B73").pack(pady=(30, 10))

tk.Button(root, text="Login", font=BUTTON_FONT, bg="#AD8B73", fg="white",
          activebackground="#E3CAA5", padx=15, pady=10, command=open_login).pack(pady=10)

tk.Button(root, text="Sign Up", font=BUTTON_FONT, bg="#AD8B73", fg="white",
          activebackground="#E3CAA5", padx=15, pady=10, command=open_signup).pack(pady=10)

root.mainloop()
