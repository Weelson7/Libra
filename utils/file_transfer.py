import os
import hashlib

CHUNK_SIZE = 64 * 1024  # 64KB

def split_file(file_path):
    """Yield file chunks and their sequence numbers."""
    with open(file_path, 'rb') as f:
        seq = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            yield seq, chunk
            seq += 1

def reassemble_file(chunks, output_path):
    """Reassemble file from ordered chunks."""
    with open(output_path, 'wb') as f:
        for seq, chunk in sorted(chunks, key=lambda x: x[0]):
            f.write(chunk)

def sha256_file(file_path):
    """Return SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha.update(block)
    return sha.hexdigest()

def save_file_to_storage(src_path, storage_dir):
    """Save file to storage directory, return new path and hash."""
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    filename = os.path.basename(src_path)
    dst_path = os.path.join(storage_dir, filename)
    # Avoid overwrite
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(dst_path):
        dst_path = os.path.join(storage_dir, f"{base}_{i}{ext}")
        i += 1
    with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
        dst.write(src.read())
    file_hash = sha256_file(dst_path)
    return dst_path, file_hash
