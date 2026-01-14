"""
Remove duplicate images from extracted frames directory.
Uses perceptual hashing to detect visually similar/identical images.
"""
import os
import hashlib
from pathlib import Path
from PIL import Image
import imagehash
import send2trash

def get_image_hash(image_path, hash_size=8):
    """
    Generate perceptual hash for an image.
    
    Args:
        image_path: Path to the image file
        hash_size: Size of the hash (larger = more precise)
    
    Returns:
        Perceptual hash string
    """
    try:
        with Image.open(image_path) as img:
            # Use average hash for perceptual similarity detection
            return str(imagehash.average_hash(img, hash_size=hash_size))
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def find_and_remove_duplicates(directory, similarity_threshold=5, dry_run=True):
    """
    Find and remove duplicate images in a directory.
    
    Args:
        directory: Path to directory containing images
        similarity_threshold: Maximum hash difference to consider images as duplicates
        dry_run: If True, only report duplicates without deleting
    
    Returns:
        Dictionary with statistics
    """
    directory = Path(directory)
    
    # Dictionary to store hash -> list of file paths
    hash_dict = {}
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    image_files = [f for f in directory.iterdir() 
                   if f.is_file() and f.suffix.lower() in image_extensions]
    
    print(f"Found {len(image_files)} image files in {directory}")
    print("Calculating image hashes...")
    
    # Calculate hashes for all images
    for idx, img_path in enumerate(image_files, 1):
        if idx % 100 == 0:
            print(f"Processed {idx}/{len(image_files)} images...")
        
        img_hash = get_image_hash(img_path)
        if img_hash:
            if img_hash not in hash_dict:
                hash_dict[img_hash] = []
            hash_dict[img_hash].append(img_path)
    
    # Find duplicates
    duplicates = []
    unique_hashes = set()
    
    for img_hash, paths in hash_dict.items():
        if len(paths) > 1:
            # Multiple files with exact same hash
            duplicates.extend(paths[1:])  # Keep first, mark rest as duplicates
            unique_hashes.add(img_hash)
        
    # Find near-duplicates using similarity threshold
    if similarity_threshold > 0:
        print("\nLooking for near-duplicates...")
        hashes_to_compare = list(hash_dict.keys())
        
        for i in range(len(hashes_to_compare)):
            for j in range(i + 1, len(hashes_to_compare)):
                hash1 = imagehash.hex_to_hash(hashes_to_compare[i])
                hash2 = imagehash.hex_to_hash(hashes_to_compare[j])
                
                # Calculate Hamming distance
                if hash1 - hash2 <= similarity_threshold:
                    # These are similar, keep the first one
                    if hashes_to_compare[j] not in unique_hashes:
                        # Add all but first from the second group
                        for path in hash_dict[hashes_to_compare[j]][1:]:
                            if path not in duplicates:
                                duplicates.append(path)
    
    # Sort duplicates by name for better reporting
    duplicates.sort(key=lambda p: p.name)
    
    # Statistics
    stats = {
        'total_files': len(image_files),
        'unique_files': len(image_files) - len(duplicates),
        'duplicates_found': len(duplicates),
        'space_saved': sum(p.stat().st_size for p in duplicates if p.exists())
    }
    
    # Report findings
    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"{'='*60}")
    print(f"Total images: {stats['total_files']}")
    print(f"Unique images: {stats['unique_files']}")
    print(f"Duplicates found: {stats['duplicates_found']}")
    print(f"Space to be saved: {stats['space_saved'] / 1024 / 1024:.2f} MB")
    
    if duplicates:
        print(f"\nDuplicate files (showing first 20):")
        for dup_path in duplicates[:20]:
            print(f"  - {dup_path.name}")
        if len(duplicates) > 20:
            print(f"  ... and {len(duplicates) - 20} more")
    
    # Delete duplicates if not dry run
    if not dry_run and duplicates:
        print(f"\n{'='*60}")
        response = input(f"Delete {len(duplicates)} duplicate files? (yes/no): ")
        if response.lower() == 'yes':
            deleted = 0
            for dup_path in duplicates:
                try:
                    # dup_path.unlink()
                    send2trash.send2trash(str(dup_path))
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {dup_path}: {e}")
            print(f"Successfully deleted {deleted} duplicate files.")
            stats['deleted'] = deleted
        else:
            print("Deletion cancelled.")
    elif dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN MODE - No files were deleted.")
        print("Run with --delete flag to actually remove duplicates.")
    
    return stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove duplicate images from a directory')
    parser.add_argument('directory', nargs='?', 
                       default='datasets/extracted_frames',
                       help='Directory containing images (default: datasets/extracted_frames)')
    parser.add_argument('--delete', action='store_true',
                       help='Actually delete duplicates (default is dry-run)')
    parser.add_argument('--threshold', type=int, default=5,
                       help='Similarity threshold (0-64, lower=more strict, default=5)')
    
    args = parser.parse_args()
    
    # Check if directory exists
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' not found!")
        exit(1)
    
    # Run duplicate detection
    stats = find_and_remove_duplicates(
        args.directory, 
        similarity_threshold=args.threshold,
        dry_run=not args.delete
    )
