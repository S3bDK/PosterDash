# 🎬 PosterDash

A lightweight local dashboard for displaying movie posters using TheMovieDB API.

⚠️ **This project is for personal/home use only.**  
Commercial use or deployment in public/production environments is not permitted.

---

## ⚠️ Important Notice

- The API key is stored in **plain text**
- It is **NOT encrypted or secure**
- Do **NOT** use this application in:
  - Public environments
  - Production systems
  - Any setup involving sensitive data

---

## 🚀 Setup Guide

### 🖥️ macOS

```bash
# Install dependencies
brew install python3
pip3 install flask requests python-dotenv

# Navigate to project folder
cd ~/Downloads/PosterDash

# Run the app
python3 app.py
```

### Ubuntu and Raspberry Pi OS / Linux
```bash
bash <(curl -s https://raw.githubusercontent.com/S3bDK/PosterDash-install/refs/heads/main/PosterDash-install.sh)
```
### Access the App

Once running, open:

* Admin Panel: http://127.0.0.1:5005/admin
* Client Panel: http://127.0.0.1:5005/client

## TheMovieDB (TMDB) Setup

### 1. Create an Account
Go to: https://www.themoviedb.org/

---

### 2. Request an API Key

- Click your profile icon (top right)
- Go to **Settings → API**
- Click **Request an API Key**
- Choose:  
  **Yes, this is for my own personal use only**

---

### 3. Application Details

Use the following:

- **Application Name:** PosterDash  
- **Application URL:** http://127.0.0.1  
- **Type of Use:** Desktop Application  
- **Application Summary:**  
  This is used for a home theater to display posters on a monitor  

---

### 4. Get Your API Key

- Go to your profile  
- Click **API Subscription**  
- Select **Access your API key details**  
- Copy your API key  

---

### 5. Add API Key to PosterDash

- Open the Admin Panel  
- Paste your API key into the field  
- Save your settings  

---

<img width="1919" height="913" alt="image" src="https://github.com/user-attachments/assets/db8be5a1-d572-42b9-8124-62f38e0de3e2" />

---

## Notes

- Runs locally on port **5005**
- Designed for home theater / personal setups
- No authentication or security included

---

## License

This project is intended for private use only.  
You are not permitted to use this in commercial or production environments.

---

## Disclaimer

This project is provided "as-is" with no guarantees of security or stability.  
Use at your own risk.
