"""
Libra Alias Generator: Creates unique, memorable three-word phrases for peer identification.
"""
import hashlib
import secrets

# Word lists for generating three-word aliases (cryptographically secure selection)
ADJECTIVES = [
    "amber", "azure", "blue", "bold", "bright", "calm", "clear", "cool", "crisp", "dark",
    "deep", "direct", "fair", "fast", "fine", "flat", "fresh", "glad", "grand", "green",
    "happy", "high", "kind", "large", "light", "long", "loud", "low", "new", "nice",
    "noble", "pale", "plain", "proud", "pure", "quick", "quiet", "rapid", "ready", "red",
    "rich", "right", "round", "royal", "safe", "short", "shy", "silver", "simple", "slow",
    "small", "smart", "smooth", "soft", "solid", "sound", "stable", "steady", "still", "strong",
    "subtle", "super", "sure", "swift", "tall", "tame", "tender", "tiny", "true", "vast",
    "warm", "weak", "white", "wide", "wild", "wise", "young", "brave", "clean", "golden"
]

NOUNS = [
    "apple", "beach", "bird", "book", "bridge", "castle", "cloud", "coffee", "coral", "crown",
    "crystal", "dawn", "desert", "diamond", "dragon", "eagle", "earth", "eclipse", "fire", "flower",
    "forest", "frost", "garden", "glacier", "harbor", "hill", "horizon", "island", "jade", "key",
    "lake", "leaf", "light", "lion", "maple", "meadow", "moon", "mountain", "ocean", "olive",
    "orchid", "palace", "path", "peak", "pearl", "phoenix", "planet", "pond", "rain", "river",
    "rock", "rose", "ruby", "sage", "sand", "sea", "shadow", "ship", "shore", "sky",
    "snow", "star", "stone", "storm", "stream", "sun", "swan", "thunder", "tiger", "tower",
    "tree", "valley", "wave", "wind", "winter", "wolf", "wood", "amber", "jade", "sapphire"
]

VERBS = [
    "blazing", "blooming", "calling", "chasing", "dancing", "dashing", "diving", "dreaming", "drifting", "echoing",
    "falling", "fading", "flying", "flowing", "gliding", "glowing", "growing", "healing", "hiding", "holding",
    "hoping", "howling", "hunting", "jumping", "keeping", "leading", "leaping", "learning", "lifting", "living",
    "moving", "playing", "racing", "raging", "resting", "riding", "rising", "roaming", "rolling", "running",
    "sailing", "seeking", "shining", "singing", "sleeping", "sliding", "soaring", "spinning", "standing", "staying",
    "swimming", "swirling", "teaching", "traveling", "walking", "waking", "wandering", "watching", "weaving", "winding",
    "winning", "working", "writing", "yearning", "yielding", "guarding", "helping", "dancing", "calling", "seeking"
]


def generate_alias(seed=None):
    """
    Generate a unique three-word alias phrase.
    
    Args:
        seed: Optional seed for deterministic generation (e.g., from public key hash)
    
    Returns:
        str: Three-word alias phrase (e.g., "brave-dancing-mountain")
    """
    if seed:
        # Deterministic generation from seed
        hash_obj = hashlib.sha256(seed.encode() if isinstance(seed, str) else seed)
        random_bytes = hash_obj.digest()
        adj_idx = int.from_bytes(random_bytes[0:2], 'big') % len(ADJECTIVES)
        verb_idx = int.from_bytes(random_bytes[2:4], 'big') % len(VERBS)
        noun_idx = int.from_bytes(random_bytes[4:6], 'big') % len(NOUNS)
    else:
        # Cryptographically secure random generation
        adj_idx = secrets.randbelow(len(ADJECTIVES))
        verb_idx = secrets.randbelow(len(VERBS))
        noun_idx = secrets.randbelow(len(NOUNS))
    
    return f"{ADJECTIVES[adj_idx]}-{VERBS[verb_idx]}-{NOUNS[noun_idx]}"


def alias_from_onion(onion_address):
    """
    Generate a deterministic alias from an onion address.
    
    Args:
        onion_address: Onion address (e.g., "abc123...xyz.onion")
    
    Returns:
        str: Three-word alias phrase derived from the onion address
    """
    # Use the onion address as seed for deterministic generation
    return generate_alias(seed=onion_address)


def validate_alias(alias):
    """
    Validate that an alias follows the correct three-word format.
    
    Args:
        alias: Alias string to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not alias or not isinstance(alias, str):
        return False
    
    parts = alias.split('-')
    if len(parts) != 3:
        return False
    
    adj, verb, noun = parts
    return (adj in ADJECTIVES and 
            verb in VERBS and 
            noun in NOUNS)
