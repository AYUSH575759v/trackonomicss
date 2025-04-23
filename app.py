from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, csv, io, os, base64, datetime
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# --- Register Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                users = json.load(f)
        else:
            users = {}

        if username in users:
            flash("Username already exists!", "error")
        else:
            users[username] = password
            with open('users.json', 'w') as f:
                json.dump(users, f)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))

    return render_template('register.html')

# --- Login Route ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                users = json.load(f)
        else:
            users = {}

        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials!", "error")

    return render_template('login.html')

# --- Logout Route ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Dashboard / Main Logic ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    product_title = ''
    current_price = None
    chart_img = None
    alert = None

    if request.method == 'POST':
        url = request.form['url']
        threshold = float(request.form['threshold'])

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")

        try:
            title = soup.find(id='productTitle').get_text().strip()
            price_text = soup.find('span', class_='a-price-whole')
            if not price_text:
                price_text = soup.find('span', class_='a-offscreen')
            price = float(price_text.get_text().replace('₹', '').replace(',', '').strip())

            product_title = title
            current_price = price

            # Save to CSV
            os.makedirs('price_data', exist_ok=True)
            filename = os.path.join('price_data', f"{session['username']}_price_data.csv")
            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.datetime.now(), title, price])

            # Generate chart
            timestamps, prices = [], []
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    try:
                        timestamps.append(row[0])
                        prices.append(float(row[2]))
                    except:
                        continue

            plt.figure(figsize=(6, 3))
            plt.plot(timestamps[-10:], prices[-10:], marker='o')
            plt.xticks(rotation=45)
            plt.title('Price Over Time')
            plt.xlabel('Time')
            plt.ylabel('Price (₹)')
            plt.tight_layout()

            img = io.BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)
            chart_img = base64.b64encode(img.getvalue()).decode()
            plt.close()

            if price <= threshold:
                alert = f"Price dropped below ₹{threshold}!"

        except Exception as e:
            flash(f"Error fetching data: {e}", "error")

    return render_template('dashboard.html',
                           username=session['username'],
                           title=product_title,
                           price=current_price,
                           chart_img=chart_img,
                           alert=alert)

if __name__ == '__main__':
    app.run(debug=True)
