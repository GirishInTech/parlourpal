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
from google.genai import types
from vertexai.language_models import TextGenerationModel


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
# 


import os
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from google.api_core.exceptions import GoogleAPIError
import traceback

# Construct the absolute path to the credentials file
# This assumes the 'secrets' directory is a subdirectory of your project's base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'secrets', 'image-gen-demo-epsilon-d9e1f100bfc8.json')

# Check if the file exists before trying to use it


if not os.path.exists(CREDENTIALS_PATH):
    print(f"CRITICAL: Credentials file not found at {CREDENTIALS_PATH}")
    imagen_model_preview = None
else:
    # Set the environment variable with the verified path
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH

    try:
        # Print debug information
        print(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        # Initialize Vertex AI
        vertexai.init(project=os.getenv('GCP_PROJECT_ID'), location="us-central1")


        # A balanced model that offers a good mix of quality and speed for general-purpose image generation.
        # Imagen_Model = "imagen-4.0-generate-preview-06-06"

        # A model optimized for speed and low latency, ideal for real-time applications.
        # Imagen_Model = "imagen-4.0-fast-generate-preview-06-06"

        # The highest quality model in the family, best for complex prompts, high detail, and accurate text rendering.
        Imagen_Model = "imagen-4.0-ultra-generate-preview-06-06"        

        imagen_model_preview = ImageGenerationModel.from_pretrained(Imagen_Model)
        
        
        if  imagen_model_preview:
            print(f"imagen_model_preview initialized successfully and is it {imagen_model_preview}")
            print(f"particular model is {Imagen_Model}")
        else:
            print("{imagen_model_preview} failed to initialize")
            print("particular model failed to initialize is {Imagen_Model}")
        print("SUCCESS: Vertex AI initialized successfully")

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"CRITICAL: Could not initialize Vertex AI. Error: {e}")
        print(f"DEBUG: Full error traceback: {error_details}")
        imagen_model_preview = None
















# -----------------
# 3. VIEW FUNCTIONS
# -----------------
# ... (home_view, register_view, login_view, etc. are unchanged) ...
def home_view(request):
    return render(request, 'core/home.html')

def register_view(request):
    if request.method == 'POST':
        user_form = RegisterForm(request.POST)
        profile_form = BusinessProfileForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                # Do NOT create BusinessProfile here; the signal will do it!
                # Optionally, update the profile with extra fields from the form:
                profile = user.businessprofile
                for field in ['business_name', 'description', 'image', 'image_url', 'location', 'phone', 'timing']:
                    value = profile_form.cleaned_data.get(field)
                    if value:
                        setattr(profile, field, value)
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
        profile_form = BusinessProfileForm()

    return render(request, 'core/register.html', {
        'user_form': user_form,
        'profile_form': profile_form
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
        prompt = f"""Task: Output only a funny and engaging social media caption for a business named {profile.business_name}.
Language: {language}
Business Name: {profile.business_name}
Services: {profile.description}
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
    Handles poster generation using the OLD 'preview' Vertex AI library.
    WARNING: This is for testing only and is not the recommended approach.
    """
    try:
        profile = BusinessProfile.objects.get(user=request.user)
    except BusinessProfile.DoesNotExist:
        messages.error(request, "You must create a business profile first.")
        return redirect('dashboard')

    poster_url = None

    if request.method == 'POST':
        # Check if imagen_model_preview is available
        if 'imagen_model_preview' not in globals() or imagen_model_preview is None:
            messages.error(request, "Poster generation is currently unavailable due to a configuration error. Please contact support.")
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
            location = profile.location if hasattr(profile, 'location') and profile.location else "Your Location"
            phone = profile.phone if hasattr(profile, 'phone') and profile.phone else "Your Phone"
            timing = profile.timing if hasattr(profile, 'timing') and profile.timing else "9:00 AM - 8:00 PM"
            
            prompt_text = f"""
Create a professional and eye-catching marketing poster for the business "{business_name}" to boost customer engagement and promote its latest offer.

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
                print(f"DEBUG: About to generate image with prompt: {prompt_text}")
                # --- MODIFICATION: Calling the old model's 'generate_images' method ---
                response = imagen_model_preview.generate_images(
                    prompt=prompt_text,
                    number_of_images=1,
                )

                print(f"DEBUG: Response: {response}")
                print(f"DEBUG: Response type: {type(response)}")
                print(f"DEBUG: Response attributes: {dir(response)}")

                # Check if response has images
                if hasattr(response, 'images') and response.images:
                    # Get the first image
                    image = response.images[0]
                    print(f"DEBUG: Got image: {image}")
                    
                    # Save the image
                    filename = f"{uuid.uuid4()}.png"
                    save_path = os.path.join(settings.MEDIA_ROOT, filename)
                    print(f"DEBUG: Attempting to save to: {save_path}")
                    
                    # Save the image bytes
                    with open(save_path, 'wb') as f:
                        f.write(image._image_bytes)
                    
                    print(f"DEBUG: Image saved successfully")

                    # Upload to Cloudinary
                    print("DEBUG: Uploading to Cloudinary...")
                    cloudinary_result = upload_image_to_cloudinary(
                        image._image_bytes,
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
                        
                        messages.success(request, "Poster generated successfully and uploaded to Cloudinary!")
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
                    print(f"DEBUG: No images in response")
                    print(f"DEBUG: Response.images: {getattr(response, 'images', 'No images attribute')}")
                    messages.warning(request, "Image could not be generated (it may have been blocked by safety filters).")

            except google.api_core.exceptions.ResourceExhausted as e:
                # You will STILL get this error if you make requests too quickly.
                messages.error(request, "🚦 Too many requests! Please wait a minute and try again.")
                print(f"Quota Error: {e}")
            except Exception as e:
                messages.error(request, f"An unexpected error occurred: {e}")
                print(f"General Error: {e}")

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
        if not user_message:
            return JsonResponse({'success': False, 'error': 'Empty message.'})

        # --- Fetch user business profile and recent activity ---
        profile = BusinessProfile.objects.filter(user=request.user).first()
        business_name = profile.business_name if profile and profile.business_name else "(not set)"
        description = profile.description if profile and profile.description else "(not set)"
        location = profile.location if profile and profile.location else "(not set)"
        phone = profile.phone if profile and profile.phone else "(not set)"
        timing = profile.timing if profile and profile.timing else "(not set)"
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

        # --- Build rich system prompt ---
        system_prompt = (
            "You are ParlorPal’s AI assistant. Here is the user’s business profile and recent activity to help you answer their questions as a helpful, friendly, and knowledgeable assistant.\n"
            f"Business Name: {business_name}\n"
            f"Description: {description}\n"
            f"Location: {location}\n"
            f"Phone: {phone}\n"
            f"Hours: {timing}\n"
            f"Email: {email}\n"
            f"Recent Posters: {poster_str}\n"
            f"Captions Generated: {caption_count}\n"
            "Help the user with any questions about their business, marketing, or navigating ParlorPal.\n"
            "If the user asks for captions, generate creative, engaging captions using their business info.\n"
            "If the user asks about their business, use the profile info above.\n"
            "If the user asks about navigation, explain how to use ParlorPal's features.\n"
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
