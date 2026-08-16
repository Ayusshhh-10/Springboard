# Centralized configurations for Pre-Exam Identity Verification

# dlib face match distance tolerance.
# Lower tolerance = stricter matching.
# Higher tolerance = more permissive matching.
# Typically, 0.50 - 0.60 is the optimal range.
FACE_MATCH_TOLERANCE = 0.50
FACE_VERIFICATION_THRESHOLD = 0.50

# Maximum number of verification retries permitted before blocking the user.
MAX_VERIFICATION_ATTEMPTS = 3

# Required number of frames that must match to confirm identity.
VERIFICATION_REQUIRED_FRAMES = 5

# Total number of frames sent from client to analyze during verification.
VERIFICATION_TOTAL_FRAMES = 8
