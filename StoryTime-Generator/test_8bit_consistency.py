"""
Test: 8-bit/Pixel Art vs Normal Style for Character Consistency

This script tests whether using pixel art/8-bit style improves
character consistency across multiple story pages.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from huggingface_hub import InferenceClient
    print("✓ huggingface_hub imported successfully")
except ImportError:
    print("❌ huggingface_hub not installed")
    exit(1)

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN")
OUTPUT_DIR = Path(__file__).parent / "output" / "8bit_test"
MODEL = "black-forest-labs/FLUX.1-schnell"

# Character descriptions for both styles
CHARACTER_8BIT = {
    "puppy": "8-bit pixel art puppy, golden yellow color with brown spots, red collar, floppy ears, simple blocky design, retro video game style, 16x16 sprite aesthetic",
    "boy": "8-bit pixel art boy, brown hair, blue shirt, simple geometric shapes, retro video game character style"
}

CHARACTER_NORMAL = {
    "puppy": "cute cartoon puppy with golden-brown fluffy fur, big brown eyes, floppy ears, red collar with silver tag, friendly expression",
    "boy": "friendly young boy with short brown hair, wearing blue striped t-shirt, round face, big smile"
}


def create_prompt(scene: str, characters: list, style: str = "normal") -> str:
    """Create prompt with either 8-bit or normal style"""
    
    char_bank = CHARACTER_8BIT if style == "8bit" else CHARACTER_NORMAL
    
    char_descriptions = [char_bank[char] for char in characters if char in char_bank]
    char_text = ", ".join(char_descriptions)
    
    if style == "8bit":
        base_style = "8-bit pixel art style, retro video game aesthetic, simple geometric shapes, limited color palette, blocky design, crisp pixels, no blur"
    else:
        base_style = "children's book illustration style, bright colors, friendly and cheerful, simple cartoon style"
    
    return f"{scene}. Characters: {char_text}. {base_style}"


def test_style_consistency(style: str = "normal"):
    """Test consistency with specified style"""
    
    print(f"\n{'=' * 70}")
    print(f"🎨 Testing {style.upper()} Style Character Consistency")
    print(f"{'=' * 70}")
    
    if not HF_TOKEN or HF_TOKEN == "your_huggingface_token_here":
        print("\n⚠️  HF_TOKEN not configured")
        return
    
    client = InferenceClient(api_key=HF_TOKEN)
    
    # Story scenes
    scenes = [
        {"page": 1, "scene": "puppy sitting in bedroom", "characters": ["puppy"]},
        {"page": 2, "scene": "puppy running down hallway", "characters": ["puppy"]},
        {"page": 3, "scene": "puppy and boy walking on sidewalk", "characters": ["puppy", "boy"]},
        {"page": 4, "scene": "puppy playing with ball in park", "characters": ["puppy", "boy"]},
        {"page": 5, "scene": "puppy and boy sitting under tree", "characters": ["puppy", "boy"]},
    ]
    
    style_dir = OUTPUT_DIR / style
    style_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🎬 Generating {len(scenes)} pages with {style.upper()} style...")
    
    if style == "8bit":
        print("\n🕹️ 8-Bit Character Specs:")
        for char, desc in CHARACTER_8BIT.items():
            print(f"  • {char}: {desc[:70]}...")
    else:
        print("\n🎨 Normal Character Specs:")
        for char, desc in CHARACTER_NORMAL.items():
            print(f"  • {char}: {desc[:70]}...")
    
    generated = []
    
    for scene in scenes:
        page = scene["page"]
        print(f"\n--- Page {page} ({style}) ---")
        print(f"Scene: {scene['scene']}")
        
        prompt = create_prompt(scene['scene'], scene['characters'], style)
        print(f"Characters: {', '.join(scene['characters'])}")
        
        try:
            print(f"   Generating {style} image...")
            image = client.text_to_image(prompt=prompt, model=MODEL)
            
            filename = f"page_{page:02d}_{style}.png"
            filepath = style_dir / filename
            image.save(filepath)
            
            generated.append(filepath)
            print(f"   ✓ Saved: {filename}")
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}")
    
    print(f"\n✅ Generated {len(generated)} {style} images")
    print(f"📁 Location: {style_dir}")
    
    return len(generated)


def compare_both_styles():
    """Generate images in both styles for comparison"""
    
    print("\n" + "=" * 70)
    print("🆚 8-BIT vs NORMAL STYLE CONSISTENCY COMPARISON")
    print("=" * 70)
    
    print("\nThis test will generate the same 5 story pages in both:")
    print("  1. 8-bit pixel art style")
    print("  2. Normal children's book illustration style")
    print("\nYou can then visually compare which style maintains better")
    print("character consistency across pages!")
    
    # Test normal style
    normal_count = test_style_consistency("normal")
    
    # Test 8-bit style
    bit_count = test_style_consistency("8bit")
    
    # Summary
    print("\n" + "=" * 70)
    print("✨ COMPARISON COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Results:")
    print(f"   Normal style: {normal_count} images generated")
    print(f"   8-bit style: {bit_count} images generated")
    
    print(f"\n📁 Output location: {OUTPUT_DIR}")
    print(f"   • {OUTPUT_DIR / 'normal'}/ - Normal style images")
    print(f"   • {OUTPUT_DIR / '8bit'}/ - 8-bit pixel art images")
    
    print("\n💡 What to look for:")
    print("   ✓ Does the puppy look the same across all pages?")
    print("   ✓ Are colors consistent?")
    print("   ✓ Do character features stay the same?")
    print("   ✓ Which style has LESS variation?")
    
    print("\n🎮 8-bit advantages:")
    print("   • Simpler shapes = easier to replicate")
    print("   • Limited colors = more consistent palette")
    print("   • Geometric design = less detail to vary")
    print("   • Retro charm = nostalgic appeal")
    
    print("\n🎨 Normal advantages:")
    print("   • More expressive and detailed")
    print("   • Traditional children's book aesthetic")
    print("   • Richer emotions and poses")
    
    print("\n👉 Open both folders and compare side-by-side!")


def test_extreme_pixel_art():
    """Test with even MORE explicit pixel art parameters"""
    
    print("\n" + "=" * 70)
    print("🕹️ EXTREME PIXEL ART TEST (Maximum Simplicity)")
    print("=" * 70)
    
    if not HF_TOKEN or HF_TOKEN == "your_huggingface_token_here":
        print("\n⚠️  HF_TOKEN not configured")
        return
    
    client = InferenceClient(api_key=HF_TOKEN)
    
    # Ultra-simple pixel art descriptions
    scenes = [
        "pixel art puppy sprite, golden color, black pixels for eyes and nose, red collar",
        "pixel art puppy sprite jumping, same golden color, same red collar, retro game",
        "two pixel art sprites: golden puppy and blue shirt boy walking, NES style",
    ]
    
    extreme_dir = OUTPUT_DIR / "extreme_pixel"
    extreme_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n🎮 Generating ultra-simple pixel art sprites...")
    print("Goal: Maximum consistency through extreme simplification")
    
    for i, scene in enumerate(scenes, 1):
        print(f"\nSprite {i}: {scene[:60]}...")
        
        prompt = f"{scene}, 16-bit pixel art, 32x32 sprite, very simple geometric shapes, limited 8-color palette, crisp pixels, game asset style, white background"
        
        try:
            image = client.text_to_image(prompt=prompt, model=MODEL)
            
            filename = f"sprite_{i:02d}.png"
            filepath = extreme_dir / filename
            image.save(filepath)
            
            print(f"   ✓ Sprite saved: {filename}")
            
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}")
    
    print(f"\n📁 Extreme pixel sprites: {extreme_dir}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "normal":
            test_style_consistency("normal")
        elif sys.argv[1] == "8bit":
            test_style_consistency("8bit")
        elif sys.argv[1] == "extreme":
            test_extreme_pixel_art()
        else:
            print("Usage: python test_8bit_consistency.py [normal|8bit|extreme|compare]")
    else:
        # Default: compare both
        compare_both_styles()
    
    print("\n" + "=" * 70)
    print("Run modes:")
    print("  python test_8bit_consistency.py           # Compare both styles")
    print("  python test_8bit_consistency.py normal    # Only normal style")
    print("  python test_8bit_consistency.py 8bit      # Only 8-bit style")
    print("  python test_8bit_consistency.py extreme   # Ultra-simple pixel art")
    print("=" * 70)
