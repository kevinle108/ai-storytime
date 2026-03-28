"""
Test script for Hugging Face Inference API - Image Generation

This script tests generating images using the Hugging Face Inference API
with the FLUX.1-schnell model (fast and free-tier friendly).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if huggingface_hub is installed
try:
    from huggingface_hub import InferenceClient
    print("✓ huggingface_hub imported successfully")
except ImportError:
    print("❌ huggingface_hub not installed")
    print("Install it with: pip install huggingface_hub")
    exit(1)

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN")
OUTPUT_DIR = Path(__file__).parent / "output"

def test_image_generation():
    """Test image generation with Hugging Face Inference API"""
    
    print("\n" + "=" * 60)
    print("🎨 Testing Hugging Face Image Generation API")
    print("=" * 60)
    
    # Check for token
    if not HF_TOKEN:
        print("\n⚠️  HF_TOKEN not found in .env file")
        print("Setup instructions:")
        print("1. Go to https://huggingface.co/settings/tokens")
        print("2. Create a token with 'Make calls to Inference Providers' permission")
        print("3. Add HF_TOKEN=your_token to .env file")
        return
    
    print(f"\n✓ HF_TOKEN found (length: {len(HF_TOKEN)})")
    
    # Initialize client
    print("\n📡 Initializing Hugging Face Inference Client...")
    try:
        client = InferenceClient(api_key=HF_TOKEN)
        print("✓ Client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Test prompts
    test_prompts = [
        "pikachu going to the park, children's book style",
        "A happy puppy playing with a colorful ball at a shopping mall, children's book style",
    ]
    
    # Models to try (in order of preference for free tier)
    models = [
        "black-forest-labs/FLUX.1-schnell",  # Fastest, most free-tier friendly
        "black-forest-labs/FLUX.1-dev",      # Higher quality but may hit limits faster
    ]
    
    print(f"\n🎯 Testing with {len(test_prompts)} prompts...")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Test {i}/{len(test_prompts)} ---")
        print(f"Prompt: {prompt[:60]}...")
        
        # Try each model until one works
        success = False
        for model in models:
            try:
                print(f"   Trying model: {model}")
                
                # Generate image
                image = client.text_to_image(
                    prompt=prompt,
                    model=model
                )
                
                # Save image
                OUTPUT_DIR.mkdir(exist_ok=True)
                filename = f"test_image_{i}_{model.split('/')[-1]}.png"
                filepath = OUTPUT_DIR / filename
                image.save(filepath)
                
                print(f"   ✓ Image generated successfully!")
                print(f"   💾 Saved to: {filepath}")
                success = True
                break
                
            except Exception as e:
                print(f"   ⚠️  Failed with {model}: {str(e)[:100]}")
                continue
        
        if not success:
            print(f"   ❌ All models failed for this prompt")
    
    print("\n" + "=" * 60)
    print("✨ Test Complete!")
    print("=" * 60)
    print(f"\nCheck the {OUTPUT_DIR} directory for generated images.")


if __name__ == "__main__":
    test_image_generation()
