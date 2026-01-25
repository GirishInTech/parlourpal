# ParlorPal - AI-Powered Marketing Automation Platform

## Project Overview

ParlorPal is a comprehensive Django-based web application that leverages multiple AI services to provide automated marketing solutions for small businesses, particularly beauty parlors and local service providers. The platform integrates Google Vertex AI, Cohere, and Google Gemini to generate promotional content, manage business profiles, and automate customer engagement through festival notifications.

## Architecture & Technical Implementation

### Core Technologies

| Component | Technology | Version/Purpose |
|-----------|------------|-----------------|
| **Backend Framework** | Django | 5.1 with custom user authentication |
| **Database** | SQLite3 | Development database with PostgreSQL ready |
| **AI Services** | Google Vertex AI (Imagen), Cohere, Google Gemini | Content generation and chatbot |
| **Image Processing** | Cloudinary | Image optimization and cloud storage |
| **Email System** | Gmail SMTP | Automated notifications and verification |
| **Static Files** | WhiteNoise | Production-ready static file serving |
| **Authentication** | Custom User Model | Extended with email verification |

### Key Features & Implementation

#### 1. **AI-Powered Content Generation**
- **Poster Generation**: Utilizes Google Vertex AI's Imagen model for custom promotional poster creation
- **Text Generation**: Gemini AI integration for marketing captions in multiple languages
- **Chatbot Assistant**: Google Gemini-powered conversational AI for business advice
- **Video Generation**: Experimental video content creation capabilities

#### 2. **Business Profile Management**
- Custom user model with email verification system
- Business profile creation with logo upload and Cloudinary integration
- Location, contact, and timing management
- Profile validation and duplicate prevention

#### 3. **Automated Marketing System**
- Festival notification system with configurable timing
- Email automation using Django's email backend
- User activity tracking and analytics
- Search history management with duplicate prevention

#### 4. **User Experience & Analytics**
- Dashboard with personalized AI suggestions
- Activity history tracking across all AI interactions
- Insights and performance analytics
- Mobile-responsive Bootstrap UI

## Code Architecture

### Models Structure
```python
# Core Models
CustomUser(AbstractUser)          # Extended user model with verification
BusinessProfile                   # Business information and branding
SearchHistory                     # User search queries with deduplication
PosterGeneration                  # AI-generated promotional content
Festival                          # Festival management for notifications
UserHistory                       # Comprehensive activity tracking
```

### View Functions (980+ lines)
- **Authentication Views**: Registration, login, email verification
- **Content Generation**: AI poster, text, and video generation
- **Business Management**: Profile management and analytics
- **Automation**: Festival notifications and email templates
- **API Endpoints**: AJAX-powered chatbot and content generation

### Key Technical Implementations

#### AI Integration Pattern
```python
# Multi-AI Service Architecture
- Google Vertex AI (Imagen): Image generation with safety filters
- Cohere AI: Text generation with context-aware prompts
- Google Gemini: Conversational AI with multi-turn context
```

#### Email Automation System
```python
# Automated Email Workflow8
- Email verification with token-based authentication
- Festival notifications with configurable timing
- HTML email templates with responsive design
- Gmail SMTP integration with app password authentication
```

#### Cloud Storage Integration
```python
# Cloudinary Implementation
- Image optimization before upload
- Automatic folder organization
- Fallback to local storage on upload failure
- Secure URL generation and management
```

## API Endpoints & Routes

### Core Application Routes
```
/                    # Landing page
/login/             # User authentication
/register/          # User registration with business profile
/dashboard/         # Main user interface with AI suggestions
/ai/                # AI text generation interface
/generate_poster/   # AI poster generation
/chatbot/           # AI assistant interface
/profile/           # Business profile management
/history/           # User activity tracking
/insights/          # Analytics and performance metrics
```

### Email & Automation Routes
```
/verify-email/<token>/     # Email verification
/resend-verification/      # Verification email resend
/toggle-notifications/     # Festival notification toggle
/manage-festivals/        # Festival management interface
```

## Database Schema

### User Management
- **CustomUser**: Extended Django user with email verification, notification preferences
- **BusinessProfile**: One-to-one relationship with user, includes business details and branding

### Content Management
- **PosterGeneration**: Stores AI-generated posters with metadata
- **SearchHistory**: User search queries with automatic deduplication
- **UserHistory**: Comprehensive activity tracking with JSON field for input/output data

### Automation
- **Festival**: Festival management with notification timing and user preferences

## Security & Authentication

### Email Verification System
- Token-based verification with 24-hour expiration
- Secure token generation using UUID4
- Automatic cleanup of expired tokens

### User Authentication
- Custom user model extending Django's AbstractUser
- Password validation and secure storage
- Session management with CSRF protection

### API Security
- CSRF protection on all forms
- AJAX request validation
- Input sanitization and validation

## Performance Optimizations

### Image Processing
- Automatic image optimization before Cloudinary upload
- Configurable quality and size parameters
- Fallback mechanisms for upload failures

### Database Optimization
- Efficient query patterns with select_related and prefetch_related
- Indexed fields for search and filtering
- Automatic cleanup of orphaned data

### Caching Strategy
- Session-based caching for user preferences
- Static file optimization with WhiteNoise
- Cloudinary CDN for image delivery

## Deployment Configuration

### Environment Variables
```bash
# AI Services
COHERE_API_KEY=your_cohere_key
GEMINI_API_KEY=your_gemini_key
GOOGLE_VERTEX_API_KEY=your_vertex_key
VERTEX_IMAGE_ENDPOINT=your_endpoint
GCP_PROJECT_ID=your_project_id

# Cloud Services
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Email Configuration
GMAIL_USER=your_gmail
GMAIL_APP_PASSWORD=your_app_password

# Django Configuration
SECRET_KEY=your_secret_key
DEBUG=True/False
```

### Production Setup
- Railway deployment configuration
- WhiteNoise for static file serving
- Environment-based settings management
- Database migration automation

## Development Workflow

### Custom Management Commands
```bash
# Festival notification automation
python manage.py send_festival_notifications --test
python manage.py send_festival_notifications --type=both

# Data cleanup and migration
python manage.py cleanup_orphaned_data
python manage.py create_missing_profiles
```

### Testing & Validation
- Form validation with custom clean methods
- API response validation for AI services
- Error handling with user-friendly messages
- Comprehensive logging for debugging

## Technical Challenges & Solutions

### AI Service Integration
- **Challenge**: Managing multiple AI APIs with different response formats
- **Solution**: Unified error handling and response processing patterns

### Image Processing Pipeline
- **Challenge**: Optimizing images for web while maintaining quality
- **Solution**: Pillow-based preprocessing with Cloudinary optimization

### Email Automation
- **Challenge**: Reliable email delivery with proper templating
- **Solution**: HTML email templates with plain text fallbacks

### User Experience
- **Challenge**: Providing intuitive AI interactions for non-technical users
- **Solution**: Context-aware prompts and progressive disclosure

## Future Enhancements

### Planned Features
- [ ] Multi-language support expansion
- [ ] Advanced analytics dashboard
- [ ] Social media integration
- [ ] Payment gateway integration
- [ ] Mobile app development
- [ ] Real-time collaboration features

### Technical Improvements
- [ ] Redis caching implementation
- [ ] Celery for background task processing
- [ ] API rate limiting and monitoring
- [ ] Advanced image generation models
- [ ] Machine learning for user behavior analysis

## Project Statistics

- **Lines of Code**: 980+ lines in views.py alone
- **Database Models**: 6 core models with relationships
- **AI Services**: 3 different AI providers integrated
- **Email Templates**: 2 HTML templates with responsive design
- **Management Commands**: 5 custom Django commands
- **Static Files**: Optimized with WhiteNoise for production

## Team & Development

**Team HustlePioneers** - Epsilon Hackathon 2025 Submission
- **Lead Developer**: Girish Yandigeri
- **Focus**: Empowering small businesses with accessible AI tools
- **Mission**: Democratizing AI-powered marketing for local entrepreneurs

---

*This project demonstrates advanced Django development practices, multi-AI service integration, and comprehensive automation systems suitable for production deployment.*
