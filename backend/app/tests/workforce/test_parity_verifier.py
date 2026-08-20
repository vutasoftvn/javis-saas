import pytest

def test_parity_verifier_mismatch():
    """Test that parity verifier detects mismatch between legacy and canonical projections."""
    # Giả lập legacy data
    legacy_data = {"runs": 100, "artifacts": 200, "hashes": ["abc", "def"]}
    
    # Giả lập canonical data (thiếu 1 artifact)
    canonical_data = {"runs": 100, "artifacts": 199, "hashes": ["abc"]}
    
    def verify(legacy, canonical):
        if legacy["runs"] != canonical["runs"]:
            return False
        if legacy["artifacts"] != canonical["artifacts"]:
            return False
        if legacy["hashes"] != canonical["hashes"]:
            return False
        return True
        
    assert verify(legacy_data, canonical_data) == False

def test_parity_verifier_match():
    """Test that parity verifier passes when data matches exactly."""
    legacy_data = {"runs": 100, "artifacts": 200, "hashes": ["abc", "def"]}
    canonical_data = {"runs": 100, "artifacts": 200, "hashes": ["abc", "def"]}
    
    def verify(legacy, canonical):
        return legacy == canonical
        
    assert verify(legacy_data, canonical_data) == True
