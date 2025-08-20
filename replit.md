# AsA - Sistema de Respostas Automáticas WhatsApp

## Overview

AsA is a WhatsApp automatic response system that integrates AI-powered responses with traditional keyword-based automation. The system provides a web-based administrative interface for managing WhatsApp connections, conversations, and automated responses. It uses Google's Gemini AI for intelligent message processing and maintains conversation history for context-aware interactions.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework Architecture
- **Flask-based Backend**: Uses Flask as the primary web framework with SQLAlchemy ORM for database operations
- **Template Engine**: Jinja2 templating with Bootstrap 5 for responsive UI design
- **Session Management**: Flask sessions for admin authentication with password hashing
- **WSGI Configuration**: ProxyFix middleware for proper header handling in production environments

### Database Design
- **SQLAlchemy Models**: Five main entities - Conversation, Message, AutoResponse, SystemSettings, and WhatsAppConnection
- **Relationship Management**: One-to-many relationship between conversations and messages with cascade deletion
- **Connection Tracking**: Dedicated model for storing WhatsApp connection status and QR codes
- **Settings Storage**: Key-value system for configurable application settings

### WhatsApp Integration
- **Service Layer**: WhatsAppService class manages connection simulation and message handling
- **QR Code Generation**: Base64-encoded QR codes for WhatsApp Web connection simulation
- **Message Processing**: Asynchronous message handling with typing indicators
- **Connection Status**: Real-time connection monitoring and status updates

### AI Integration
- **Gemini AI**: Google Generative AI integration for intelligent response generation
- **Context Management**: Maintains conversation history for contextual AI responses
- **Intent Analysis**: Message intent classification for appropriate response routing
- **Bilingual Support**: Portuguese-language responses with professional tone

### Admin Interface
- **Dashboard**: Statistics overview with conversation and message counts
- **Conversation Management**: View and manage all WhatsApp conversations
- **Response Configuration**: CRUD operations for automatic responses
- **Authentication**: Simple password-based admin access control

## External Dependencies

### AI Services
- **Google Generative AI**: Primary AI service using Gemini 2.5 Flash model for message generation and intent analysis
- **API Authentication**: Requires GEMINI_API_KEY environment variable

### Frontend Libraries
- **Bootstrap 5**: CSS framework with dark theme support via CDN
- **Font Awesome 6**: Icon library for UI elements
- **Custom CSS**: WhatsApp-inspired color scheme and styling

### Database
- **SQLite**: Default database for development (configurable via DATABASE_URL)
- **SQLAlchemy**: ORM with connection pooling and automatic table creation

### Environment Configuration
- **SESSION_SECRET**: Flask session encryption key
- **ADMIN_PASSWORD**: Admin panel access password
- **DATABASE_URL**: Database connection string (defaults to SQLite)
- **GEMINI_API_KEY**: Google AI API authentication key