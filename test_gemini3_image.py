"""
Test script for Gemini 3 Pro Image (Nano Banana)
Run this to verify the model works before using it in Django
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

def test_gemini_3_image():
    """Test Gemini 3 Pro Image generation"""
    
    # Get API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in .env file")
        return
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    # Initialize client
    try:
        client = genai.Client(api_key=api_key)
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Simple test prompt
    prompt = """
    You are a creative director. Include emotional, atmospheric, and cultural details relevant to the promotion theme (e.g., festivals, seasons , etc). Keep the business details exact, but describe the visuals vividly.
 so , Create a professional and eye-catching marketing poster for the business "Omlette OMG" to boost customer engagement and promote its latest offer.

BUSINESS INFO:
- Business Name: Omlette OMG
- Business Type: Omlette OMG offers freshly prepared omelettes and quick meals, focused on quality ingredients, great taste, and fast service
- Location: Plot 42C, Sector 8, Navanagar, Bagalkot, Karnataka, India
- Phone: 6362905961
- Timing: 08:00 AM - 10:00 PM

PROMOTION:
- Promotion Name: New Year
- Main Offer: Buy Two Get One Free
- Language: English

DESIGN GUIDELINES:
- Format optimized for Instagram and WhatsApp sharing
- Display the business name clearly at the top
- Highlight the promotion name and main offer with bold and attractive fonts
- Use colors and typography that match the business theme
- Include relevant visuals or illustrations:
  - If Omlette OMG offers freshly prepared omelettes and quick meals, focused on quality ingredients, great taste, and fast service is "salon" or "beauty parlour",
  include an elegant image of a woman in format (Make sure the woman is fully clothed in a traditional or professional outfit, modest and elegant, suitable for a beauty parlour advertisement. Avoid sexualized or revealing imagery.) based on the culture of the business name to show beauty services
  - Otherwise, avoid human faces and use visuals/icons that match the business type (e.g., tools, tech, food)
- Keep the layout clean and easy to read on mobile
- Add marketing elements like badges, stickers, or call-to-action text (e.g., "Call Now", "Limited Offer", "Visit Today")
- Ensure the design remains professional, family-friendly, and suitable for public social media marketing. 

POSTER GOAL:
- Should look modern, polished, and shareable
- Designed to attract attention and drive real engagement on social media

DEBUG: About to generate image with prompt:
            You are a creative director. Include emotional, atmospheric, and cultural details relevant to the promotion theme (e.g., festivals, seasons , etc). Keep the business details exact, but describe the visuals vividly.
 so , Create a professional and eye-catching marketing poster for the business "Omlette OMG" to boost customer engagement and promote its latest offer.

BUSINESS INFO:
- Business Name: Omlette OMG
- Business Type: Omlette OMG offers freshly prepared omelettes and quick meals, focused on quality ingredients, great taste, and fast service
- Location: Plot 42C, Sector 8, Navanagar, Bagalkot, Karnataka, India
- Phone: 6362905961
- Timing: 08:00 AM - 10:00 PM

PROMOTION:
- Promotion Name: New Year
- Main Offer: Buy Two Get One Free
- Language: English

DESIGN GUIDELINES:
- Format optimized for Instagram and WhatsApp sharing
- Display the business name clearly at the top
- Highlight the promotion name and main offer with bold and attractive fonts
- Use colors and typography that match the business theme
- Include relevant visuals or illustrations:
  - If Omlette OMG offers freshly prepared omelettes and quick meals, focused on quality ingredients, great taste, and fast service is "salon" or "beauty parlour",
  include an elegant image of a woman in format (Make sure the woman is fully clothed in a traditional or professional outfit, modest and elegant, suitable for a beauty parlour advertisement. Avoid sexualized or revealing imagery.) based on the culture of the business name to show beauty services
  - Otherwise, avoid human faces and use visuals/icons that match the business type (e.g., tools, tech, food)
- Keep the layout clean and easy to read on mobile
- Add marketing elements like badges, stickers, or call-to-action text (e.g., "Call Now", "Limited Offer", "Visit Today")
- Ensure the design remains professional, family-friendly, and suitable for public social media marketing. 

POSTER GOAL:
- Should look modern, polished, and shareable
- Designed to attract attention and drive real engagement on social media
    """
    
    print(f"\n📝 Prompt: {prompt}")
    print("\n🔄 Generating image with gemini-3-pro-image-preview...")
    
    try:
        # Generate content
        config = types.GenerateContentConfig(
            response_modalities=['IMAGE']
        )
        
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[prompt],
            config=config
        )
        
        print(f"✅ Response received!")
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        print(f"\nResponse object: {response}")
        
        # Try to extract image
        if hasattr(response, 'candidates'):
            print(f"\n✅ Found candidates: {len(response.candidates)}")
            for i, candidate in enumerate(response.candidates):
                print(f"\nCandidate {i}:")
                print(f"  - Attributes: {dir(candidate)}")
                if hasattr(candidate, 'content'):
                    print(f"  - Has content")
                    content = candidate.content
                    if hasattr(content, 'parts'):
                        print(f"  - Has parts: {len(content.parts)}")
                        for j, part in enumerate(content.parts):
                            print(f"    Part {j}: {type(part)}")
                            if hasattr(part, 'inline_data'):
                                print(f"      ✅ Has inline_data!")
                                if hasattr(part.inline_data, 'data'):
                                    print(f"      ✅ Has data (image bytes)!")
                                    print(f"      Data length: {len(part.inline_data.data)} bytes")
                                    
                                    # Save the image
                                    from PIL import Image
                                    from io import BytesIO
                                    
                                    # Create testing folder if it doesn't exist
                                    os.makedirs("testing", exist_ok=True)
                                    
                                    # Data is already raw binary (not base64)
                                    image_data = part.inline_data.data
                                    pil_image = Image.open(BytesIO(image_data))
                                    
                                    output_path = "testing/test_gemini3_output.png"
                                    pil_image.save(output_path)
                                    print(f"\n🎉 SUCCESS! Image saved as '{output_path}'")
                                    print(f"   Size: {pil_image.size}")
                                    return True
        
        print("\n❌ No image data found in response")
        return False
        
    except Exception as e:
        print(f"\n❌ Error during generation: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Gemini 3 Pro Image (Nano Banana)")
    print("=" * 60)
    test_gemini_3_image()
