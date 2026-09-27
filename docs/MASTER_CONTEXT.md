# MASTER PROJECT CONTEXT — IBVAP

You are the lead software architect, AI/ML engineer, backend engineer, frontend engineer, DevOps engineer, cybersecurity engineer, and QA engineer for this project.

Do NOT treat this as a simple college CRUD project.

We are building a serious SIH 2026 prototype for:

**Smart India Hackathon 2026**
**Problem Statement ID: PS-26187**
**Title: AI-Based Intelligent Video Analytics Platform for Border Surveillance using existing CCTV Infrastructure**
**Category: Software**

Project name / working name:

**IBVAP — Intelligent Border Video Analytics Platform**

---

# 1. CORE PROBLEM

The goal is to transform existing standard IP CCTV infrastructure into an intelligent video analytics system.

We should NOT assume that expensive new specialized surveillance cameras must be installed everywhere.

The platform should ingest existing CCTV/IP-camera video streams, process them locally/at the edge, detect relevant objects and events, generate alerts, preserve evidence, and provide an operator dashboard.

The system should be:

* Edge-first
* Offline-first
* Modular
* Secure
* Auditable
* Fault tolerant
* Scalable
* Replaceable-component architecture
* Suitable for remote/low-connectivity environments
* Human-supervised rather than blindly autonomous
* Cost-conscious
* Designed toward deployment readiness, while making NO unsupported government/military certification claims

IMPORTANT:

SIH prototype ≠ certified operational military/government deployment.

The architecture should be deployment-oriented, but documentation must clearly distinguish prototype capabilities from requirements that would require formal security assessment, hardware validation, operational testing, privacy/data governance, licensing review, and government acceptance.

---

# 2. EXPECTED HIGH-LEVEL PIPELINE

Use this conceptual architecture:

Existing CCTV
↓
RTSP/IP Video Stream
↓
Video Ingestion
↓
Video Quality Assessment
↓
Optional Preprocessing / Low-Light Enhancement
↓
Object Detection
↓
Multi-Object Tracking
↓
Spatial + Temporal Analysis
↓
Event Correlation
↓
Incident / Evidence Service
↓
Backend API + WebSocket
↓
Operations Dashboard
↓
Human Operator Feedback
↓
Dataset / Active Learning
↓
Training
↓
Validation
↓
Candidate Model
↓
Canary Deployment
↓
Production Model
↓
Rollback if required

---

# 3. MVP FEATURES

The first strong SIH MVP should support:

1. Multiple CCTV/RTSP camera streams
2. Person detection
3. Vehicle detection
4. Basic relevant object detection
5. Multi-object tracking
6. Persistent track IDs
7. Virtual fence / restricted zone
8. Line crossing
9. Polygon intrusion detection
10. Exclusion zones
11. Loitering / temporal activity analysis
12. Night/low-light video handling
13. Vehicle → number plate detection → OCR pipeline
14. Real-time alerts
15. Event logging
16. Incident creation
17. Evidence snapshot/reference
18. SHA-256 evidence integrity hash
19. Operator feedback
20. Model version tracking
21. Audit logging
22. Camera health monitoring
23. System health monitoring
24. Offline local operation
25. React-based operations dashboard
26. Docker-based deployment
27. Model evaluation
28. Candidate/production model management
29. Rollback capability

Advanced features can be added after MVP:

* Active learning
* DVC dataset versioning
* MLflow experiment tracking
* Human-supervised continuous learning
* Canary deployment
* Automatic health-based rollback
* NVIDIA GPU acceleration
* TensorRT optimization
* NVIDIA DeepStream integration
* Advanced activity recognition
* Multi-camera correlation
* Offline synchronization

---

# 4. IMPORTANT AI/ML DESIGN PRINCIPLE

DO NOT create a monolithic AI script.

The AI layer MUST be replaceable.

Use interfaces/adapters such as:

DetectionEngine
TrackingEngine
OCRProvider
ActivityEngine
Preprocessor
ModelProvider

Example conceptual interface:

DetectionEngine.detect(frame) → Detection[]

Each detection should contain at minimum:

* camera_id
* frame_id
* timestamp
* class_name
* confidence
* bounding_box
* model_name
* model_version

The rest of the application must NOT depend directly on one specific AI framework.

This allows us to replace a detector later without rewriting the backend, rules engine, dashboard, or database.

---

# 5. OBJECT DETECTION

The detector must be configurable.

Do NOT hard-code:

* model path
* confidence threshold
* input size
* inference device
* class list

These should come from configuration.

Architecture should allow:

Development detector
↓
Production detector
↓
Future license-cleared detector

YOLO-family models may be used for SIH prototyping, but DO NOT assume that every YOLO implementation/model is automatically suitable for proprietary government production deployment.

The exact model and license must be recorded in the project's third-party/model license registry.

Avoid claims such as:

"100% free for commercial deployment"

unless the exact model/version/license has been verified.

---

# 6. TRACKING

Use a replaceable multi-object tracker.

ByteTrack or another appropriate tracker can be used if its exact implementation/license is documented.

Track object state should contain:

* track_id
* class
* current bounding box
* center point
* trajectory
* first_seen
* last_seen
* confidence history
* current state

The tracker must be independent from the detector.

---

# 7. VIRTUAL FENCE / SPATIAL RULE ENGINE

Implement a reusable geometry/rules engine.

Supported zone/rule types:

* LINE
* POLYGON
* RESTRICTED_ZONE
* EXCLUSION_ZONE

Coordinates should preferably be normalized relative to frame dimensions.

Examples:

Person crosses restricted boundary
→ event generated

Vehicle enters restricted polygon
→ event generated

Object remains in restricted zone beyond configured duration
→ potential loitering event

Do NOT trigger critical security alerts based on a single noisy frame.

Use temporal confirmation/debouncing.

---

# 8. ACTIVITY ANALYSIS

Activity detection should be temporal.

Do NOT classify activities using only one bounding box or one frame.

Potential activities:

* standing
* walking
* crouching
* loitering

Activity signals should normally contribute to event correlation.

IMPORTANT:

Activity classification alone should NOT automatically generate a high-severity security incident without contextual confirmation.

---

# 9. NIGHT / LOW-LIGHT PROCESSING

Implement a video-quality layer.

It should estimate:

* brightness
* contrast
* noise
* frame quality

Only enable enhancement when needed.

Possible baseline:

CLAHE / controlled preprocessing.

Do NOT automatically include research implementations with restrictive/non-commercial licenses in a production architecture.

Any ML-based low-light enhancement model must undergo the same license review as the detector.

The system should benchmark:

Raw video
vs
Processed video

Metrics:

* detection recall
* false positives
* FPS
* inference latency
* end-to-end latency

Do not claim improvement without measured results.

---

# 10. ANPR PIPELINE

Architecture:

Vehicle Detection
↓
Vehicle Crop
↓
Plate Detection
↓
Plate Crop
↓
OCR
↓
Normalization
↓
Confidence
↓
Event / Record

Do NOT run OCR on every frame.

Use configurable triggers such as:

* vehicle detected
* stable track
* suitable crop
* plate candidate detected

The OCR provider must be replaceable.

PaddleOCR can be evaluated as one implementation, but exact version/license must be recorded.

For SIH testing, prefer:

* synthetic plates
* authorized datasets
* controlled test footage

Do not unnecessarily collect or expose personal vehicle data.

---

# 11. EVENT CORRELATION

Do not let every detector produce an independent alert.

Create an event correlation layer.

Possible inputs:

* object detection
* tracking
* zone rules
* line crossing
* temporal behavior
* activity
* camera health
* confidence
* repeated observations

Severity levels:

INFO
LOW
MEDIUM
HIGH
CRITICAL

Every event should explain WHY it was generated.

Example:

"Person entered restricted zone and remained for 8 seconds."

This is better than:

"Suspicious person detected."

---

# 12. INCIDENT / EVIDENCE SYSTEM

Each important event can create an incident.

Incident metadata should include:

* incident_id
* camera_id
* event_type
* timestamp
* severity
* confidence
* model_name
* model_version
* evidence_reference
* evidence_hash
* created_at

Store large evidence files outside the relational database.

The database stores metadata/reference.

Use SHA-256 to verify evidence file integrity.

IMPORTANT:

Do NOT claim that SHA-256 by itself provides legal admissibility, chain-of-custody, or statutory compliance.

---

# 13. DATABASE ARCHITECTURE

Development:

SQLite

Production-oriented:

PostgreSQL

Use repository/service abstraction so database migration does not require rewriting business logic.

Suggested tables:

users
roles
cameras
zones
detections
tracks
events
incidents
evidence
feedback
models
model_evaluations
audit_logs
system_health

Use:

* UTC timestamps
* proper indexes
* foreign keys
* migrations
* constraints
* parameterized queries
* transaction handling

No passwords/API keys/secrets in the database source files.

---

# 14. BACKEND

Use:

Python
FastAPI
Pydantic
Uvicorn

Suggested API areas:

GET /health
GET /cameras
POST /cameras
GET /zones
POST /zones
GET /events
GET /incidents
GET /evidence
POST /feedback
GET /models
GET /system/metrics

WebSocket:

/ws/alerts

Backend responsibilities:

* authentication
* authorization
* camera management
* event management
* incident management
* evidence metadata
* feedback
* model management
* system health
* audit logs

Business rules should remain server-side.

Never trust frontend validation alone.

---

# 15. AUTHENTICATION / RBAC

Roles:

ADMIN
OPERATOR
READ_ONLY

Admin:

* user management
* camera configuration
* zone configuration
* model management
* system settings

Operator:

* monitor cameras
* acknowledge incidents
* view evidence
* provide feedback

Read-only:

* view permitted dashboards/events
* no modification

Use secure password hashing.

Use secure authentication tokens/session management.

Do not store plaintext passwords.

---

# 16. SECURITY BASELINE

Implement security from the beginning.

Requirements:

* RBAC
* secure password hashing
* token/session protection
* input validation
* SQL injection protection
* path traversal protection
* upload restrictions
* file type validation
* file size limits
* restricted CORS
* security headers
* rate limiting
* structured audit logs
* secrets through environment/secret management
* no credentials in source code
* no credentials in logs
* dependency scanning
* container image scanning
* SBOM generation
* secure configuration defaults

Do NOT claim:

"military-grade security"
"government certified"
"MHA certified"

unless formal evidence exists.

Use wording such as:

"security-focused architecture"
"deployment-oriented security baseline"

---

# 17. AUDIT LOGGING

Audit important operations.

Examples:

* login
* logout
* failed login
* camera configuration change
* zone creation/change/deletion
* incident acknowledgement
* incident status change
* evidence access
* operator feedback
* model promotion
* model rollback
* admin changes

Each audit entry should include:

* actor
* action
* timestamp
* resource
* result
* reference ID

Operators should not be able to casually modify audit history.

---

# 18. CONTINUOUS LEARNING

THIS IS A CRITICAL ARCHITECTURAL REQUIREMENT.

Do NOT implement uncontrolled online learning.

Production model weights must NEVER silently change because of operator feedback.

Correct workflow:

Live camera
↓
Detection
↓
Alert
↓
Operator labels:

TRUE_INTRUSION
FALSE_ALARM
UNSURE

↓
Store feedback
↓
Select valuable samples
↓
Human labeling
↓
Version dataset
↓
Train candidate model
↓
Fixed validation dataset
↓
Evaluate
↓
Candidate model
↓
Human approval
↓
Canary deployment
↓
Monitor 48–72 hours
↓
Promote OR rollback
↓
Production

Potential active-learning samples:

* low-confidence detections
* false alarms
* uncertain cases
* manually flagged missed detections
* difficult environmental conditions

Training frequency can initially be:

Feedback: continuous
Labeling: weekly
Retraining: biweekly/monthly
Canary: 48–72 hours
Audit: monthly

These are configurable operational defaults, not hard requirements.

---

# 19. DATA VERSIONING

Use DVC or an equivalent versioning strategy.

Separate:

data/raw
data/processed
data/labeled
data/validation

The validation set should remain controlled and should not silently change during every retraining cycle.

Record:

* dataset version
* source
* checksum
* annotation version
* training date
* model version

Large datasets should NOT be committed to Git.

---

# 20. EXPERIMENT TRACKING

Use MLflow or equivalent self-hosted experiment tracking.

Record:

* model version
* dataset version
* hyperparameters
* precision
* recall
* mAP where appropriate
* false-positive rate
* latency
* FPS
* hardware
* training duration
* preprocessing configuration
* validation results

No model should be promoted merely because it "looks better."

---

# 21. MODEL REGISTRY

Model states:

CANDIDATE
VALIDATED
CANARY
PRODUCTION
REJECTED
RETIRED

Never overwrite production model files blindly.

Always maintain previous production versions for rollback.

Example:

model_v1 → production
model_v2 → candidate
model_v2 → validated
model_v2 → canary
model_v2 → production

If v2 fails:

model_v1 → production

---

# 22. OFFLINE-FIRST ARCHITECTURE

Core functionality must continue without internet.

Local components:

* inference
* database
* dashboard
* evidence storage
* camera processing
* alerts

Internet/cloud should NOT be required for core inference.

If connectivity returns, optional synchronization can occur.

Use queued synchronization where appropriate.

Do not make a cloud API mandatory for the SIH prototype.

---

# 23. RTSP DEVELOPMENT ENVIRONMENT

For SIH demonstration, use local authorized video files.

MediaMTX can be used as a local RTSP simulator.

Example:

CAM-01
CAM-02
CAM-03
CAM-04

Each can replay a different authorized/local clip.

Do NOT put video files inside Git.

Use configuration such as:

CAM_01=...
CAM_02=...
CAM_03=...
CAM_04=...

Keep actual paths outside source control.

No dependence on live YouTube/EarthCam/etc. for the core demo.

The system must continue to work entirely from local media.

---

# 24. DATA COLLECTION STRATEGY

Do NOT design the system around downloading huge quantities of internet videos every day.

Preferred data sources:

1. Authorized own recordings
2. Synthetic test scenarios
3. Legitimately licensed/open datasets
4. Carefully selected free-to-use footage where rights permit

For initial SIH prototype, a few GB of carefully selected data is preferable to hundreds of GB.

Large data should be versioned externally using DVC/object storage.

---

# 25. FRONTEND

Use:

React
TypeScript
Tailwind CSS

The dashboard should look like a serious professional operations application.

DO NOT use:

* cyberpunk styling
* excessive neon
* glowing borders everywhere
* excessive gradients
* unnecessary animations
* "AI-looking" gimmicks

Preferred visual language:

* neutral gray/white surfaces
* restrained dark/blue operational accents
* red only for alerts
* green for healthy status
* clear typography
* information density without clutter

Pages:

Dashboard
Cameras
Zones
Incidents
Evidence
Events
Models
System Health
Settings

Dashboard should show:

* camera status
* live/near-live feeds
* active incidents
* severity
* recent events
* FPS
* system health
* GPU/CPU/memory
* connectivity
* camera connection status

Alerts should arrive through WebSocket where appropriate.

---

# 26. PERFORMANCE METRICS

Never invent performance numbers.

Measure:

* FPS per camera
* total FPS
* inference latency
* end-to-end latency
* CPU usage
* GPU usage
* RAM
* VRAM
* dropped frames
* camera reconnect time
* alert latency
* processing queue depth

Benchmark:

1 stream
2 streams
4 streams
8 streams

only where hardware supports it.

Generate benchmark reports.

Performance claims in the SIH presentation must be based on measured results.

---

# 27. NVIDIA ACCELERATION

Architecture should support optional NVIDIA acceleration.

Possible production-oriented pipeline:

RTSP
↓
GStreamer / NVIDIA DeepStream
↓
TensorRT
↓
Detection
↓
Tracking
↓
Rules

The core application should still be architecturally independent from NVIDIA-specific components.

Potential optimization:

ONNX
↓
TensorRT
↓
FP16 / validated INT8

Do not claim a specific speedup until benchmarking on the actual target hardware.

---

# 28. RESILIENCE TESTING

Test:

* camera disconnect
* camera reconnect
* invalid RTSP URL
* corrupt frame
* backend restart
* database restart
* GPU unavailable
* network interruption
* disk-space warning
* high CPU usage
* high GPU usage
* overloaded processing queue

The system should:

detect
log
display
recover

where recovery is possible.

---

# 29. DOCKER

Use Docker Compose for the development/deployment-oriented environment.

Potential services:

frontend
backend
database
mlflow
mediamtx
inference

Keep inference separable so GPU-specific implementation can evolve independently.

Use:

* health checks
* environment variables
* secrets
* minimal exposed ports
* separate development/production configuration

---

# 30. LICENSE MANAGEMENT

Every third-party component/model must be documented.

Create:

docs/THIRD_PARTY_LICENSES.md

and preferably:

docs/third_party_registry.yaml

Fields:

name
version
source
license
license_url
model_license
commercial_status
attribution_required
source_disclosure_required
additional_terms
notes

DO NOT mark something as "commercially free" without checking the exact license/version.

The project must be able to replace a component if its license is unsuitable.

---

# 31. REPOSITORY STRUCTURE

Use this as the target architecture:

IBVAP/

├── apps/
│   ├── backend/
│   └── frontend/
│
├── services/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── detection/
│   ├── tracking/
│   ├── rules/
│   ├── anpr/
│   ├── incidents/
│   └── feedback/
│
├── ml/
│   ├── datasets/
│   ├── labeling/
│   ├── training/
│   ├── evaluation/
│   └── models/
│
├── infrastructure/
│   ├── mediamtx/
│   ├── docker/
│   └── nvidia/
│
├── configs/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── labeled/
│   ├── validation/
│   └── incidents/
│
├── tests/
│
├── docs/
│
└── scripts/

---

# 32. CONFIGURATION PRINCIPLE

Do not hard-code environment-specific values.

Use:

.env
.env.example
config files

Separate:

development
testing
production

configuration.

Never commit:

* API keys
* passwords
* private certificates
* CCTV credentials
* tokens
* secrets
* private footage

---

# 33. TESTING STRATEGY

Implement:

Unit tests
Integration tests
API tests
Database tests
Geometry tests
Detection adapter tests
Tracking tests
WebSocket tests
Authentication tests
RBAC tests
Resilience tests
Security tests

Security tests should include:

* invalid authentication
* unauthorized endpoint access
* unauthorized camera access
* unauthorized evidence access
* path traversal
* SQL injection attempts
* oversized uploads
* malformed payloads
* malformed WebSocket messages
* rate-limit behavior
* CORS validation

---

# 34. DEVELOPMENT PRINCIPLES

Follow these rules:

1. Do not create one giant Python file.
2. Do not tightly couple frontend and ML logic.
3. Do not hard-code camera credentials.
4. Do not hard-code model paths.
5. Do not silently modify production models.
6. Do not silently retrain models.
7. Do not expose internal services unnecessarily.
8. Do not put secrets in Git.
9. Do not put large video datasets in Git.
10. Do not claim unmeasured performance.
11. Do not claim government/military certification.
12. Do not add unnecessary cloud dependency.
13. Do not add unnecessary UI animations.
14. Do not use fake AI outputs in the final architecture.
15. Do not hide errors — log them properly.
16. Prefer interfaces/adapters for replaceable components.
17. Keep the system testable.
18. Keep configuration externalized.
19. Keep production and demo concerns clearly separated.
20. Preserve rollback capability.

---

# 35. SIH DEMO CONFIGURATION

The final SIH demo can use four simulated cameras:

CAM-01
Normal daytime scene

CAM-02
Night/low-light scene

CAM-03
Restricted-zone intrusion scenario

CAM-04
Vehicle + ANPR scenario

Dashboard should visibly demonstrate:

* camera health
* detection
* tracking
* zone intrusion
* alert generation
* incident creation
* evidence
* operator feedback
* model version
* system health

The demo should be deterministic and repeatable.

---

# 36. SIH PRESENTATION ANGLE

The solution should emphasize four major differentiators:

A. Existing CCTV Intelligence
Turn existing CCTV infrastructure into intelligent surveillance without requiring complete camera replacement.

B. Edge/Offline First
Core detection and alerting continue locally even in low/no-connectivity environments.

C. Human-Supervised Continuous Learning
Operator feedback becomes training data through controlled versioned retraining.

D. Security + Reliability + Auditability
RBAC, audit logs, evidence integrity, health monitoring, model versioning, canary deployment, and rollback.
