-- Migration 0002: Add onion_address column to peers table
ALTER TABLE peers ADD COLUMN onion_address TEXT;
