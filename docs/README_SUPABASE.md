# Supabase Database Setup for report_id

This repository contains scripts to help you set up the required `report_id` column and related database objects in your Supabase database.

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)
- Supabase project with `reports` table
- Supabase service_role key (admin privileges)

## Setup Instructions

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file based on the `.env.example` template:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file and add your Supabase URL and service_role key:
   
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-service-role-key
   ```

   > **IMPORTANT**: You must use the `service_role` key for these scripts, as they create database functions and modify schema.

3. **Run the setup script**

   ```bash
   python setup_supabase.py
   ```

   This script will:
   - Create helper database functions
   - Add the `report_id` column if it doesn't exist
   - Add a UNIQUE constraint on `report_id`
   - Create a trigger for automatic UUID generation
   - Add indexes for performance

4. **Verify the setup**

   ```bash
   python check_supabase.py
   ```

   This will check that everything is properly set up and display information about:
   - The `reports` table structure
   - Whether the `report_id` column exists
   - Whether proper indexes are in place
   - Whether the UUID generation trigger is active

## What It Does

This setup ensures:

1. **UUID Generation**: Every report automatically gets a UUID in the `report_id` column
2. **Uniqueness**: No duplicate UUIDs can exist in the `report_id` column
3. **Indexing**: Both `id` and `report_id` columns are indexed for performance
4. **Backwards Compatibility**: Works with existing code that uses either `id` or `report_id`

## Database Changes

The scripts make the following changes to your database:

- Adds a `report_id` UUID column with `NOT NULL` constraint
- Adds a unique constraint on the `report_id` column
- Creates the `set_report_uuid()` function
- Creates the `ensure_report_has_uuid` trigger
- Creates indexes on both `id` and `report_id` columns 