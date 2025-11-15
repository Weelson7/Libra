import random
from data.word_dictionary import adjectives, verbs, nouns

def generate_pairing_code():
    """
    Generate a 3-word pairing code (adjective-verb-noun) for device linking.
    """
    return f"{random.choice(adjectives)}-{random.choice(verbs)}-{random.choice(nouns)}"

# Example usage:
if __name__ == "__main__":
    print("Pairing code:", generate_pairing_code())
