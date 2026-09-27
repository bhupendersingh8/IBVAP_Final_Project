# Authorized Personnel Registry (IBVAP Face & Person Verification)

This directory stores the database of authorized people allowed in surveillance zones.
Any person detected by CCTV or webcam that is NOT registered here will be flagged as **UNAUTHORIZED PERSON**.

## How to Add an Authorized Person:

### Method 1: Drop Image & Update JSON (Recommended)
1. Copy the person's photo (clear face/headshot, .jpg or .png) into the `images/` folder:
   Example: `data/authorized_people/images/rajesh_kumar.jpg`
2. Open `authorized_people.json` in this folder and add a new entry:
   ```json
   {
     "id": "AUTH-003",
     "name": "Rajesh Kumar",
     "role": "Border Security Officer",
     "department": "BSF Sector Alpha",
     "image_file": "rajesh_kumar.jpg",
     "status": "authorized",
     "notes": "Full sector clearance"
   }
   ```

### Method 2: Quick Drop (Auto-Discovery)
Simply drop a photo named with the person's name into the `images/` folder:
- Example: `images/Major_Arjun_Sharma.jpg`
- The system automatically discovers and registers them as an authorized person even without editing the JSON!

## How It Works in Live Surveillance:
- **Authorized Person**: Bounding box appears in **GREEN** with `[AUTHORIZED] Name (ID)`.
- **Unauthorized Person**: Bounding box turns **RED** with `[UNAUTHORIZED PERSON]`, triggers instant visual alert, and logs an unauthorized intrusion event.
