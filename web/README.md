# AI Storyboard Pro

AI-powered storyboard generation system for filmmakers, animators, and content creators.

## Features

- **Smart Story Import**: Import scripts from PDF, DOCX, Markdown, or plain text
- **Character & Scene Management**: Define characters and scenes with visual references
- **AI-Powered Shot Generation**: Generate professional storyboard images from descriptions
- **Multiple Shot Templates**: Pre-defined camera angles and compositions
- **Export Options**: Export to JSON, ZIP (images), or full project backup
- **REST API**: Full API access for integration with other tools
- **Mobile Support**: Flutter-based mobile app for on-the-go access

## Quick Start

### Prerequisites

- Python 3.9+
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/ai-storyboard-pro.git
cd ai-storyboard-pro
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the setup wizard:
```bash
python setup_wizard.py
```

4. Start the application:

**Windows:**
```batch
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

### Manual Configuration

If you prefer manual setup, copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
NANA_BANANA_API_KEY=your_api_key_here
GRADIO_PORT=7861
API_PORT=8000
```

## Usage

### Web UI (Gradio)

Access the web interface at: `http://localhost:7861`

### REST API

API documentation available at: `http://localhost:8000/docs`

Start the API server:

**Windows:**
```batch
start_api.bat
```

**Linux/Mac:**
```bash
./start_api.sh
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options:

| Variable | Description | Default |
|----------|-------------|---------|
| `NANA_BANANA_API_KEY` | API key for image generation | Required |
| `GRADIO_PORT` | Port for Gradio UI | 7861 |
| `API_PORT` | Port for REST API | 8000 |
| `CORS_ORIGINS` | Allowed CORS origins | * |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size | 50 |

## Project Structure

```
ai-storyboard-pro/
├── app.py              # Main Gradio UI application
├── api_server.py       # FastAPI REST server
├── settings.py         # Configuration management
├── setup_wizard.py     # Interactive setup wizard
├── services.py         # Business logic layer
├── models.py           # Data models
├── templates.py        # Shot templates
├── .env.example        # Configuration template
├── requirements.txt    # Python dependencies
├── start.bat           # Windows startup script
├── start_api.bat       # Windows API startup script
├── start.sh            # Linux/Mac startup script
├── start_api.sh        # Linux/Mac API startup script
└── mobile/             # Flutter mobile app
```

## Security Notes

- Never commit your `.env` file (it's in `.gitignore`)
- In production, restrict `CORS_ORIGINS` to specific domains
- File uploads are validated for size and type
- API endpoints have path traversal protection

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## Support

- Create an issue for bug reports
- Start a discussion for feature requests
