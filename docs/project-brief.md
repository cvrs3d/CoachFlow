> Historical planning document. For the current implementation and setup instructions, see [README](../README.md). Items below may be proposals rather than implemented features.

# CoachFlow

# Project Brief

## 1. Problem
  This service is aiming to help professional coaches and their clients with organising both their trainings and food review.
  
## 2. Users
  Trainer/Coach - in the system is represented as manager, who can administrate(invite, block) clients, create, update and delete time slots 
  for clients and review individual client's daily food intake via photos and description provided by the client
  
  Client - the second role in the system, client registers via provided link in the Telegram Bot (CoachFlow). After that they are capable of 
  chosing and altering chosen slots. Notifications are provided for food  review and training slot.

## 3. Roles & Permissions
Roles:
  - Guest: Person who have just opened the bot.
  - Client: Authorized client.
  - Trainer/Admin: Trainer.
  - SuperAdmin: Owner of the system, dev? .

Permissions:
Guest:
  - Can send auth request.

Client:
- Can manage their booked slots.
- Can book free slots
- Can send food review photos

Trainer:
- Approves clients.
- Manages all their slots.
- Manages their clients.
- Can manage food review photos.

## 4. MVP Scope
1. Clients can register
2. Trainer can approve clients
3. Trainer can manage time slots
4. Client is able to book free slot
5. The bot is notifying the client to send pictures of food throughout the day
6. Trainer can see those photos

## 5. Out of Scope
1. Integration with calendar apps (Google Cal., etc.)
2. Web Interface/Admin panel for trainer (To see monthly reports, etc.)
3. Payments/Subscriptions??
4. Multi trainer system/Trainer registration via web interface???
5. Repetative time slots
6. Multiple slots in a time frame
7. Soft time slot overlap restriction policy

## 6. Core User Flows
Main events:
  - Client registration:
      1. Trainer creates invite link, then sends it to the client
      2. Client accesses the bot via the link and press /start
      3. Server checks wether:
          - Does code exists?
          - Is code valid?
          - Is code expired?
          - used_count < max_uses?
          - This client is not registred yet
          - Code is linked to the real trainer   
     4. Client Accepts Privacy Policy
     5. Minimal data needed:
         - Name
         - Checkbox for food review notifications
  - Time slot booking:
      1. Client clicks "Book"
      2. System shows only free unoccupied slots 
      3. Client picks the slot
      4. System atomically reserves the slot
         4.1 If already taken, client recieves an error
      5. Trainer and Client recieve notifications
  - Food review :
      1. The client receives a photo request.
      2. The client sends 1–5 photos plus an optional comment.
      3. The backend creates a `meal_report` with `status='submitted'`.
      4. The photos are stored in S3, and the metadata is stored in PostgreSQL.
      5. The coach sees a button: “Reports to review: N”.
      6. The coach clicks “Review one by one”.
      7. The bot shows one report.
      8. The coach selects a verdict:
         ✅ Good / ⚠️ Needs improvement / ❓ Needs clarification
      9. The coach selects a template or writes a comment.
      10. The client receives feedback.
  - Adding free slots:
      1. Trainer clicks "Create time slot"
      2. Trainer is prompted to pick day, starting time, duration
      3. Trainer then is prompted with acknowledge message
      4. After confimation system checks for overlaping and creates time window if no overlap detected
      5. Clients later can access them
  - Managing slots as a Trainer :
      1. Trainer clicks "My schedule"
      2. Sees all the days and time
      3. Clicks on certain slot
      4. Sees pop-up menu
         - Silent deletion is done for unoccupied slots
         - For booked slots action menu is provided with further choises
      

## 7. Data Model
  Main entities:

    User: 
     - telegram_id (PK)
     - role (client, admin, trainer)
     - status (active, blocked, created)
     - name 
     - created_at
    Client_Trainer:
     - user_id (PK)
     - trainer_id (PK)
    TimeSlot:
     - trainer_id (PK)
     - start_time (PK)
     - end_time
     - status (available, booked, cancelled)
     - booked_by_user_id 
     - created_at
    Booking: 
      - slot_id    (PK)
      - client_id (PK)
      - trainer_id (PK)
      - status: active/cancelled/completed
      - created_at
    NotificationSchedule:
      - id
      - client_id
      - time
      - type
      - is_active

  Other entities (AI suggested, needs resolving):
    invite_codes
    invite_redemptions
    privacy_policy_versions
    consents
    
    availability_slots
    availability_rules
    appointments
    appointment_cancellations
    
    meal_checkins
    meal_reports
    meal_report_photos
    meal_reviews
    meal_review_tags
    meal_report_messages
    report_access_logs
    
    stored_files
    file_upload_jobs
    
    notifications
    reminders
    scheduled_jobs
    job_execution_logs
    
    telegram_accounts
    bot_sessions
    bot_states
    
    audit_logs
    security_events
    rate_limit_entries
    system_settings
    

  

## 8. System Architecture
 ### **Components** 
  #### Telegram Bot
    - Main interface 
    - Accepts messages and callback-buttons
    - Does not contain any business logic
  #### Backend Server
    - Registration, Authorization
    - Booking
    - Slot managing
    - Notify
 #### Database Layer 
   - Transactions
   - Constrains
   - Saves user, photo and slot data
#### Scheduler / Worker 
  - Notification
  - Upload to S3
  - Lifecycle policy

## 9. Security
- Access
- Rate limiting
- Constraints
- User Data GDPR
- Secrets
- Private Storage
- webhook secret token

## 10. Consistency & Edge Cases
- ACID
- Cancelation
- Network partition (S3 availablity) 
- Multiple messages
- Spam
- Authorization

## 11. Infrastructure ( in progress)
- hosting
  Hetzner VPS
  DigitalOcean Droplet
  Railway
  Render
  Fly.io
  AWS ECS/Fargate + RDS + S3
  Google Cloud Run + Cloud SQL + Cloud Storage
  Azure Container Apps + PostgreSQL + Blob Storage
- database
  PostgreSQL
- storage
  AWS S3
  Cloudflare R2
  Backblaze B2
  DigitalOcean Spaces
  MinIO на своем VPS
- backups
  S3 
- logs
  S3

## 12. Development Roadmap
  1. Database schema
  2. Domain services
  3. Bot handlers
  4. Background jobs
  5. Storage
  6. Security/audit
  7. Deployment
