import os
import sys

def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python remove_local_smartcache_copies.py /path/to/parent_dir")
        sys.exit(1)

    parent_dir = sys.argv[1]
    if not os.path.isdir(parent_dir):
        print(f"Error: {parent_dir} is not a directory.")
        sys.exit(1)

    # List subdirectories (suffixes)
    for suffix in os.listdir(parent_dir):
        suffix_path = os.path.join(parent_dir, suffix)
        if not os.path.isdir(suffix_path):
            continue
        try:
            suffix_number = int(suffix)
        except ValueError:
            print(f"Skipping non-numeric suffix directory: {suffix}")
            continue

        # Process files in the suffix directory
        for fname in os.listdir(suffix_path):
            fpath = os.path.join(suffix_path, fname)
            if not os.path.isfile(fpath):
                continue
            # if len(fname) < 8 or not is_hex(fname[:8]):
            #     continue
            # first_eight = int(fname[:8], 16)
            # if first_eight % suffix_number != 0:
            try:
                os.remove(fpath)
                print(f"Deleted: {fpath}")
            except Exception as e:
                print(f"Failed to delete {fpath}: {e}")

if __name__ == "__main__":
    main()