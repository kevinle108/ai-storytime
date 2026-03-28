"""
Test script for generating consistent characters across story pages

Approaches tested:
1. Detailed character description bank
2. Character reference generation first
3. Consistent prompt templates
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from huggingface_hub import InferenceClient
    print("✓ huggingface_hub imported successfully")
except ImportError:
    print("❌ huggingface_hub not installed")
    print("Install it with: pip install huggingface_hub")
    exit(1)

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN")
OUTPUT_DIR = Path(__file__).parent / "output" / "consistency_test"
MODEL = "black-forest-labs/FLUX.1-schnell"  # Fast model

# Character description bank - reuse these exact descriptions in every prompt
CHARACTER_BANK = {
    "puppy": {
        "name": "Sparky",
        "description": "a small fluffy golden-brown puppy with big dark brown eyes, floppy ears, a bright red collar with a silver bone-shaped tag, happy expression, cartoon style"
    },
    "boy": {
        "name": "Timmy",
        "description": "a friendly young boy with short brown hair, wearing a blue striped t-shirt and denim shorts, round face, big smile, cartoon style"
    }
}


def create_consistent_prompt(scene_description: str, characters: list) -> str:
    """
    Create a prompt that includes detailed character descriptions for consistency
    
    Args:
        scene_description: Description of what's happening in the scene
        characters: List of character keys from CHARACTER_BANK
    
    Returns:
        Complete prompt with character details
    """
    character_details = []
    for char in characters:
        if char in CHARACTER_BANK:
            char_info = CHARACTER_BANK[char]
            character_details.append(f"{char_info['name']} ({char_info['description']})")
    
    character_text = ", ".join(character_details)
    
    prompt = f"{scene_description}. Characters: {character_text}. Simple children's book illustration style, bright colors, friendly and cheerful."
    
    return prompt


def test_character_consistency():
    """Test generating consistent characters across multiple scenes"""
    
    print("\n" + "=" * 70)
    print("🎨 Testing Character Consistency Across Story Pages")
    print("=" * 70)
    
    # Check for token
    if not HF_TOKEN or HF_TOKEN == "your_huggingface_token_here":
        print("\n⚠️  HF_TOKEN not configured properly")
        print("1. Go to https://huggingface.co/settings/tokens")
        print("2. Create a token with 'Make calls to Inference Providers' permission")
        print("3. Update HF_TOKEN in .env file")
        return
    
    print(f"\n✓ HF_TOKEN found")
    
    # Initialize client
    print(f"📡 Initializing client with model: {MODEL}")
    client = InferenceClient(api_key=HF_TOKEN)
    
    # Story scenes with the same character(s)
    story_scenes = [
        {
            "page": 1,
            "scene": "Sparky wakes up in his cozy dog bed in a bright bedroom",
            "characters": ["puppy"]
        },
        {
            "page": 2,
            "scene": "Sparky runs excitedly to the front door, wagging his tail",
            "characters": ["puppy"]
        },
        {
            "page": 3,
            "scene": "Sparky and Timmy walk together on a sunny sidewalk",
            "characters": ["puppy", "boy"]
        },
        {
            "page": 4,
            "scene": "Sparky plays with a red ball at the park while Timmy watches",
            "characters": ["puppy", "boy"]
        },
        {
            "page": 5,
            "scene": "Sparky and Timmy sit under a big tree eating ice cream",
            "characters": ["puppy", "boy"]
        },
    ]
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🎬 Generating {len(story_scenes)} story pages with consistent characters...")
    print("\nCharacter Descriptions:")
    for char_key, char_info in CHARACTER_BANK.items():
        print(f"  • {char_info['name']}: {char_info['description'][:80]}...")
    
    generated_images = []
    
    for scene in story_scenes:
        page_num = scene["page"]
        print(f"\n--- Page {page_num} ---")
        print(f"Scene: {scene['scene']}")
        
        # Create prompt with consistent character descriptions
        prompt = create_consistent_prompt(scene['scene'], scene['characters'])
        print(f"Characters: {', '.join(scene['characters'])}")
        
        try:
            # Generate image
            print(f"   Generating image...")
            image = client.text_to_image(
                prompt=prompt,
                model=MODEL
            )
            
            # Save image
            filename = f"page_{page_num:02d}_consistent.png"
            filepath = OUTPUT_DIR / filename
            image.save(filepath)
            
            generated_images.append(filepath)
            print(f"   ✓ Image saved: {filename}")
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✨ Character Consistency Test Complete!")
    print("=" * 70)
    print(f"\n📁 Generated {len(generated_images)} images in: {OUTPUT_DIR}")
    print("\n💡 Tips for better consistency:")
    print("   1. Use the SAME detailed character description in every prompt")
    print("   2. Keep character features simple and memorable")
    print("   3. Mention character name + description each time")
    print("   4. Use consistent art style descriptions")
    print("   5. Consider generating a character reference sheet first")
    print("\n   Review the images to see if characters look consistent!")
    print("   If not consistent enough, try:")
    print("   - More detailed character descriptions")
    print("   - Different models (FLUX.1-dev may be better)")
    print("   - IP-Adapter-enabled models with reference images")


def generate_character_reference_sheet():
    """Generate a character reference sheet to use as visual guide"""
    
    print("\n" + "=" * 70)
    print("🎨 Generating Character Reference Sheet")
    print("=" * 70)
    
    if not HF_TOKEN or HF_TOKEN == "your_huggingface_token_here":
        print("⚠️  HF_TOKEN not configured")
        return
    
    client = InferenceClient(api_key=HF_TOKEN)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    for char_key, char_info in CHARACTER_BANK.items():
        print(f"\n📋 Creating reference sheet for: {char_info['name']}")
        
        # Generate reference image with multiple views
        prompt = f"Character reference sheet showing {char_info['description']} from multiple angles: front view, side view, happy expression, sad expression. White background, character design sheet style."
        
        print(f"   Prompt: {prompt[:80]}...")
        
        try:
            image = client.text_to_image(
                prompt=prompt,
                model=MODEL
            )
            
            filename = f"character_ref_{char_key}.png"
            filepath = OUTPUT_DIR / filename
            image.save(filepath)
            
            print(f"   ✓ Reference sheet saved: {filename}")
            print(f"   💡 Use this as a visual reference when describing the character!")
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "reference":
        # Generate reference sheets
        generate_character_reference_sheet()
    else:
        # Test consistency across story pages
        test_character_consistency()
    
    print("\n" + "=" * 70)
    print("Run with 'python test_character_consistency.py reference' to generate")
    print("character reference sheets first.")
    print("=" * 70)
