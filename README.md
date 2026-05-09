# TrekHub SummitAI

Find your next Himalayan adventure! TrekHub SummitAI is a full-stack web application that allows users to explore, filter, and get smart recommendations for treks across India. It features a natural language search powered by Google Gemini AI, letting you search for treks in plain English.

## 🌟 Features

- **Explore Treks:** Browse a comprehensive database of treks and filter them by State, Difficulty, Budget, and Duration.
- **Smart Recommendations:** A custom scoring engine that ranks the top 3 treks for you based on your exact preferences.
- **AI Search (NLP):** Ask for treks in plain English (e.g., *"cheap easy trek in Uttarakhand under 10000 for 6 days"*), and Gemini AI will parse your query and find the best matches.
- **Add Treks:** A community-driven feature that allows you to add new destinations directly to the database.

## 💻 Tech Stack

- **Frontend:** HTML5, CSS3 (Custom + Bootstrap 5), Vanilla JavaScript
- **Backend:** Python (Flask)
- **Database:** SQLite (`trekhub.db`)
- **AI Integration:** Google Gemini AI API

## 🚀 How to Run Locally

### Prerequisites
Make sure you have Python 3 installed on your machine. You will also need a free Google Gemini API Key.

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ya-yashawasthi-13/Trek-Advisor-.git
   cd Trek-Advisor-
   ```

2. **Set up a virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your Environment Variables:**
   Create a `.env` file inside the `backend` folder and add your Gemini API key:
   ```env
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

5. **Run the server:**
   ```bash
   python server.py
   ```

6. **Open the App:**
   Open your web browser and go to `http://127.0.0.1:8001`


## 📝 License
This project is open-source and available under the MIT License.
