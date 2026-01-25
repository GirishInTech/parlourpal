# python
# core/views.py

# -----------------
# 1. IMPORTS
# -----------------
# Standard Library
import os
import uuid
from io import BytesIO
from datetime import datetime
import json
from urllib.parse import quote

# Third-Party Imports
import cohere
import vertexai
import google.api_core.exceptions
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Django Imports
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

# Local Application Imports
from .forms import RegisterForm, LoginForm, BusinessProfileForm
from .models import CustomUser, BusinessProfile, SearchHistory, Festival, PosterGeneration, UserHistory
from .email_utils import send_verification_email, send_festival_notifications, is_token_valid
from .cloudinary_utils import upload_image_to_cloudinary, optimize_image_for_cloudinary
# --- MODIFICATION: Using the old 'preview' library as requested ---
from vertexai.preview.vision_models import ImageGenerationModel
import google.generativeai as genai
from vertexai.language_models import TextGenerationModel
# --- NEW: Gemini 3 Pro Image (Nano Banana) for better text rendering ---
from google import genai as google_genai
from google.genai import types


# -----------------
# 2. INITIALIZATIONS
# -----------------
# Load environment variables from .env file
load_dotenv()

# Initialize Cohere Client once
try:
    cohere_client = cohere.Client(os.getenv("COHERE_API_KEY"))
except Exception as e:
    print(f"CRITICAL: Could not initialize Cohere client. Error: {e}")

# Initialize Vertex AI once
import os
import json
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.api_core.exceptions import GoogleAPIError
import traceback

# Handle Google credentials - support both file and environment variable
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'secrets', 'image-gen-demo-epsilon-d9e1f100bfc8.json')

# Try to set credentials from environment variable first (for production)
google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
if google_creds_json:
    # Production: credentials provided as JSON string in environment variable
    try:
        credentials_file = '/tmp/google-credentials.json'
        with open(credentials_file, 'w') as f:
            f.write(google_creds_json)
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_file
        print("SUCCESS: Using Google credentials from environment variable")
    except Exception as e:
        print(f"ERROR: Failed to write credentials from environment: {e}")
elif os.path.exists(CREDENTIALS_PATH):
    # Development: use local credentials file
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
    print(f"SUCCESS: Using local credentials file at {CREDENTIALS_PATH}")
else:
    print(f"WARNING: No Google credentials found. Image generation will not work.")

# Initialize Vertex AI
imagen_model_preview = None
try:
    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        vertexai.init(project=os.getenv('GCP_PROJECT_ID'), location="us-central1")

        # A balanced model that offers a good mix of quality and speed for general-purpose image generation.
        # Imagen_Model = "imagen-4.0-generate-preview-06-06"

        # A model optimized for speed and low latency, ideal for real-time applications.
        # Imagen_Model = "imagen-4.0-fast-generate-preview-06-06"

        # The highest quality model in the family, best for complex prompts, high detail, and accurate text rendering.
        # Imagen_Model = "imagen-4.0-ultra-generate-preview-06-06"


        # NOTE: We are now using Gemini 3 Pro Image (Nano Banana) via the generate_poster_gemini_3() function
        # This old Vertex AI initialization is kept for backwards compatibility but not actively used
        # Gemini 3 Pro Image is NOT available via ImageGenerationModel - it requires the google.genai library
        Imagen_Model = "imagen-4.0-ultra-generate-preview-06-06"  # Keep using Imagen as fallback


        imagen_model_preview = ImageGenerationModel.from_pretrained(Imagen_Model)
        
        if imagen_model_preview:
            print(f"imagen_model_preview initialized successfully: {imagen_model_preview}")
            print(f"Using model: {Imagen_Model}")
        else:
            print(f"imagen_model_preview failed to initialize")
            print(f"Model failed: {Imagen_Model}")
        print("SUCCESS: Vertex AI initialized successfully")
    else:
        print("WARNING: Skipping Vertex AI initialization - no credentials available")
except Exception as e:
    error_details = traceback.format_exc()
    print(f"CRITICAL: Could not initialize Vertex AI. Error: {e}")
    print(f"DEBUG: Full error traceback: {error_details}")
    imagen_model_preview = None


# -----------------
# 2B. GEMINI 3 PRO IMAGE INITIALIZATION (NANO BANANA)
# -----------------
def generate_poster_gemini_3(user_prompt):
    """
    Generates a poster using Gemini 3 Pro Image (Nano Banana).
    This model handles TEXT and EMOTIONS much better than Imagen.
    
    Args:
        user_prompt: The detailed prompt for poster generation
        
    Returns:
        PIL Image object if successful, None otherwise
    """
    try:
        # 1. Initialize the Client (different from Vertex AI)
        if not settings.GOOGLE_API_KEY:
            print("ERROR: GOOGLE_API_KEY not configured in settings.py")
            return None
            
        client = google_genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # 2. Define the Model ID (This is Nano Banana Pro)
        model_id = "gemini-3-pro-image-preview"
        
        # 3. Create a config to ensure high quality (simplified config)
        config = types.GenerateContentConfig(
            response_modalities=['IMAGE']  # Request an image back
        )
        
        print(f"DEBUG: Sending prompt to {model_id} (Nano Banana)...")
        
        # 4. Generate content
        response = client.models.generate_content(
            model=model_id,
            contents=[user_prompt],
            config=config
        )
        
        print(f"DEBUG: Received response from Gemini 3 Pro Image")
        
        # 5. Extract the Image - EXACT same logic as working test script
        if hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and candidate.content:
                    content = candidate.content
                    if hasattr(content, 'parts') and content.parts:
                        for part in content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                if hasattr(part.inline_data, 'data'):
                                    # Data is already raw binary (not base64)
                                    image_data = part.inline_data.data
                                    pil_image = Image.open(BytesIO(image_data))
                                    print(f"DEBUG: Successfully extracted PIL Image")
                                    print(f"DEBUG: Image size: {pil_image.size}")
                                    return pil_image
        
        print("WARNING: No image found in Gemini 3 Pro response")
        return None
        
    except Exception as e:
        print(f"ERROR: Gemini 3 Pro Image generation failed: {e}")
        print(f"DEBUG: Full error traceback: {traceback.format_exc()}")
        return None


# -----------------
# 3. VIEW FUNCTIONS
# -----------------
# ... (home_view, register_view, login_view, etc. are unchanged) ...
def home_view(request):
    return render(request, 'core/home.html')

def register_view(request):
    if request.method == 'POST':
        user_form = RegisterForm(request.POST)
        if user_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                # Update the business profile (created by signal) with form data
                profile = user.businessprofile
                profile.business_name = user_form.cleaned_data.get('business_name') or f"{user.username}'s Business"
                profile.country = user_form.cleaned_data.get('country', '')
                profile.state = user_form.cleaned_data.get('state', '')
                profile.district = user_form.cleaned_data.get('district', '')
                profile.town = user_form.cleaned_data.get('town', '')
                profile.address = user_form.cleaned_data.get('address', '')
                profile.phone = user_form.cleaned_data.get('phone', '')
                profile.business_hours_start = user_form.cleaned_data.get('business_hours_start')
                profile.business_hours_end = user_form.cleaned_data.get('business_hours_end')
                profile.save()
            # Send verification email
            if send_verification_email(user):
                messages.success(request, "🎉 Registration successful! Please check your email to verify your account.")
            else:
                messages.warning(request, "Registration successful! Please log in. (Email verification failed)")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = RegisterForm()

    return render(request, 'core/register.html', {
        'form': user_form
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                # Direct login without 2FA
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('home')


def two_factor_view(request):
    """Handle TOTP 2FA: show QR on first setup and verify codes on every login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return redirect('login')

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        messages.error(request, "Session expired. Please login again.")
        return redirect('login')

    # Get or create 2FA record
    tfa, _created = TwoFactorAuth.objects.get_or_create(user=user)
    # Generate a secret if missing, but keep showing QR until enabled
    if not tfa.secret:
        tfa.secret = pyotp.random_base32()
        tfa.enabled = False
        tfa.save()
    show_qr = not tfa.enabled

    totp = pyotp.TOTP(tfa.secret)
    issuer = 'ParlorPal'
    account_name = user.email or user.username
    provisioning_uri = totp.provisioning_uri(name=account_name, issuer_name=issuer)
    # Use QuickChart for QR (more reliable in some networks)
    qr_url = f"https://quickchart.io/qr?text={quote(provisioning_uri)}&size=200&margin=2"

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if not code:
            messages.error(request, 'Please enter the 6-digit code from your authenticator app.')
        else:
            if totp.verify(code, valid_window=1):
                # Mark enabled if first time
                if not tfa.enabled:
                    from django.utils import timezone
                    tfa.enabled = True
                    tfa.last_verified_at = timezone.now()
                    tfa.save()

                # Complete login now
                login(request, user)
                try:
                    del request.session['pre_2fa_user_id']
                except KeyError:
                    pass
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid code. Please try again.')

    context = {
        'user_obj': user,
        'show_qr': show_qr,
        'qr_url': qr_url,
        'issuer': issuer,
        'account_name': account_name,
        'secret': tfa.secret,
        'provisioning_uri': provisioning_uri,
    }
    return render(request, 'core/two_factor.html', context)

@login_required
def dashboard_view(request):
    from datetime import datetime, timedelta
    from django.utils import timezone
    profile = BusinessProfile.objects.filter(user=request.user).first()
    # Agentic journey logic
    from .models import UserHistory
    user_history = UserHistory.objects.filter(user=request.user)
    poster_count = user_history.filter(action_type='poster_generation').count()
    caption_count = user_history.filter(action_type='text_generation').count()
    last_activity = user_history.order_by('-created_at').first()
    suggestion = None
    now = timezone.now()
    # Determine journey stage and suggestion
    if poster_count == 0 and caption_count == 0:
        suggestion = "Welcome! Start by generating your first poster or caption to see the magic of AI marketing."
    elif poster_count > 0 and caption_count == 0:
        suggestion = "Great job creating posters! Try generating a catchy caption to boost your next campaign."
    elif poster_count == 0 and caption_count > 0:
        suggestion = "Awesome captions! How about designing a stunning poster to go with your content?"
    elif last_activity and (now - last_activity.created_at).days >= 7:
        suggestion = "We miss you! It's been a while—generate new content to re-engage your audience."
    else:
        suggestion = "Keep up the great work! Explore more AI tools to supercharge your marketing."
    return render(request, 'core/dashboard.html', {
        'user': request.user, 
        'profile': profile,
        'current_date': now,
        'suggestion': suggestion
    })

@login_required
def ai_suggestions_view(request):
    try:
        profile = BusinessProfile.objects.get(user=request.user)
    except BusinessProfile.DoesNotExist:
        # If no business profile exists, show a form to create one
        if request.method == 'POST':
            profile_form = BusinessProfileForm(request.POST, request.FILES)
            if profile_form.is_valid():
                profile = profile_form.save(commit=False)
                profile.user = request.user
                profile.save()
                messages.success(request, "Business profile created successfully!")
                return redirect('ai_suggestions')
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            profile_form = BusinessProfileForm()
        
        return render(request, 'core/create_profile.html', {
            'profile_form': profile_form,
            'user': request.user
        })
    
    marketing_text = ""
    
    # Get previous searches for this user (last 10)
    previous_searches = SearchHistory.objects.filter(user=request.user)[:10]
    
    if request.method == "POST":
        user_input = request.POST.get("user_input", "").strip()
        language = request.POST.get("language", "english")
        length = request.POST.get("length", "small")
        
        if user_input:  # Only save if there's actual input
            # Save search to history (this will handle duplicates automatically due to unique_together)
            SearchHistory.objects.get_or_create(
                user=request.user,
                search_query=user_input
            )
        
        token_map = {"small": 100, "medium": 200, "long": 300}
        max_tokens = token_map.get(length, 100)
        # Get location details
        location_parts = []
        if profile.town:
            location_parts.append(profile.town)
        if profile.state:
            location_parts.append(profile.state)
        location_str = ", ".join(location_parts) if location_parts else "your area"
        
        prompt = f"""Task: Output only a funny and engaging social media caption for a business named {profile.business_name}.
Language: {language}
Business Name: {profile.business_name}
Services: {profile.description}
Location: {location_str}
Focus: {user_input}
Instructions: Use at least 4 relevant emojis. Output only the caption text."""
        try:
            response = cohere_client.generate(
                model="command",
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.7
            )
            marketing_text = response.generations[0].text.strip()
        except Exception as e:
            marketing_text = f"❌ Error: {str(e)}"
        
        # Track text generation in user history
        # Only save if not an error message
        if marketing_text and not marketing_text.startswith("❌ Error:"):
            UserHistory.objects.create(
                user=request.user,
                action_type='text_generation',
                input_data={
                    'user_input': user_input,
                    'language': language,
                    'length': length
                },
                output_data=marketing_text,
                prompt_used=prompt
            )
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            print(f"DEBUG: AJAX request received. Marketing text: {marketing_text[:100]}...")
            try:
                return JsonResponse({
                    'success': True,
                    'marketing_text': marketing_text
                })
            except Exception as e:
                print(f"DEBUG: Error in AJAX response: {e}")
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
    
    return render(request, 'core/ai_suggestions.html', {
        'marketing_text': marketing_text,
        'profile': profile,
        'previous_searches': previous_searches
    })

@login_required
def feedback_view(request):
    return render(request, "core/feedback.html")

@login_required
def user_history_view(request):
    """View for displaying user's complete activity history"""
    user_history = UserHistory.objects.filter(user=request.user)
    
    # Filter by action type if requested
    action_type = request.GET.get('action_type')
    if action_type:
        user_history = user_history.filter(action_type=action_type)
    
    # Get statistics
    total_activities = user_history.count()
    poster_count = user_history.filter(action_type='poster_generation').count()
    text_count = user_history.filter(action_type='text_generation').count()
    logo_count = user_history.filter(action_type='logo_upload').count()
    
    context = {
        'user_history': user_history,
        'total_activities': total_activities,
        'poster_count': poster_count,
        'text_count': text_count,
        'logo_count': logo_count,
        'action_types': UserHistory.ACTION_TYPES,
        'current_filter': action_type
    }
    
    return render(request, 'core/user_history.html', context)

@login_required
def profile_view(request):
    # Get or create business profile
    profile, created = BusinessProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        profile_form = BusinessProfileForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid():
            # Handle logo upload to Cloudinary
            if 'image' in request.FILES:
                logo_file = request.FILES['image']
                print(f"DEBUG: Logo upload - {logo_file.name}, size: {logo_file.size}")
                
                # Upload to Cloudinary
                from .cloudinary_utils import upload_file_to_cloudinary
                cloudinary_result = upload_file_to_cloudinary(
                    logo_file,
                    folder="logos",
                    public_id=f"logo_{request.user.username}_{uuid.uuid4().hex[:8]}"
                )
                
                if cloudinary_result['success']:
                    profile.image_url = cloudinary_result['url']
                    print(f"DEBUG: Logo uploaded to Cloudinary: {profile.image_url}")
                    
                    # Track logo upload in user history
                    UserHistory.objects.create(
                        user=request.user,
                        action_type='logo_upload',
                        input_data={
                            'filename': logo_file.name,
                            'file_size': logo_file.size,
                            'content_type': logo_file.content_type
                        },
                        output_data=profile.image_url,
                        prompt_used="Logo upload"
                    )
                    
                    messages.success(request, "Logo uploaded successfully to Cloudinary!")
                else:
                    print(f"DEBUG: Cloudinary upload failed: {cloudinary_result['error']}")
                    messages.warning(request, "Logo upload to Cloudinary failed. Using local storage.")
            
            # Save the profile
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        profile_form = BusinessProfileForm(instance=profile)
    """View for user profile details and editing"""
    try:
        profile = BusinessProfile.objects.get(user=request.user)
    except BusinessProfile.DoesNotExist:
        messages.error(request, "Business profile not found.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Handle profile updates
        profile_form = BusinessProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        

        
        if profile_form.is_valid():
            # Save business profile
            profile_form.save()
            
            # Update user email if changed
            new_email = profile_form.cleaned_data.get('email')
            
            if new_email and new_email != request.user.email:
                # Check if email is already taken by another user
                if CustomUser.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                    messages.error(request, "This email is already registered by another user.")
                else:
                    old_email = request.user.email
                    request.user.email = new_email
                    # Reset email verification if email changed
                    request.user.email_verified = False
                    request.user.verification_token = ''  # Empty string instead of None
                    request.user.token_created_at = None
                    request.user.save()
                    
                    # Send new verification email
                    try:
                        from .email_utils import send_verification_email
                        if send_verification_email(request.user):
                            messages.success(request, "Profile updated successfully! A new verification email has been sent to your new email address.")
                        else:
                            messages.warning(request, "Profile updated successfully! However, the verification email could not be sent. Please check your Gmail settings in the .env file.")
                    except Exception as e:
                        messages.warning(request, f"Profile updated successfully! However, there was an issue sending the verification email. Please configure your Gmail credentials in the .env file. Error: {str(e)}")
            else:
                messages.success(request, "Profile updated successfully!")
            
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        profile_form = BusinessProfileForm(instance=profile, user=request.user)
    
    # Get user's search history for statistics
    search_history = SearchHistory.objects.filter(user=request.user)
    total_searches = search_history.count()
    recent_searches = search_history[:5]  # Last 5 searches
    
    # Get user's poster generation statistics
    poster_generations = PosterGeneration.objects.filter(user=request.user)
    total_posters = poster_generations.count()
    recent_posters = poster_generations[:5]  # Last 5 posters
    
    # Get user's video generation statistics
    from .models import UserHistory
    video_count = UserHistory.objects.filter(user=request.user, action_type='video_generation').count()

    context = {
        'profile': profile,
        'profile_form': profile_form,
        'total_searches': total_searches,
        'recent_searches': recent_searches,
        'total_posters': total_posters,
        'recent_posters': recent_posters,
        'video_count': video_count,
        'user': request.user,
    }
    return render(request, "core/profile.html", context)


@login_required
def poster_generator_view(request):
    """
    Handles poster generation using Gemini 3 Pro Image (Nano Banana).
    This model has better text rendering and emotional understanding than Imagen.
    """
    try:
        profile = BusinessProfile.objects.get(user=request.user)
    except BusinessProfile.DoesNotExist:
        messages.error(request, "You must create a business profile first.")
        return redirect('dashboard')

    poster_url = None
    
    # Always load the most recent poster for this user (in case of timeout/broken pipe)
    latest_poster = PosterGeneration.objects.filter(user=request.user).order_by('-id').first()
    if latest_poster:
        poster_url = latest_poster.poster_url
        print(f"DEBUG: Loaded latest poster from DB: {poster_url}")

    if request.method == 'POST':
        # Check if GOOGLE_API_KEY is configured
        if not settings.GOOGLE_API_KEY:
            messages.error(request, "Poster generation is currently unavailable. Please configure GOOGLE_API_KEY in your .env file.")
            return redirect('dashboard')
        promotion_name = request.POST.get("promotion_name", "").strip()
        offer_type = request.POST.get("offer_type")
        custom_offer = request.POST.get("custom_offer")
        language = request.POST.get("language")

        if not promotion_name:
            messages.error(request, "Please provide a promotion name.")
        else:
            final_offer = custom_offer if offer_type == "Other" else offer_type
            
            # Extract key business details for marketing
            business_name = profile.business_name
            business_type = profile.description.split('.')[0] if profile.description else "Business"
            
            # Build location string from detailed fields
            location_parts = []
            if profile.town:
                location_parts.append(profile.town)
            if profile.district:
                location_parts.append(profile.district)
            if profile.state:
                location_parts.append(profile.state)
            if profile.country:
                location_parts.append(profile.country)
            location = ", ".join(location_parts) if location_parts else "Your Location"
            
            # Add detailed address if available
            if profile.address:
                location = f"{profile.address}, {location}"
            
            phone = profile.phone if profile.phone else "Your Phone"
            
            # Format business hours
            if profile.business_hours_start and profile.business_hours_end:
                timing = f"{profile.business_hours_start.strftime('%I:%M %p')} - {profile.business_hours_end.strftime('%I:%M %p')}"
            else:
                timing = "9:00 AM - 8:00 PM"
            
            prompt_text = f"""
            You are a creative director. Include emotional, atmospheric, and cultural details relevant to the promotion theme (e.g., festivals, seasons , etc). Keep the business details exact, but describe the visuals vividly.
 so , Create a professional and eye-catching marketing poster for the business "{business_name}" to boost customer engagement and promote its latest offer.

BUSINESS INFO:
- Business Name: {business_name}
- Business Type: {business_type}
- Location: {location}
- Phone: {phone}
- Timing: {timing}

PROMOTION:
- Promotion Name: {promotion_name}
- Main Offer: {final_offer}
- Language: {language}

DESIGN GUIDELINES:
- Format optimized for Instagram and WhatsApp sharing
- Display the business name clearly at the top
- Highlight the promotion name and main offer with bold and attractive fonts
- Use colors and typography that match the business theme
- Include relevant visuals or illustrations:
  - If {business_type} is "salon" or "beauty parlour", 
  include an elegant image of a woman in format (Make sure the woman is fully clothed in a traditional or professional outfit, modest and elegant, suitable for a beauty parlour advertisement. Avoid sexualized or revealing imagery.) based on the culture of the business name to show beauty services
  - Otherwise, avoid human faces and use visuals/icons that match the business type (e.g., tools, tech, food)
- Keep the layout clean and easy to read on mobile
- Add marketing elements like badges, stickers, or call-to-action text (e.g., "Call Now", "Limited Offer", "Visit Today")
- Ensure the design remains professional, family-friendly, and suitable for public social media marketing.

POSTER GOAL:
- Should look modern, polished, and shareable
- Designed to attract attention and drive real engagement on social media
"""




            
            print(prompt_text)
            try:
                print(f"DEBUG: About to generate image with Gemini 3 Pro Image (Nano Banana)")
                
                # --- NEW: Using Gemini 3 Pro Image (Nano Banana) for better text rendering ---
                pil_image = generate_poster_gemini_3(prompt_text)
                
                if pil_image:
                    print(f"DEBUG: Successfully generated PIL Image")
                    
                    # Convert PIL Image to bytes
                    img_byte_arr = BytesIO()
                    pil_image.save(img_byte_arr, format='PNG')
                    image_bytes = img_byte_arr.getvalue()
                    
                    # Save the image locally
                    filename = f"{uuid.uuid4()}.png"
                    save_path = os.path.join(settings.MEDIA_ROOT, filename)
                    print(f"DEBUG: Attempting to save to: {save_path}")
                    
                    # Save the image bytes
                    with open(save_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    print(f"DEBUG: Image saved successfully")

                    # Upload to Cloudinary
                    print("DEBUG: Uploading to Cloudinary...")
                    cloudinary_result = upload_image_to_cloudinary(
                        image_bytes,
                        folder="posters",
                        public_id=f"poster_{request.user.username}_{uuid.uuid4().hex[:8]}"
                    )
                    
                    if cloudinary_result['success']:
                        poster_url = cloudinary_result['url']
                        print(f"DEBUG: Cloudinary URL = {poster_url}")
                        
                        # Track poster generation
                        PosterGeneration.objects.create(
                            user=request.user,
                            promotion_name=promotion_name,
                            offer_type=final_offer,
                            poster_url=poster_url
                        )
                        
                        # Track in user history
                        UserHistory.objects.create(
                            user=request.user,
                            action_type='poster_generation',
                            input_data={
                                'promotion_name': promotion_name,
                                'offer_type': final_offer,
                                'language': language,
                                'business_name': business_name,
                                'location': location,
                                'phone': phone,
                                'timing': timing
                            },
                            output_data=poster_url,
                            prompt_used=prompt_text
                        )
                        
                        print(f"DEBUG: About to return response with poster_url = {poster_url}")
                        messages.success(request, "🎉 Poster generated successfully! Check below.")
                    else:
                        print(f"DEBUG: Cloudinary upload failed: {cloudinary_result['error']}")
                        # Fallback to local storage
                        poster_url = settings.MEDIA_URL + filename
                        PosterGeneration.objects.create(
                            user=request.user,
                            promotion_name=promotion_name,
                            offer_type=final_offer,
                            poster_url=poster_url
                        )
                        messages.warning(request, "Poster generated but Cloudinary upload failed. Using local storage.")
                else:
                    print(f"DEBUG: Gemini 3 Pro Image failed to generate an image")
                    messages.warning(request, "Image could not be generated (it may have been blocked by safety filters).")

            except google.api_core.exceptions.ResourceExhausted as e:
                # You will STILL get this error if you make requests too quickly.
                messages.error(request, "🚦 Too many requests! Please wait a minute and try again.")
                print(f"Quota Error: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
                print(f"General Error: {e}")
                import traceback
                print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        
        # Redirect after POST to prevent resubmission on refresh
        return redirect('poster_generator')

    context = {
        'profile': profile,
        'poster_url': poster_url,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, "core/generate_poster.html", context)


@login_required
def insights_view(request):
    from datetime import timedelta
    from django.utils import timezone
    user = request.user
    # Aggregate stats
    user_history = UserHistory.objects.filter(user=user)
    poster_count = user_history.filter(action_type='poster_generation').count()
    text_count = user_history.filter(action_type='text_generation').count()
    logo_count = user_history.filter(action_type='logo_upload').count()
    video_count = user_history.filter(action_type='video_generation').count()
    total_activities = user_history.count()

    # Poster generation trend (last 30 days)
    today = timezone.now().date()
    trend_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        count = user_history.filter(action_type='poster_generation', created_at__date=day).count()
        trend_data.append({'date': day.strftime('%Y-%m-%d'), 'count': count})

    context = {
        'poster_count': poster_count,
        'text_count': text_count,
        'logo_count': logo_count,
        'video_count': video_count,
        'total_activities': total_activities,
        'trend_data_json': json.dumps(trend_data),
    }
    return render(request, 'core/insights.html', context)


# Email Verification Views

def verify_email_view(request, token):
    """Verify user email with token"""
    try:
        # Find user with this token
        user = CustomUser.objects.get(verification_token=token)
        
        # Check if token is valid and not expired
        if is_token_valid(user, token):
            # Mark email as verified
            user.email_verified = True
            user.verification_token = ''  # Clear the token
            user.token_created_at = None
            user.save()
            
            messages.success(request, "🎉 Email verified successfully! You can now receive festival notifications.")
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Verification link has expired. Please request a new one.")
            return redirect('dashboard')
            
    except CustomUser.DoesNotExist:
        messages.error(request, "❌ Invalid verification link.")
        return redirect('dashboard')


@login_required
def resend_verification_email(request):
    """Resend verification email to user"""
    if request.user.email_verified:
        messages.info(request, "Your email is already verified!")
        return redirect('dashboard')
    
    try:
        if send_verification_email(request.user):
            messages.success(request, "📧 Verification email sent! Please check your inbox.")
        else:
            messages.error(request, "❌ Failed to send verification email. Please check your Gmail settings in the .env file.")
    except Exception as e:
        messages.error(request, f"❌ Failed to send verification email. Please configure your Gmail credentials in the .env file. Error: {str(e)}")
    
    return redirect('dashboard')


@login_required
def toggle_notifications(request):
    """Toggle festival notifications on/off"""
    if not request.user.email_verified:
        messages.error(request, "❌ Please verify your email first to enable notifications.")
        return redirect('dashboard')
    
    # Toggle notification setting
    request.user.notifications_enabled = not request.user.notifications_enabled
    request.user.save()
    
    status = "enabled" if request.user.notifications_enabled else "disabled"
    messages.success(request, f"🔔 Festival notifications {status}!")
    
    return redirect('dashboard')


def unsubscribe_view(request, user_id):
    """Unsubscribe user from festival notifications"""
    try:
        user = CustomUser.objects.get(id=user_id)
        user.notifications_enabled = False
        user.save()
        messages.success(request, "🔕 You have been unsubscribed from festival notifications.")
    except CustomUser.DoesNotExist:
        messages.error(request, "❌ Invalid unsubscribe link.")
    
    return redirect('home')


@login_required
def manage_festivals_view(request):
    """Admin view to manage festivals"""
    if not request.user.is_staff:
        messages.error(request, "❌ Access denied. Admin privileges required.")
        return redirect('dashboard')
    
    festivals = Festival.objects.all().order_by('date')
    
    if request.method == 'POST':
        # Add new festival
        name = request.POST.get('name')
        date = request.POST.get('date')
        notification_days = request.POST.get('notification_days', 3)
        send_on_festival_day = request.POST.get('send_on_festival_day') == 'on'
        
        if name and date:
            Festival.objects.create(
                name=name,
                date=date,
                notification_days=notification_days,
                send_on_festival_day=send_on_festival_day
            )
            messages.success(request, f"🎊 Festival '{name}' added successfully!")
            return redirect('manage_festivals')
    
    return render(request, 'core/manage_festivals.html', {
        'festivals': festivals
    })

def preview_verification_email(request):
    """Preview the verification email template"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('dashboard')
    
    # Mock data for preview
    context = {
        'site_name': 'ParlorPal',
        'user': request.user,
        'verification_url': 'https://example.com/verify/token123',
        'site_url': 'https://parlorpal.com'
    }
    return render(request, 'core/emails/verification_email.html', context)

def preview_festival_notification(request):
    """Preview the festival notification email template"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('dashboard')
    
    # Mock data for preview
    from datetime import date, timedelta
    context = {
        'site_name': 'ParlorPal',
        'user': request.user,
        'festival': {
            'name': 'Diwali',
            'date': date.today() + timedelta(days=5),
            'notification_days': 5
        },
        'site_url': 'https://parlorpal.com'
    }
    return render(request, 'core/emails/festival_notification.html', context)

def email_templates_view(request):
    """Display all email templates with preview links"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('dashboard')
    
    return render(request, 'core/email_templates.html')

@login_required
@csrf_exempt
def chatbot_view(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        user_message = request.POST.get('message', '').strip()
        current_page = request.POST.get('current_page', '').strip()
        page_content = request.POST.get('page_content', '').strip()
        if not user_message:
            return JsonResponse({'success': False, 'error': 'Empty message.'})

        # --- Fetch user business profile and recent activity ---
        profile = BusinessProfile.objects.filter(user=request.user).first()
        business_name = profile.business_name if profile and profile.business_name else "(not set)"
        description = profile.description if profile and profile.description else "(not set)"
        
        # Location details
        country = profile.country if profile and profile.country else "(not set)"
        state = profile.state if profile and profile.state else "(not set)"
        district = profile.district if profile and profile.district else "(not set)"
        town = profile.town if profile and profile.town else "(not set)"
        address = profile.address if profile and profile.address else "(not set)"
        full_location = f"{town}, {district}, {state}, {country}" if all([town, district, state, country]) else "(not set)"
        
        phone = profile.phone if profile and profile.phone else "(not set)"
        
        # Business hours
        if profile and profile.business_hours_start and profile.business_hours_end:
            timing = f"{profile.business_hours_start.strftime('%I:%M %p')} - {profile.business_hours_end.strftime('%I:%M %p')}"
        else:
            timing = "(not set)"
        
        email = request.user.email if hasattr(request.user, 'email') else "(not set)"

        # Recent posters
        from core.models import PosterGeneration, UserHistory
        last_posters = PosterGeneration.objects.filter(user=request.user).order_by('-id')[:3]
        poster_list = []
        for poster in last_posters:
            poster_list.append(f"{poster.promotion_name} ({poster.offer_type})")
        poster_str = ", ".join(poster_list) if poster_list else "No posters generated yet."

        # Caption count
        caption_count = UserHistory.objects.filter(user=request.user, action_type='text_generation').count()

        # --- Multi-turn context: Store and use last 10 turns ---
        history = request.session.get('chat_history', [])
        history.append({'role': 'user', 'content': user_message})

        # Build page-specific context
        page_context = ""
        if current_page:
            page_context = f"\n\nCURRENT PAGE: {current_page}"
            if page_content:
                page_context += f"\n\nPAGE CONTENT (form fields, buttons, and elements visible to user):\n{page_content}\n\nUse this page content to help the user. If they ask about inputs, options, or features on the current page, refer to the PAGE CONTENT above."
            else:
                page_context += "\nThe user is currently on this page. Help them based on the page URL and context."

        # --- Build rich system prompt ---
        system_prompt = (
            "You are ParlorPal’s AI assistant. Here is the user’s business profile and recent activity to help you answer their questions as a helpful, friendly, and knowledgeable assistant.\n"
            f"Business Name: {business_name}\n"
            f"Description: {description}\n"
            f"Location: {full_location}\n" + f"Detailed Address: {address}\n"
            f"Phone: {phone}\n"
            f"Business Hours: {timing}\n"
            f"Email: {email}\n"
            f"Recent Posters: {poster_str}\n"
            f"Captions Generated: {caption_count}\n"
            f"{page_context}\n"
            "Help the user with any questions about their business, marketing, or navigating ParlorPal.\n"
            "If the user asks for captions, generate creative, engaging captions using their business info.\n"
            "If the user asks about their business, use the profile info above.\n"
            "If the user asks about navigation or what page they're on, use the CURRENT PAGE context above.\n"
            "Always answer naturally and conversationally, as a real human assistant would.\n"
        )
        prompt_parts = [system_prompt]
        for msg in history[-10:]:
            prefix = "User:" if msg['role'] == 'user' else "Bot:"
            prompt_parts.append(f"{prefix} {msg['content']}")
        full_prompt = "\n".join(prompt_parts)

        try:
            from google import genai
            from google.genai import types
            import os
            client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            ai_reply = response.text
            history.append({'role': 'bot', 'content': ai_reply})
            request.session['chat_history'] = history[-10:]
            return JsonResponse({'success': True, 'reply': ai_reply})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        # Optionally clear history on GET
        request.session['chat_history'] = []
        return render(request, 'core/chatbot.html', {'user': request.user})

def email_subjects_view(request):
    from django.contrib.auth.decorators import login_required
    from django.utils.decorators import method_decorator
    @login_required
    def inner(request):
        subject_lines = []
        error = None
        profile = BusinessProfile.objects.filter(user=request.user).first()
        business_name = profile.business_name if profile and profile.business_name else "(not set)"
        description = profile.description if profile and profile.description else "(not set)"
        if request.method == 'POST':
            offer = request.POST.get('offer', '').strip()
            audience = request.POST.get('audience', '').strip()
            tone = request.POST.get('tone', '').strip()
            prompt = (
                f"Suggest 5 engaging email subject lines for a business named '{business_name}'. "
                f"Description: {description}. "
                f"Offer: {offer}. "
                f"Target audience: {audience}. "
                f"Tone: {tone}. "
                "Make them catchy, relevant, and suitable for a marketing campaign."
            )
            try:
                from google import genai
                from google.genai import types
                import os
                client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0)
                    )
                )
                # Split lines if possible
                lines = response.text.strip().split('\n')
                subject_lines = [line for line in lines if line.strip()]
            except Exception as e:
                error = str(e)
        return render(request, 'core/email_subjects.html', {
            'subject_lines': subject_lines,
            'error': error,
            'profile': profile
        })
    return inner(request)

def generate_video_view(request):
    import os
    import time
    import requests
    from django.contrib.auth.decorators import login_required
    from django.utils.decorators import method_decorator
    from .models import BusinessProfile
    from django.conf import settings
    video_url = None
    error = None
    if request.method == 'POST':
        campaign_name = request.POST.get('campaign_name', '').strip()
        if campaign_name == 'Other':
            campaign_name = request.POST.get('campaign_name_custom', '').strip()
        theme = request.POST.get('theme', '').strip()
        if theme == 'Other':
            theme = request.POST.get('theme_custom', '').strip()
        aspect_ratio = request.POST.get('aspect_ratio', '16:9')
        script = request.POST.get('script', '').strip()
        api_key = os.getenv('GOOGLE_VERTEX_API_KEY')
        # Fetch business profile details
        profile = BusinessProfile.objects.filter(user=request.user).first()
        business_name = profile.business_name if profile and profile.business_name else ""
        description = profile.description if profile and profile.description else ""
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            prompt = (
                f"Generate a marketing video using the following details.\n"
                f"Script: {script}\n"
                f"Theme: {theme}\n"
                f"Campaign Name: {campaign_name}\n"
                f"\nUse the details below as reference only (do not include verbatim):\n"
                f"Business Name: {business_name}\n"
                f"Description: {description}"
            )
            operation = client.models.generate_videos(
                model="veo-3.0-generate-preview",
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    person_generation="allow_all",
                    aspect_ratio=aspect_ratio,
                ),
            )
            # Wait for operation to complete (polling)
            for _ in range(30):  # Wait up to 10 minutes (20s * 30)
                if operation.done:
                    break
                time.sleep(20)
                operation = client.operations.get(operation)
            if operation.done and hasattr(operation.response, 'generated_videos') and operation.response.generated_videos:
                generated_video = operation.response.generated_videos[0]
                if hasattr(generated_video.video, 'uri'):
                    video_uri = generated_video.video.uri
                    # Download the video file and save to media/videos
                    try:
                        media_videos_path = os.path.join(settings.MEDIA_ROOT, 'videos')
                        os.makedirs(media_videos_path, exist_ok=True)
                        filename = f"video_{int(time.time())}.mp4"
                        file_path = os.path.join(media_videos_path, filename)
                        r = requests.get(video_uri, stream=True)
                        if r.status_code == 200:
                            with open(file_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            video_url = settings.MEDIA_URL + f"videos/{filename}"
                        else:
                            error = 'Failed to download generated video.'
                            video_url = 'https://www.w3schools.com/html/mov_bbb.mp4'  # Fallback
                    except Exception as e:
                        error = f"Video download failed: {str(e)}"
                        video_url = 'https://www.w3schools.com/html/mov_bbb.mp4'  # Fallback
                else:
                    video_url = 'https://www.w3schools.com/html/mov_bbb.mp4'  # Fallback
            else:
                error = 'Video generation did not complete successfully.'
        except Exception as e:
            error = f"Video generation failed: {str(e)}"
            video_url = 'https://www.w3schools.com/html/mov_bbb.mp4'  # Fallback
    return render(request, 'core/generate_video.html', {
        'video_url': video_url,
        'error': error
    })

