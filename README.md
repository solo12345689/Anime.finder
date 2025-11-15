run pip install -r requirements.txt
Then
run python -m flask run
# MovieBox Streaming App

A Flask-based web application that allows users to search for movies and TV series, then retrieve streaming/download information using the moviebox_api library.

## Features

- Search for movies and TV series
- View search results with cover images, titles, genres, and release dates
- Retrieve streaming/download information for selected content
- Responsive web interface

## Prerequisites

- Python 3.7+
- pip (Python package installer)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd moviebox-app
   python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
moviebox-app/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css   # Custom styles
│   └── js/
│       └── main.js     # Frontend JavaScript
├── README.md           # This file
└── requirements.txt    # Python dependencies
