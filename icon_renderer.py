#!/usr/bin/env python3
"""
Icon Renderer for LED Matrix
Pre-renders icons/logos to JSON format with configurable intensity quantization
"""

import numpy as np
from PIL import Image
import json
import os
import argparse
from pathlib import Path
import sys


class IconRenderer:
    """Renders icons to LED matrix format with intensity quantization"""
    
    def __init__(self, target_size=(7, 15), intensity_levels=5):
        """
        Initialize renderer
        
        Args:
            target_size: (width, height) in pixels
            intensity_levels: Number of discrete intensity levels (2-5 recommended)
        """
        self.target_width, self.target_height = target_size
        self.intensity_levels = intensity_levels
        
    def load_image(self, path):
        """Load and prepare image for rendering"""
        try:
            img = Image.open(path)
            print(f"Loaded image: {img.size[0]}x{img.size[1]} ({img.mode})")
            
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
                print(f"Converted to grayscale")
            
            # Resize to target dimensions
            if img.size != (self.target_width, self.target_height):
                img = img.resize((self.target_width, self.target_height), 
                                Image.Resampling.LANCZOS)
                print(f"Resized to: {self.target_width}x{self.target_height}")
            
            return np.array(img)
            
        except Exception as e:
            print(f"Error loading image: {e}", file=sys.stderr)
            sys.exit(1)
    
    def quantize_intensities(self, img_array):
        """
        Reduce image to N discrete intensity levels
        
        Args:
            img_array: numpy array with values 0-255
            
        Returns:
            quantized array with intensity_levels discrete values
        """
        # Create intensity levels from 0 to 255
        levels = np.linspace(0, 255, self.intensity_levels).astype(np.uint8)
        
        # Quantize to nearest level
        quantized = np.zeros_like(img_array)
        
        # For each pixel, find nearest intensity level
        for pixel_val in np.unique(img_array):
            # Find closest level
            closest_idx = np.argmin(np.abs(levels - pixel_val))
            mask = img_array == pixel_val
            quantized[mask] = levels[closest_idx]
        
        print(f"Quantized to {self.intensity_levels} levels: {levels.tolist()}")
        return quantized.astype(np.uint8)
    
    def render_static(self, image_path, output_path):
        """
        Render static icon frame
        
        Args:
            image_path: Path to source image
            output_path: Path for output JSON file
            
        Returns:
            quantized numpy array
        """
        print(f"\n=== Rendering Static Icon ===")
        print(f"Input: {image_path}")
        
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        # Save as JSON (transposed for LED matrix orientation)
        output_data = quantized.T.tolist()
        
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Output: {output_path}")
        print(f"Dimensions: {quantized.shape[0]}x{quantized.shape[1]} (WxH)")
        return quantized
    
    def render_fade_animation(self, image_path, output_dir, frames=10):
        """
        Pre-render fade in animation
        
        Args:
            image_path: Path to source image
            output_dir: Directory for output frames
            frames: Number of animation frames
        """
        print(f"\n=== Rendering Fade Animation ===")
        print(f"Frames: {frames}")
        
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frames):
            alpha = i / (frames - 1)  # 0 to 1
            frame = (quantized * alpha).astype(np.uint8)
            
            output_path = os.path.join(output_dir, f"frame_{i:02d}.json")
            output_data = frame.T.tolist()
            
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
        
        print(f"Output: {output_dir}/ (frame_00.json to frame_{frames-1:02d}.json)")
    
    def render_pulse_animation(self, image_path, output_dir, frames=20, cycles=1):
        """
        Pre-render pulse/breathing animation
        
        Args:
            image_path: Path to source image
            output_dir: Directory for output frames
            frames: Number of animation frames
            cycles: Number of pulse cycles
        """
        print(f"\n=== Rendering Pulse Animation ===")
        print(f"Frames: {frames}, Cycles: {cycles}")
        
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frames):
            # Sine wave for smooth pulsing
            phase = (i / frames) * 2 * np.pi * cycles
            intensity = 0.5 + 0.5 * np.sin(phase)  # 0 to 1
            frame = (quantized * intensity).astype(np.uint8)
            
            output_path = os.path.join(output_dir, f"frame_{i:02d}.json")
            output_data = frame.T.tolist()
            
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
        
        print(f"Output: {output_dir}/ (frame_00.json to frame_{frames-1:02d}.json)")
    
    def render_slide_animation(self, image_path, output_dir, frames=10, direction='left'):
        """
        Pre-render slide animation
        
        Args:
            image_path: Path to source image
            output_dir: Directory for output frames
            frames: Number of animation frames
            direction: 'left', 'right', 'up', or 'down'
        """
        print(f"\n=== Rendering Slide Animation ===")
        print(f"Frames: {frames}, Direction: {direction}")
        
        img = self.load_image(image_path)
        quantized = self.quantize_intensities(img)
        
        os.makedirs(output_dir, exist_ok=True)
        
        for i in range(frames):
            progress = i / (frames - 1)  # 0 to 1
            frame = np.zeros_like(quantized)
            
            if direction == 'left':
                offset = int((1 - progress) * quantized.shape[1])
                width = quantized.shape[1] - offset
                frame[:, :width] = quantized[:, offset:]
            elif direction == 'right':
                offset = int(progress * quantized.shape[1])
                frame[:, offset:] = quantized[:, :quantized.shape[1] - offset]
            elif direction == 'up':
                offset = int((1 - progress) * quantized.shape[0])
                height = quantized.shape[0] - offset
                frame[:height, :] = quantized[offset:, :]
            elif direction == 'down':
                offset = int(progress * quantized.shape[0])
                frame[offset:, :] = quantized[:quantized.shape[0] - offset, :]
            
            output_path = os.path.join(output_dir, f"frame_{i:02d}.json")
            output_data = frame.T.tolist()
            
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)
        
        print(f"Output: {output_dir}/ (frame_00.json to frame_{frames-1:02d}.json)")
    
    def preview_icon(self, image_array, scale=2):
        """
        Print ASCII preview of icon
        
        Args:
            image_array: numpy array to preview
            scale: Character width/height ratio compensation
        """
        print("\n=== Icon Preview ===")
        # ASCII gradient from dark to light
        chars = ' .:-=+*#%@'
        
        for row in image_array:
            line = ''
            for pixel in row:
                # Map 0-255 to char index
                idx = int((pixel / 255) * (len(chars) - 1))
                line += chars[idx] * scale
            print(line)
        print()


def parse_size(size_str):
    """Parse size string like '7x15' to tuple (7, 15)"""
    try:
        w, h = size_str.lower().split('x')
        return (int(w), int(h))
    except:
        raise argparse.ArgumentTypeError(f"Size must be WxH format (e.g., 7x15)")


def main():
    parser = argparse.ArgumentParser(
        description='Pre-render icons for LED matrix display',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Render static icon
  %(prog)s input.png -o output.json
  
  # Render with custom size and intensity levels
  %(prog)s input.png -o output.json --size 9x34 --levels 3
  
  # Render animations
  %(prog)s input.png -o icons/firefox --animations fade pulse slide
  
  # Preview icon
  %(prog)s input.png --preview
        """
    )
    
    parser.add_argument('input', help='Input image path (PNG, JPG, etc.)')
    parser.add_argument('-o', '--output', required=True,
                       help='Output path (file for static, directory for animations)')
    parser.add_argument('--size', type=parse_size, default='7x15',
                       help='Target size as WxH (default: 7x15)')
    parser.add_argument('--levels', type=int, default=5,
                       help='Intensity levels 2-8 (default: 5)')
    parser.add_argument('--animations', nargs='+',
                       choices=['static', 'fade', 'pulse', 'slide'],
                       default=['static'],
                       help='Animations to render (default: static)')
    parser.add_argument('--frames', type=int, default=15,
                       help='Number of frames for animations (default: 15)')
    parser.add_argument('--slide-direction', choices=['left', 'right', 'up', 'down'],
                       default='left', help='Slide direction (default: left)')
    parser.add_argument('--pulse-cycles', type=int, default=1,
                       help='Number of pulse cycles (default: 1)')
    parser.add_argument('--preview', action='store_true',
                       help='Show ASCII preview of icon')
    
    args = parser.parse_args()
    
    # Validate intensity levels
    if not 2 <= args.levels <= 8:
        parser.error("Intensity levels must be between 2 and 8")
    
    # Create renderer
    renderer = IconRenderer(target_size=args.size, intensity_levels=args.levels)
    
    # Render requested animations
    for anim_type in args.animations:
        if anim_type == 'static':
            # For static, output should be a file
            output_file = args.output if args.output.endswith('.json') else f"{args.output}/static.json"
            icon_array = renderer.render_static(args.input, output_file)
            
            if args.preview:
                renderer.preview_icon(icon_array)
                
        elif anim_type == 'fade':
            output_dir = f"{args.output}/fade" if not args.output.endswith('fade') else args.output
            renderer.render_fade_animation(args.input, output_dir, frames=args.frames)
            
        elif anim_type == 'pulse':
            output_dir = f"{args.output}/pulse" if not args.output.endswith('pulse') else args.output
            renderer.render_pulse_animation(args.input, output_dir, frames=args.frames, 
                                          cycles=args.pulse_cycles)
            
        elif anim_type == 'slide':
            output_dir = f"{args.output}/slide_{args.slide_direction}"
            renderer.render_slide_animation(args.input, output_dir, frames=args.frames,
                                          direction=args.slide_direction)
    
    print("\n=== Rendering Complete ===")


if __name__ == "__main__":
    main()
