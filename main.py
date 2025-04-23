# Filename: trackonomics.py

import requests
from bs4 import BeautifulSoup
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import re
import csv
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from twilio.rest import Client

# --- Twilio Config ---
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_PHONE_NUMBER = "+1XXXXXXXXXX"
RECEIVER_PHONE_NUMBER = "+91XXXXXXXXXX"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- HTTP Headers ---
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

# --- Global Vars ---
current_price = None
product_title = ""
product_url = ""
price_data = []
logged_in_user = None

USER_DB = "users2.csv"
fig = None
ax = None
canvas = None
chart_visible = False
url_entry = None
info_box = None
status_label = None
view_chart_btn = None

# --- User Auth ---
def save_user(username, password):
    with open(USER_DB, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, password])

def user_exists(username):
    if not os.path.exists(USER_DB):
        return False
    with open(USER_DB, newline='') as file:
        return any(row[0] == username for row in csv.reader(file))

def validate_user(username, password):
    if not os.path.exists(USER_DB):
        return False
    with open(USER_DB, newline='') as file:
        return any(row[0] == username and row[1] == password for row in csv.reader(file))

# --- Scraper ---
def get_price_title(url):
    try:
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, "lxml")

        title_tag = soup.find(id="productTitle")
        if not title_tag:
            raise Exception("Title not found.")
        title = title_tag.get_text(strip=True)

        price_selectors = ["priceblock_dealprice", "priceblock_ourprice", "priceblock_saleprice"]
        price = None
        for selector in price_selectors:
            price_tag = soup.find(id=selector)
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                price = float(''.join(c for c in price_text if (c.isdigit() or c == ".")))
                break

        if price is None:
            price_tag = soup.find("span", class_="a-offscreen")
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                price = float(''.join(c for c in price_text if (c.isdigit() or c == ".")))

        if price is None:
            raise Exception("Price not found. Product may be unavailable.")

        return title, price
    except Exception as e:
        raise Exception(f"Error: {str(e)}")

# --- SMS ---
def send_sms(message):
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=RECEIVER_PHONE_NUMBER
        )
    except Exception as e:
        print("SMS Error:", e)

# --- Monitor ---
def start_monitoring():
    global current_price, product_title, product_url

    product_url = url_entry.get().strip()
    if not product_url or not re.match(r"^https?://(www\.)?amazon\.", product_url):
        messagebox.showerror("Input Error", "Please enter a valid Amazon product URL.")
        return

    try:
        product_title, current_price = get_price_title(product_url)
        update_info_box(current_price, True)
        save_price_to_csv(current_price)
        update_price_chart()
        status_label.config(text=" Monitoring started...", fg="green")
        threading.Thread(target=monitor_price, daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error", str(e))
        status_label.config(text=" Error occurred", fg="red")

def monitor_price():
    global current_price
    while True:
        time.sleep(10)
        try:
            _, new_price = get_price_title(product_url)
            timestamp = time.strftime('%I:%M:%S %p')

            if new_price < current_price:
                msg = f" Price Drop!\n{product_title}\nOld: ₹{current_price}\nNew: ₹{new_price}"
                send_sms(msg)
                messagebox.showinfo("Price Drop Alert", msg)
                current_price = new_price
            elif new_price > current_price:
                msg = f"⚠️ Price Increased!\n{product_title}\nOld: ₹{current_price}\nNew: ₹{new_price}"
                send_sms(msg)
                messagebox.showinfo("Price Increase", msg)
                current_price = new_price
            else:
                msg = f"No change in price: ₹{new_price} (as of {timestamp})"
                send_sms(msg)

            update_info_box(new_price, False)
            save_price_to_csv(new_price)
            update_price_chart()
        except Exception as e:
            update_info_box(f"Error: {e}", False)

def save_price_to_csv(price):
    filename = "price_history.csv"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    price_data.append((timestamp, price))

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, price])

def update_info_box(latest_price, is_first=False):
    timestamp = time.strftime('%I:%M:%S %p')
    status = f" {product_title}\n💲 Price: ₹{latest_price}\n Checked: {timestamp}\n{'-'*60}\n"

    info_box.config(state="normal")
    if is_first:
        info_box.delete(1.0, tk.END)
    info_box.insert(tk.END, status)
    info_box.config(state="disabled")
    info_box.see(tk.END)

def update_price_chart():
    global fig, ax, canvas
    if not price_data:
        return
    times, prices = zip(*price_data)
    ax.clear()
    ax.plot(times, prices, marker='o', color='green')
    ax.set_title("Price Trend")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price (INR)")
    ax.tick_params(axis='x', rotation=45)
    fig.tight_layout()
    canvas.draw()

def toggle_chart():
    global chart_visible
    if chart_visible:
        canvas.get_tk_widget().pack_forget()
        view_chart_btn.config(text="View Price Chart")
    else:
        canvas.get_tk_widget().pack(pady=(5, 10))
        view_chart_btn.config(text=" Hide Price Chart")
    chart_visible = not chart_visible

# --- GUI Auth ---
def open_signup():
    def signup():
        username = user_entry.get().strip()
        password = pass_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Error", "Fill in all fields.")
            return
        if user_exists(username):
            messagebox.showerror("Exists", "User already exists.")
        else:
            save_user(username, password)
            messagebox.showinfo("Success", "Account created.")
            signup_win.destroy()

    signup_win = tk.Toplevel(root)
    signup_win.title("Sign Up")
    signup_win.geometry("300x200")
    tk.Label(signup_win, text="Username:").pack(pady=5)
    user_entry = tk.Entry(signup_win)
    user_entry.pack()
    tk.Label(signup_win, text="Password:").pack(pady=5)
    pass_entry = tk.Entry(signup_win, show="*")
    pass_entry.pack()
    tk.Button(signup_win, text="Sign Up", command=signup).pack(pady=10)

def open_login():
    def login():
        username = user_entry.get().strip()
        password = pass_entry.get().strip()
        if validate_user(username, password):
            global logged_in_user
            logged_in_user = username
            messagebox.showinfo("Welcome", f"Logged in as {username}")
            login_win.destroy()
            open_dashboard()
        else:
            messagebox.showerror("Error", "Invalid credentials.")

    login_win = tk.Toplevel(root)
    login_win.title("Login")
    login_win.geometry("300x200")
    tk.Label(login_win, text="Username:").pack(pady=5)
    user_entry = tk.Entry(login_win)
    user_entry.pack()
    tk.Label(login_win, text="Password:").pack(pady=5)
    pass_entry = tk.Entry(login_win, show="*")
    pass_entry.pack()
    tk.Button(login_win, text="Login", command=login).pack(pady=10)

# --- Dashboard ---
def open_dashboard():
    global url_entry, info_box, status_label, canvas, fig, ax, view_chart_btn

    dashboard = tk.Toplevel(root)
    dashboard.title("Dashboard - Trackonomics")
    dashboard.geometry("1000x700")
    dashboard.configure(bg="#FFFBE9")

    HEADER_FONT = ("Arial", 16, "bold")
    LABEL_FONT = ("Arial", 12)
    ENTRY_FONT = ("Arial", 11)
    BUTTON_FONT = ("Arial", 11, "bold")
    TEXT_FONT = ("Consolas", 10)

    tk.Label(dashboard, text=f"Welcome, {logged_in_user}!", font=HEADER_FONT, bg="#FFFBE9", fg="#AD8B73").pack(pady=(20, 5))
    tk.Label(dashboard, text="Enter Amazon Product URL:", font=LABEL_FONT, bg="#FFFBE9", fg="#AD8B73").pack(pady=(10, 2))

    url_entry = tk.Entry(dashboard, width=85, font=ENTRY_FONT, bg="#CEAB93", fg="#3b2a1a", insertbackground="#3b2a1a", relief="flat")
    url_entry.pack(pady=(0, 10))

    tk.Button(dashboard, text="Start Monitoring", font=BUTTON_FONT, bg="#AD8B73", fg="white",
              activebackground="#E3CAA5", padx=15, pady=5, command=start_monitoring).pack()

    status_label = tk.Label(dashboard, text="Waiting for input...", font=("Arial", 10), bg="#FFFBE9", fg="gray")
    status_label.pack()

    info_box = scrolledtext.ScrolledText(dashboard, height=10, width=115, font=TEXT_FONT,
                                         bg="#CEAB93", fg="#3b2a1a", wrap="word", bd=2, relief="solid")
    info_box.pack(pady=(15, 5))
    info_box.insert(tk.END, "Product details will appear here...\n")
    info_box.config(state="disabled")

    fig, ax = plt.subplots(figsize=(9, 3))
    canvas = FigureCanvasTkAgg(fig, master=dashboard)

    view_chart_btn = tk.Button(
        dashboard, text="View Price Chart", font=BUTTON_FONT,
        bg="#AD8B73", fg="white", activebackground="#E3CAA5",
        padx=15, pady=5, command=toggle_chart
    )
    view_chart_btn.pack(pady=(5, 10))

    tk.Label(dashboard, text="Made by Ayush Anil Nikam", font=("Arial", 9, "italic"), bg="#FFFBE9", fg="#AD8B73").pack(pady=(10, 5))

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
