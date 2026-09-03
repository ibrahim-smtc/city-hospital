-- schema.sql
-- ----------
-- PostgreSQL schema for the City Hospital Demo API.
-- Recreates the exact same tables as data/hospital.db (SQLite lift-and-shift).
--
-- Integer PKs use GENERATED ALWAYS AS IDENTITY (Postgres equivalent of
-- SQLite's AUTOINCREMENT).  appointments.id stays TEXT because it is a
-- custom string format like "APPT-1001".
--
-- Run this once against your Supabase database before running
-- migrate_to_postgres.py.

-- Drop tables in reverse FK order so the script is re-runnable.
DROP TABLE IF EXISTS appointments          CASCADE;
DROP TABLE IF EXISTS doctor_publications   CASCADE;
DROP TABLE IF EXISTS doctor_achievements   CASCADE;
DROP TABLE IF EXISTS doctor_memberships    CASCADE;
DROP TABLE IF EXISTS doctor_expertise      CASCADE;
DROP TABLE IF EXISTS doctor_qualifications CASCADE;
DROP TABLE IF EXISTS doctor_availability   CASCADE;
DROP TABLE IF EXISTS doctors               CASCADE;
DROP TABLE IF EXISTS specialties           CASCADE;
DROP TABLE IF EXISTS services              CASCADE;

-- ------------------------------------------------------------------ doctors --
CREATE TABLE doctors (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug             TEXT    NOT NULL,
    name             TEXT    NOT NULL,
    designation      TEXT,
    department       TEXT,
    description      TEXT,
    experience_years INTEGER,
    source_url       TEXT,
    hospital_branch  TEXT DEFAULT 'Cytecare Hospitals, Bangalore'
);

-- --------------------------------------------------------- doctor_availability --
CREATE TABLE doctor_availability (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id      INTEGER NOT NULL REFERENCES doctors(id),
    available_days TEXT    NOT NULL,   -- JSON array stored as text
    available_slots TEXT   NOT NULL    -- JSON array stored as text
);

-- ------------------------------------------------------- doctor_qualifications --
CREATE TABLE doctor_qualifications (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id     INTEGER NOT NULL REFERENCES doctors(id),
    qualification TEXT    NOT NULL
);

-- ---------------------------------------------------------- doctor_expertise --
CREATE TABLE doctor_expertise (
    id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id),
    area      TEXT    NOT NULL
);

-- -------------------------------------------------------- doctor_memberships --
CREATE TABLE doctor_memberships (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id),
    membership TEXT    NOT NULL
);

-- -------------------------------------------------------- doctor_achievements --
CREATE TABLE doctor_achievements (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id),
    achievement TEXT    NOT NULL
);

-- -------------------------------------------------------- doctor_publications --
CREATE TABLE doctor_publications (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id),
    publication TEXT    NOT NULL
);

-- ------------------------------------------------------------ specialties --
CREATE TABLE specialties (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug        TEXT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT
);

-- --------------------------------------------------------------- services --
CREATE TABLE services (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug        TEXT NOT NULL,
    name        TEXT NOT NULL,
    type        TEXT,
    description TEXT
);

-- ------------------------------------------------------------ appointments --
-- id is TEXT (format: APPT-1001) so no identity sequence needed here.
CREATE TABLE appointments (
    id            TEXT    PRIMARY KEY,
    patient_name  TEXT    NOT NULL,
    patient_phone TEXT    NOT NULL,
    doctor_id     INTEGER NOT NULL REFERENCES doctors(id),
    date          TEXT    NOT NULL,
    slot          TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending',
    reason        TEXT    DEFAULT '',
    created_at    TEXT    NOT NULL
);
