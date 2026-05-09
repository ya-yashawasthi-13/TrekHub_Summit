# Trek Advisor

Trek Advisor is a web application designed to help users discover and plan trekking adventures across India. The application provides personalized trek recommendations, detailed information, and an interactive interface for trek exploration.

## Tech Stack

### Backend
- **Framework**: Flask 3.1.3
- **Language**: Python 3.12.2
- **Database**: SQLite
- **API**: Google Generative AI (Gemini 2.5 Flash)
- **CORS**: Flask-CORS 6.0.2
- **Authentication**: Werkzeug (for password hashing)
- **Environment Management**: python-dotenv

### Frontend
- **HTML5**: Markup and structure
- **CSS3**: Styling and responsive design
- **JavaScript (Vanilla)**: Client-side logic and interactivity
- **Asset Management**: Static images and resources

### Dependencies
```
Flask==3.1.3
flask-cors==6.0.2
python-dotenv>=1.0.1
google-generativeai==0.8.6
asgiref==3.11.1
werkzeug>=3.0.0
```

## Project Structure

```
Trek-Advisor/
├── backend/
│   ├── server.py                 # Main Flask application
│   ├── requirements.txt           # Python dependencies
│   ├── .env                       # Environment variables (not included)
│   └── trekhub.db                 # SQLite database
├── frontend/
│   ├── index.html                 # Main dashboard page
│   ├── login.html                 # Login page
│   ├── assts/                     # Assets folder
│   │   ├── IMG_6111_web.jpg
│   │   ├── treks_web.jpeg
│   │   └── ...other images
│   ├── css/
│   │   └── styles.css             # Main stylesheet
│   └── js/
│       └── app.js                 # Main JavaScript file
└── README.md                       # This file
```

## Prerequisites

Before running this project, ensure you have:
- **Python 3.12+** installed
- **pip** (Python package manager)
- **Git** (for version control)
- **Google API Key** (for Generative AI features)

## Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/ya-yashawasthi-13/Trek-Advisor.git
cd Trek-Advisor
```

### Step 2: Set Up Environment Variables
Create a `.env` file in the `backend/` directory with your Google API key:

```bash
cd backend
echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
cd ..
```

**Note**: Get your Google API key from [Google Cloud Console](https://console.cloud.google.com/).

### Step 3: Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
cd ..
```

## How to Run

### Start the Backend Server

```bash
cd backend
python3 server.py
```

The server will start on `http://127.0.0.1:8001` (or `http://localhost:8001`).

**Expected Output**:
```
 * Serving Flask app 'server'
 * Debug mode: on
 * Running on http://127.0.0.1:8001
 * Press CTRL+C to quit
```

### Access the Application

Open your browser and navigate to:
- **Main App**: http://localhost:8001
- **Login Page**: http://localhost:8001/login.html

## API Endpoints

### Authentication
- **POST** `/api/login` - User login

### Trek Information
- **GET** `/api/states` - Get all available states
- **GET** `/api/treks` - Get all available treks
- **GET** `/api/faq` - Get FAQ information

### Additional Endpoints
- **GET** `/` - Serve index.html (main dashboard)
- **GET** `/login.html` - Serve login page
- **GET** `/css/styles.css` - Serve styles
- **GET** `/js/app.js` - Serve JavaScript

## Features

✅ **Trek Discovery**: Browse and search treks across different Indian states
✅ **User Authentication**: Secure login system
✅ **AI-Powered Recommendations**: Uses Google Gemini for personalized suggestions
✅ **Responsive Design**: Works on desktop and mobile devices
✅ **FAQ Section**: Common questions about trekking
✅ **State-based Filtering**: Filter treks by Indian states
✅ **RESTful API**: Clean API for frontend-backend communication

## Configuration

### Database
- SQLite database file: `backend/trekhub.db`
- Automatically created on first run
- Connection pooling via Flask's `g` object

### CORS Configuration
- CORS is enabled for all origins on `/api/*` endpoints
- Allows cross-origin requests from frontend to backend

### AI Model
- **Model**: Gemini 2.5 Flash
- **Purpose**: Trek recommendations and AI-powered suggestions
- **Configuration**: Set via `GOOGLE_API_KEY` in `.env`

## Development

### Debug Mode
The server runs in debug mode by default, which:
- Auto-reloads on code changes
- Provides detailed error messages
- Enables the Flask debugger (use cautiously)

### Disable Debug Mode (Production)
Modify `server.py` and change:
```python
flask_app.run(debug=False)
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution**: Ensure you've installed dependencies:
```bash
pip install -r backend/requirements.txt
```

### Issue: "GOOGLE_API_KEY not found"
**Solution**: Create `.env` file in `backend/` directory with your Google API key

### Issue: "Port 8001 already in use"
**Solution**: Either stop the process using port 8001 or modify the port in `server.py`:
```python
flask_app.run(host="127.0.0.1", port=8002)  # Use different port
```

### Issue: Database locked error
**Solution**: Ensure only one instance of the server is running

### Deprecation Warning: google.generativeai
**Note**: The `google.generativeai` package is deprecated. Consider updating to `google.genai` in the future.

## Performance Tips

1. **Caching**: Frontend assets include versioning (`?v=7`) for cache busting
2. **Static Files**: CSS and JS are served directly from Flask static folder
3. **Database**: Using SQLite with connection pooling for better performance

## Future Enhancements

- [ ] User profiles and preferences
- [ ] Trek booking system
- [ ] Reviews and ratings
- [ ] Google Maps integration
- [ ] Weather forecasting
- [ ] Mobile app
- [ ] Database migration to PostgreSQL for scalability

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions, please:
- Open an issue on GitHub
- Contact the maintainers
- Check existing documentation

## Authors

**Trek Advisor Team** - [ya-yashawasthi-13](https://github.com/ya-yashawasthi-13)

## Changelog

### Version 1.0.0
- Initial release
- Trek discovery and filtering
- User authentication
- AI-powered recommendations
- FAQ section
